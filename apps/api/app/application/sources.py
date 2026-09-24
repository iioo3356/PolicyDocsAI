import hashlib
from pathlib import Path
from sqlalchemy import delete, func, select
from sqlalchemy.orm import Session
from app.config import settings
from app.infrastructure.models import AnalysisJob, JobStatus, PolicyCandidate, PolicyEvidence, Source, SourceChunk, SourceFile, SourceKind, SourceVersion
from app.application.dto import SourceAnalysisOut, SourceRoleUpdate
from app.domain.application_error import ApplicationError
from app.domain.source_role import normalize_source_role

from .queries import require_project
from .source_versions import capture_expectations

from app.infrastructure.storage import store_bytes, remove_file


def list_sources(project_id: str, db: Session):
    require_project(db, project_id)
    return db.scalars(select(Source).where(Source.project_id == project_id).order_by(Source.created_at.desc())).all()


def upload_source(project_id: str, filename: str, raw: bytes, role: str, db: Session, replaces_source_id: str | None = None):
    require_project(db, project_id)
    name = Path(filename or "upload").name
    suffix = Path(name).suffix.lower()
    kind = (SourceKind.CODE_ZIP if suffix == ".zip" else SourceKind.MARKDOWN if suffix in {".md", ".markdown"}
            else SourceKind.CSV if suffix == ".csv" else SourceKind.XLSX if suffix == ".xlsx" else None)
    if not kind:
        raise ApplicationError(400, "ZIP, Markdown, CSV, XLSX 파일만 업로드할 수 있습니다.")
    previous = None
    expectations = {}
    if replaces_source_id:
        previous = db.get(Source, replaces_source_id)
        if not previous or previous.project_id != project_id:
            raise ApplicationError(404, '업데이트할 소스를 찾을 수 없습니다.')
        if previous.status != JobStatus.COMPLETED:
            raise ApplicationError(409, '분석이 완료된 소스만 업데이트할 수 있습니다.')
        if previous.kind != kind:
            raise ApplicationError(400, '기존 소스와 같은 파일 형식으로 업데이트해 주세요.')
        expectations = capture_expectations(db, previous)
        role = previous.role
    role = normalize_source_role(role)
    if len(raw) > settings.max_upload_bytes:
        raise ApplicationError(413, "업로드 크기 제한을 초과했습니다.")
    digest = hashlib.sha256(raw).hexdigest()
    storage_key = f"{project_id}/{digest}-{name}"
    store_bytes(storage_key, raw)
    source = Source(project_id=project_id, kind=kind, role=role, name=name, storage_key=storage_key, content_hash=digest)
    db.add(source)
    db.flush()
    if previous:
        db.add(SourceVersion(source_id=source.id, previous_source_id=previous.id, expected_policies=expectations))
    job = AnalysisJob(project_id=project_id, source_id=source.id)
    db.add(job)
    db.commit()
    db.refresh(source)
    return source, job.id


def update_source_role(source_id: str, payload: SourceRoleUpdate, db: Session):
    source = db.get(Source, source_id)
    if not source:
        raise ApplicationError(404, "Source를 찾을 수 없습니다.")
    source.role = normalize_source_role(payload.role)
    db.commit()
    db.refresh(source)
    return source


def delete_source(source_id: str, db: Session) -> None:
    source = db.scalar(select(Source).where(Source.id == source_id).with_for_update())
    if not source:
        raise ApplicationError(404, "Source를 찾을 수 없습니다.")
    if source.status in {JobStatus.PENDING, JobStatus.PROCESSING}:
        raise ApplicationError(409, "분석 중인 Source는 삭제할 수 없습니다. 분석이 끝난 뒤 다시 시도하세요.")

    if db.scalar(select(SourceVersion.source_id).where(SourceVersion.previous_source_id == source_id).limit(1)):
        raise ApplicationError(409, '소스 업데이트 이력에서 참조 중인 소스는 삭제할 수 없습니다.')

    evidence_count = db.scalar(
        select(func.count()).select_from(PolicyEvidence)
        .join(SourceChunk, PolicyEvidence.source_chunk_id == SourceChunk.id)
        .join(SourceFile, SourceChunk.source_file_id == SourceFile.id)
        .where(SourceFile.source_id == source_id)
    ) or 0
    if evidence_count:
        raise ApplicationError(409, "승인된 Policy의 근거로 사용 중인 Source는 삭제할 수 없습니다.")

    file_ids = list(db.scalars(select(SourceFile.id).where(SourceFile.source_id == source_id)))
    if file_ids:
        db.execute(delete(PolicyCandidate).where(PolicyCandidate.source_id == source_id))
        db.execute(delete(SourceChunk).where(SourceChunk.source_file_id.in_(file_ids)))
        db.execute(delete(SourceFile).where(SourceFile.id.in_(file_ids)))
    else:
        db.execute(delete(PolicyCandidate).where(PolicyCandidate.source_id == source_id))
    db.execute(delete(AnalysisJob).where(AnalysisJob.source_id == source_id))

    db.execute(delete(SourceVersion).where(SourceVersion.source_id == source_id))
    storage_key = source.storage_key
    db.delete(source)
    db.flush()
    remaining = db.scalar(select(func.count()).select_from(Source).where(Source.storage_key == storage_key)) or 0
    db.commit()

    if remaining == 0:
        remove_file(storage_key)


def get_job(job_id: str, db: Session):
    job = db.get(AnalysisJob, job_id)
    if not job:
        raise ApplicationError(404, "분석 작업을 찾을 수 없습니다.")
    return job


def analysis_progress(source_id: str, db: Session) -> SourceAnalysisOut:
    source = db.get(Source, source_id)
    if not source:
        raise ApplicationError(404, "Source를 찾을 수 없습니다.")
    job = db.scalar(select(AnalysisJob).where(AnalysisJob.source_id == source_id)
                    .order_by(AnalysisJob.created_at.desc()).limit(1))
    if not job:
        raise ApplicationError(404, "분석 작업을 찾을 수 없습니다.")
    stats = job.stats or {}
    candidates = list(db.scalars(select(PolicyCandidate).where(PolicyCandidate.source_id == source_id)
                                 .order_by(PolicyCandidate.created_at)))
    return SourceAnalysisOut(
        source_id=source.id, status=job.status, stage=job.stage, progress=job.progress,
        current_file=stats.get('current_file'), current_policy_title=stats.get('current_policy_title'),
        processed_files=stats.get('processed_files', 0), total_files=stats.get('total_files', 0),
        candidates=candidates,
    )
