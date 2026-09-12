import hashlib
import logging
import re
from collections import defaultdict
from datetime import datetime
from pathlib import Path

from fastapi import BackgroundTasks, Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import delete, func, or_, select, update
from sqlalchemy.orm import Session, selectinload

from .analysis.pipeline import run_analysis
from .config import settings
from .db import Base, engine, get_db
from .models import (
    AnalysisJob, CandidateDecision, JobStatus, Policy, PolicyCandidate, PolicyConflict,
    PolicyEvidence, PolicyRule, PolicyStatus, Project, Source, SourceChunk, SourceFile, SourceKind,
)
from .schemas import (
    CandidateDetail, CandidateOut, CandidateReview, ChatCitation, ChatRequest, ChatResponse,
    DashboardOut, JobOut, NavigationItem, PolicyOut, PolicyUpdate, ProjectCreate, ProjectOut,
    SourceOut, SourceRoleUpdate,
)

app = FastAPI(title="Policy Docs API", version="0.1.0")
logger = logging.getLogger(__name__)
app.add_middleware(CORSMiddleware, allow_origins=[settings.web_origin], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])


@app.on_event("startup")
def startup() -> None:
    logging.getLogger("uvicorn.error").info(
        "Policy Docs API configuration ai_enabled=%s model=%s",
        bool(settings.llm_api_key), settings.llm_model,
    )
    settings.storage_path.mkdir(parents=True, exist_ok=True)
    if engine.dialect.name == "postgresql":
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
            enum_exists = connection.exec_driver_sql(
                "SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'sourcekind')"
            ).scalar()
            if enum_exists:
                connection.exec_driver_sql("ALTER TYPE sourcekind ADD VALUE IF NOT EXISTS 'XLSX'")
    Base.metadata.create_all(engine)
    _recover_interrupted_analysis_jobs()


def _recover_interrupted_analysis_jobs() -> None:
    """In-process background jobs cannot survive an API process restart."""
    interrupted = {JobStatus.PENDING, JobStatus.PROCESSING}
    message = "API가 재시작되어 분석이 중단되었습니다. Source를 삭제한 뒤 다시 업로드하세요."
    with Session(engine) as db:
        source_count = db.execute(
            update(Source).where(Source.status.in_(interrupted)).values(
                status=JobStatus.FAILED,
                error_message=message,
            )
        ).rowcount
        job_count = db.execute(
            update(AnalysisJob).where(AnalysisJob.status.in_(interrupted)).values(
                status=JobStatus.FAILED,
                stage="failed",
                error_message=message,
                completed_at=datetime.utcnow(),
            )
        ).rowcount
        db.commit()
    if source_count or job_count:
        logging.getLogger("uvicorn.error").warning(
            "Recovered interrupted analysis state sources=%s jobs=%s", source_count, job_count,
        )


def require_project(db: Session, project_id: str) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise HTTPException(404, "Project를 찾을 수 없습니다.")
    return project


def policy_query():
    return select(Policy).options(selectinload(Policy.rules), selectinload(Policy.evidence))


def normalize_source_role(role: str) -> str:
    normalized = role.strip()
    if not normalized or len(normalized) > 50 or not re.fullmatch(r"[\w가-힣 ./_-]+", normalized):
        raise HTTPException(400, "역할은 1~50자의 문자, 숫자, 공백, ., /, _, -만 사용할 수 있습니다.")
    return normalized


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/projects", response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    return db.scalars(select(Project).order_by(Project.created_at.desc())).all()


@app.post("/projects", response_model=ProjectOut, status_code=201)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    project = Project(name=payload.name.strip(), description=payload.description)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


@app.get("/projects/{project_id}", response_model=ProjectOut)
def get_project(project_id: str, db: Session = Depends(get_db)):
    return require_project(db, project_id)


@app.get("/projects/{project_id}/dashboard", response_model=DashboardOut)
def dashboard(project_id: str, db: Session = Depends(get_db)):
    require_project(db, project_id)
    scalar = lambda statement: db.scalar(statement) or 0
    return DashboardOut(
        source_count=scalar(select(func.count()).select_from(Source).where(Source.project_id == project_id)),
        policy_count=scalar(select(func.count()).select_from(Policy).where(Policy.project_id == project_id)),
        review_count=scalar(select(func.count()).select_from(PolicyCandidate).where(
            PolicyCandidate.project_id == project_id, PolicyCandidate.decision == CandidateDecision.PENDING)),
        conflict_count=scalar(select(func.count()).select_from(PolicyConflict).join(Policy).where(
            Policy.project_id == project_id, PolicyConflict.status == "OPEN")),
    )


