from sqlalchemy import select
from sqlalchemy.orm import Session
from app.domain.application_error import ApplicationError
from app.infrastructure.models import Policy, PolicyEvidence, Source, SourceChunk, SourceFile, SourceVersion
from .chat_context import snapshot
from .queries import policy_query


def related_policies(db: Session, source_id: str) -> list[Policy]:
    ids = select(PolicyEvidence.policy_id).select_from(PolicyEvidence).join(SourceChunk, PolicyEvidence.source_chunk_id == SourceChunk.id).join(SourceFile, SourceChunk.source_file_id == SourceFile.id).where(SourceFile.source_id == source_id)
    return list(db.scalars(policy_query().where(Policy.id.in_(ids))))


def capture_expectations(db: Session, source: Source) -> dict:
    return {p.id: {**snapshot(p), 'updated_at': p.updated_at.isoformat()}
            for p in related_policies(db, source.id)}


def suggest_policy(db: Session, source: Source, chunk: SourceChunk) -> str | None:
    version = db.get(SourceVersion, source.id)
    if not version:
        return None
    rows = db.execute(select(PolicyEvidence.policy_id, SourceChunk, SourceFile.path)
                      .select_from(PolicyEvidence).join(SourceChunk, PolicyEvidence.source_chunk_id == SourceChunk.id).join(SourceFile, SourceChunk.source_file_id == SourceFile.id)
                      .where(SourceFile.source_id == version.previous_source_id)).all()
    matches = set()
    for policy_id, old, path in rows:
        same_file = source.kind.value != 'CODE_ZIP' or path == chunk.file.path
        same_location = (bool(chunk.document_path) and old.document_path == chunk.document_path
                         or bool(chunk.symbol_name) and old.symbol_name == chunk.symbol_name
                         or old.content == chunk.content)
        if same_file and same_location and policy_id in version.expected_policies:
            matches.add(policy_id)
    return next(iter(matches)) if len(matches) == 1 else None


def verify_expected(policy: Policy, version: SourceVersion) -> None:
    expected = version.expected_policies.get(policy.id)
    current = {**snapshot(policy), 'updated_at': policy.updated_at.isoformat()}
    if expected is None:
        raise ApplicationError(400, '기존 소스와 연결된 정책만 갱신할 수 있습니다.')
    if expected != current:
        raise ApplicationError(409, '분석 이후 정책이 변경되었습니다. 최신 소스를 다시 업로드해 검토해 주세요.')