def _process_job(source_id: str, job_id: str) -> None:
    with Session(engine) as db:
        run_analysis(db, db.get(Source, source_id), db.get(AnalysisJob, job_id))


@app.get("/projects/{project_id}/sources", response_model=list[SourceOut])
def list_sources(project_id: str, db: Session = Depends(get_db)):
    require_project(db, project_id)
    return db.scalars(select(Source).where(Source.project_id == project_id).order_by(Source.created_at.desc())).all()


@app.post("/projects/{project_id}/sources", response_model=SourceOut, status_code=201)
async def upload_source(background: BackgroundTasks, project_id: str, file: UploadFile = File(...),
                        role: str = Form("document"), db: Session = Depends(get_db)):
    require_project(db, project_id)
    name = Path(file.filename or "upload").name
    suffix = Path(name).suffix.lower()
    kind = (SourceKind.CODE_ZIP if suffix == ".zip" else SourceKind.MARKDOWN if suffix in {".md", ".markdown"}
            else SourceKind.CSV if suffix == ".csv" else SourceKind.XLSX if suffix == ".xlsx" else None)
    if not kind:
        raise HTTPException(400, "ZIP, Markdown, CSV, XLSX 파일만 업로드할 수 있습니다.")
    role = normalize_source_role(role)
    raw = await file.read(settings.max_upload_bytes + 1)
    if len(raw) > settings.max_upload_bytes:
        raise HTTPException(413, "업로드 크기 제한을 초과했습니다.")
    digest = hashlib.sha256(raw).hexdigest()
    storage_key = f"{project_id}/{digest}-{name}"
    destination = settings.storage_path / storage_key
    destination.parent.mkdir(parents=True, exist_ok=True)
    if not destination.exists():
        destination.write_bytes(raw)
    source = Source(project_id=project_id, kind=kind, role=role, name=name, storage_key=storage_key, content_hash=digest)
    db.add(source)
    db.flush()
    job = AnalysisJob(project_id=project_id, source_id=source.id)
    db.add(job)
    db.commit()
    db.refresh(source)
    background.add_task(_process_job, source.id, job.id)
    return source


@app.patch("/sources/{source_id}/role", response_model=SourceOut)
def update_source_role(source_id: str, payload: SourceRoleUpdate, db: Session = Depends(get_db)):
    source = db.get(Source, source_id)
    if not source:
        raise HTTPException(404, "Source를 찾을 수 없습니다.")
    source.role = normalize_source_role(payload.role)
    db.commit()
    db.refresh(source)
    return source


@app.delete("/sources/{source_id}", status_code=204)
def delete_source(source_id: str, db: Session = Depends(get_db)) -> None:
    source = db.scalar(select(Source).where(Source.id == source_id).with_for_update())
    if not source:
        raise HTTPException(404, "Source를 찾을 수 없습니다.")
    if source.status in {JobStatus.PENDING, JobStatus.PROCESSING}:
        raise HTTPException(409, "분석 중인 Source는 삭제할 수 없습니다. 분석이 끝난 뒤 다시 시도하세요.")

    evidence_count = db.scalar(
        select(func.count()).select_from(PolicyEvidence)
        .join(SourceChunk, PolicyEvidence.source_chunk_id == SourceChunk.id)
        .join(SourceFile, SourceChunk.source_file_id == SourceFile.id)
        .where(SourceFile.source_id == source_id)
    ) or 0
    if evidence_count:
        raise HTTPException(409, "승인된 Policy의 근거로 사용 중인 Source는 삭제할 수 없습니다.")

    file_ids = list(db.scalars(select(SourceFile.id).where(SourceFile.source_id == source_id)))
    if file_ids:
        db.execute(delete(PolicyCandidate).where(PolicyCandidate.source_id == source_id))
        db.execute(delete(SourceChunk).where(SourceChunk.source_file_id.in_(file_ids)))
        db.execute(delete(SourceFile).where(SourceFile.id.in_(file_ids)))
    else:
        db.execute(delete(PolicyCandidate).where(PolicyCandidate.source_id == source_id))
    db.execute(delete(AnalysisJob).where(AnalysisJob.source_id == source_id))

    storage_key = source.storage_key
    db.delete(source)
    db.flush()
    remaining = db.scalar(select(func.count()).select_from(Source).where(Source.storage_key == storage_key)) or 0
    db.commit()

    if remaining == 0:
        storage_root = settings.storage_path.resolve()
        stored_file = (storage_root / storage_key).resolve()
        if stored_file.is_relative_to(storage_root):
            try:
                stored_file.unlink(missing_ok=True)
            except OSError:
                logger.warning("Deleted Source record but could not remove stored file: %s", stored_file)


@app.get("/analysis-jobs/{job_id}", response_model=JobOut)
def get_job(job_id: str, db: Session = Depends(get_db)):
    job = db.get(AnalysisJob, job_id)
    if not job:
        raise HTTPException(404, "분석 작업을 찾을 수 없습니다.")
    return job


def candidate_detail(candidate: PolicyCandidate, db: Session) -> CandidateDetail:
    source = db.get(Source, candidate.source_id)
    chunk = candidate.chunk
    return CandidateDetail(
        id=candidate.id, project_id=candidate.project_id, source_id=candidate.source_id,
        proposed_policy_id=candidate.proposed_policy_id, title=candidate.title, summary=candidate.summary,
        category=candidate.category, rules=candidate.rules, confidence=candidate.confidence,
        decision=candidate.decision, created_at=candidate.created_at, source_path=chunk.file.path,
        start_line=chunk.start_line, end_line=chunk.end_line, excerpt=chunk.content,
        source_type=source.role, source_name=source.name,
    )


@app.get("/projects/{project_id}/policy-candidates", response_model=list[CandidateOut])
def list_candidates(project_id: str, decision: CandidateDecision = CandidateDecision.PENDING, db: Session = Depends(get_db)):
    require_project(db, project_id)
    return db.scalars(select(PolicyCandidate).where(
        PolicyCandidate.project_id == project_id, PolicyCandidate.decision == decision).order_by(PolicyCandidate.confidence.desc())).all()


@app.get("/policy-candidates/{candidate_id}", response_model=CandidateDetail)
def get_candidate(candidate_id: str, db: Session = Depends(get_db)):
    candidate = db.scalar(select(PolicyCandidate).options(selectinload(PolicyCandidate.chunk).selectinload(SourceChunk.file)).where(PolicyCandidate.id == candidate_id))
    if not candidate:
        raise HTTPException(404, "후보를 찾을 수 없습니다.")
    return candidate_detail(candidate, db)


def apply_review(candidate: PolicyCandidate, payload: CandidateReview, db: Session, merge: bool) -> Policy:
    if candidate.decision != CandidateDecision.PENDING:
        raise HTTPException(409, "이미 검토된 후보입니다.")
    if merge:
        if not payload.target_policy_id:
            raise HTTPException(400, "병합할 Policy가 필요합니다.")
        policy = db.scalar(policy_query().where(Policy.id == payload.target_policy_id, Policy.project_id == candidate.project_id))
        if not policy:
            raise HTTPException(404, "병합할 Policy를 찾을 수 없습니다.")
        candidate.decision = CandidateDecision.MERGED
    else:
        policy = Policy(project_id=candidate.project_id, title=payload.title, summary=payload.summary,
                        category=payload.category, confidence=candidate.confidence, status=PolicyStatus.APPROVED,
                        approved_at=datetime.utcnow())
        db.add(policy)
        db.flush()
        candidate.decision = CandidateDecision.APPROVED
    existing = {rule.content for rule in policy.rules}
    for index, content in enumerate(payload.rules):
        if content not in existing:
            policy.rules.append(PolicyRule(content=content, sort_order=len(policy.rules) + index))
    chunk, source = candidate.chunk, db.get(Source, candidate.source_id)
    policy.evidence.append(PolicyEvidence(source_chunk_id=chunk.id, source_type=source.role, source_name=source.name,
        source_path=chunk.file.path, start_line=chunk.start_line, end_line=chunk.end_line, excerpt=chunk.content,
        extracted_claim=payload.summary, confidence=candidate.confidence))
    policy.search_text = " ".join([policy.title, policy.summary, policy.category, *[r.content for r in policy.rules]])
    candidate.reviewed_at = datetime.utcnow()
    db.commit()
    return db.scalar(policy_query().where(Policy.id == policy.id))


@app.post("/policy-candidates/{candidate_id}/approve", response_model=PolicyOut)
def approve_candidate(candidate_id: str, payload: CandidateReview, db: Session = Depends(get_db)):
    candidate = db.scalar(select(PolicyCandidate).options(selectinload(PolicyCandidate.chunk).selectinload(SourceChunk.file)).where(PolicyCandidate.id == candidate_id))
    if not candidate:
        raise HTTPException(404, "후보를 찾을 수 없습니다.")
    return apply_review(candidate, payload, db, False)


@app.post("/policy-candidates/{candidate_id}/merge", response_model=PolicyOut)
def merge_candidate(candidate_id: str, payload: CandidateReview, db: Session = Depends(get_db)):
    candidate = db.scalar(select(PolicyCandidate).options(selectinload(PolicyCandidate.chunk).selectinload(SourceChunk.file)).where(PolicyCandidate.id == candidate_id))
    if not candidate:
        raise HTTPException(404, "후보를 찾을 수 없습니다.")
    return apply_review(candidate, payload, db, True)


@app.post("/policy-candidates/{candidate_id}/reject", status_code=204)
def reject_candidate(candidate_id: str, db: Session = Depends(get_db)):
    candidate = db.get(PolicyCandidate, candidate_id)
    if not candidate:
        raise HTTPException(404, "후보를 찾을 수 없습니다.")
    candidate.decision, candidate.reviewed_at = CandidateDecision.REJECTED, datetime.utcnow()
    db.commit()


@app.get("/projects/{project_id}/policies", response_model=list[PolicyOut])
def list_policies(project_id: str, status: PolicyStatus | None = None, db: Session = Depends(get_db)):
    require_project(db, project_id)
    query = policy_query().where(Policy.project_id == project_id)
    if status:
        query = query.where(Policy.status == status)
    return db.scalars(query.order_by(Policy.category, Policy.title)).all()


@app.get("/policies/{policy_id}", response_model=PolicyOut)
def get_policy(policy_id: str, db: Session = Depends(get_db)):
    policy = db.scalar(policy_query().where(Policy.id == policy_id))
    if not policy:
        raise HTTPException(404, "Policy를 찾을 수 없습니다.")
    return policy


@app.patch("/policies/{policy_id}", response_model=PolicyOut)
def update_policy(policy_id: str, payload: PolicyUpdate, db: Session = Depends(get_db)):
    policy = db.scalar(policy_query().where(Policy.id == policy_id))
    if not policy:
        raise HTTPException(404, "Policy를 찾을 수 없습니다.")
    for field in ("title", "summary", "category"):
        value = getattr(payload, field)
        if value is not None:
            setattr(policy, field, value)
    if payload.rules is not None:
        policy.rules.clear()
        policy.rules.extend(PolicyRule(content=content, sort_order=i) for i, content in enumerate(payload.rules))
    policy.search_text = " ".join([policy.title, policy.summary, policy.category, *[r.content for r in policy.rules]])
    db.commit()
    return db.scalar(policy_query().where(Policy.id == policy.id))


@app.get("/projects/{project_id}/docs/navigation", response_model=list[NavigationItem])
def docs_navigation(project_id: str, db: Session = Depends(get_db)):
    policies = db.scalars(select(Policy).where(Policy.project_id == project_id, Policy.status == PolicyStatus.APPROVED)
                          .order_by(Policy.category, Policy.title)).all()
    grouped = defaultdict(list)
    for policy in policies:
        grouped[policy.category].append({"id": policy.id, "title": policy.title})
    return [NavigationItem(category=category, policies=items) for category, items in grouped.items()]


def tokens(text: str) -> set[str]:
    return {word.lower() for word in re.findall(r"[\w가-힣]{2,}", text)}


@app.post("/projects/{project_id}/chat", response_model=ChatResponse)
def chat(project_id: str, payload: ChatRequest, db: Session = Depends(get_db)):
    require_project(db, project_id)
    policies = db.scalars(policy_query().where(Policy.project_id == project_id, Policy.status == PolicyStatus.APPROVED)).all()
    question_tokens = tokens(payload.question)
    ranked = sorted(((len(question_tokens & tokens(policy.search_text)), policy) for policy in policies), key=lambda item: item[0], reverse=True)
    selected = [policy for score, policy in ranked[:payload.top_k] if score > 0]
    if not selected:
        return ChatResponse(answer="현재 등록된 정책에서 해당 내용을 찾을 수 없습니다.", grounded=False,
                            related_policies=[], citations=[])
    citations = [ChatCitation(policy_id=p.id, policy_title=p.title, source_path=e.source_path,
                              lines=f"{e.start_line}-{e.end_line}") for p in selected for e in p.evidence]
    summaries = "\n".join(f"- {p.title}: {p.summary}" for p in selected)
    conflict_note = "\n⚠ 관련 정책에 해결되지 않은 충돌이 있습니다." if any(p.has_conflict for p in selected) else ""
    return ChatResponse(answer=f"등록된 승인 정책에서 다음 내용을 확인했습니다.\n{summaries}{conflict_note}", grounded=True,
                        related_policies=selected, citations=citations)
