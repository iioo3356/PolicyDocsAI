from app.domain.clock import utc_now_naive
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from app.infrastructure.models import CandidateDecision, JobStatus, Policy, PolicyCandidate, PolicyEvidence, PolicyRule, PolicyStatus, Source, SourceChunk, SourceVersion
from app.application.dto import CandidateDetail, CandidateReview
from app.domain.application_error import ApplicationError

from .queries import require_project, policy_query
from .source_versions import related_policies
from .source_policy_review import apply_source_update


def candidate_detail(candidate: PolicyCandidate, db: Session) -> CandidateDetail:
    source = db.get(Source, candidate.source_id)
    chunk = candidate.chunk
    version = db.get(SourceVersion, source.id)
    return CandidateDetail(
        id=candidate.id, project_id=candidate.project_id, source_id=candidate.source_id,
        proposed_policy_id=candidate.proposed_policy_id, title=candidate.title, summary=candidate.summary,
        category=candidate.category, rules=candidate.rules, confidence=candidate.confidence,
        decision=candidate.decision, created_at=candidate.created_at, source_path=chunk.file.path,
        start_line=chunk.start_line, end_line=chunk.end_line, excerpt=chunk.content,
        source_type=source.role, source_name=source.name,
        previous_source_id=version.previous_source_id if version else None,
        related_policies=related_policies(db, version.previous_source_id) if version else [],
    )


def list_candidates(project_id: str, decision: CandidateDecision, db: Session):
    require_project(db, project_id)
    return db.scalars(select(PolicyCandidate).join(Source, Source.id == PolicyCandidate.source_id).where(
        PolicyCandidate.project_id == project_id, PolicyCandidate.decision == decision,
        Source.status == JobStatus.COMPLETED).order_by(PolicyCandidate.confidence.desc())).all()


def get_candidate(candidate_id: str, db: Session):
    candidate = db.scalar(select(PolicyCandidate).options(selectinload(PolicyCandidate.chunk).selectinload(SourceChunk.file)).where(PolicyCandidate.id == candidate_id).with_for_update())
    if not candidate:
        raise ApplicationError(404, "후보를 찾을 수 없습니다.")
    return candidate_detail(candidate, db)


def apply_review(candidate: PolicyCandidate, payload: CandidateReview, db: Session, merge: bool) -> Policy:
    if candidate.decision != CandidateDecision.PENDING:
        raise ApplicationError(409, "이미 검토된 후보입니다.")
    if db.get(Source, candidate.source_id).status != JobStatus.COMPLETED:
        raise ApplicationError(409, "소스 분석이 완료된 뒤 정책 후보를 검토해 주세요.")
    version = db.get(SourceVersion, candidate.source_id)
    if version and (payload.target_policy_id or candidate.proposed_policy_id):
        try:
            policy = apply_source_update(candidate, payload, version, db)
            candidate.decision = CandidateDecision.APPROVED
            candidate.reviewed_at = utc_now_naive()
            db.commit()
        except Exception:
            db.rollback()
            raise
        return db.scalar(policy_query().where(Policy.id == policy.id))
    if merge:
        if not payload.target_policy_id:
            raise ApplicationError(400, "병합할 Policy가 필요합니다.")
        policy = db.scalar(policy_query().where(Policy.id == payload.target_policy_id, Policy.project_id == candidate.project_id))
        if not policy:
            raise ApplicationError(404, "병합할 Policy를 찾을 수 없습니다.")
        candidate.decision = CandidateDecision.MERGED
    else:
        policy = Policy(project_id=candidate.project_id, title=payload.title, summary=payload.summary,
                        category=payload.category, confidence=candidate.confidence, status=PolicyStatus.APPROVED,
                        approved_at=utc_now_naive())
        db.add(policy)
        db.flush()
        candidate.decision = CandidateDecision.APPROVED
    existing = {rule.content for rule in policy.rules}
    for content in payload.rules:
        if content not in existing:
            policy.rules.append(PolicyRule(content=content, sort_order=len(policy.rules)))
            existing.add(content)
    chunk, source = candidate.chunk, db.get(Source, candidate.source_id)
    policy.evidence.append(PolicyEvidence(source_chunk_id=chunk.id, source_type=source.role, source_name=source.name,
        source_path=chunk.file.path, start_line=chunk.start_line, end_line=chunk.end_line, excerpt=chunk.content,
        extracted_claim=payload.summary, confidence=candidate.confidence))
    policy.search_text = " ".join([policy.title, policy.summary, policy.category, *[r.content for r in policy.rules]])
    candidate.proposed_policy_id = policy.id
    candidate.reviewed_at = utc_now_naive()
    db.commit()
    return db.scalar(policy_query().where(Policy.id == policy.id))


def approve_candidate(candidate_id: str, payload: CandidateReview, db: Session):
    candidate = db.scalar(select(PolicyCandidate).options(selectinload(PolicyCandidate.chunk).selectinload(SourceChunk.file)).where(PolicyCandidate.id == candidate_id).with_for_update())
    if not candidate:
        raise ApplicationError(404, "후보를 찾을 수 없습니다.")
    return apply_review(candidate, payload, db, False)


def merge_candidate(candidate_id: str, payload: CandidateReview, db: Session):
    candidate = db.scalar(select(PolicyCandidate).options(selectinload(PolicyCandidate.chunk).selectinload(SourceChunk.file)).where(PolicyCandidate.id == candidate_id).with_for_update())
    if not candidate:
        raise ApplicationError(404, "후보를 찾을 수 없습니다.")
    return apply_review(candidate, payload, db, True)


def reject_candidate(candidate_id: str, db: Session):
    candidate = db.scalar(select(PolicyCandidate).where(PolicyCandidate.id == candidate_id).with_for_update())
    if not candidate:
        raise ApplicationError(404, "후보를 찾을 수 없습니다.")
    if candidate.decision != CandidateDecision.PENDING:
        raise ApplicationError(409, "이미 검토된 후보입니다.")
    if db.get(Source, candidate.source_id).status != JobStatus.COMPLETED:
        raise ApplicationError(409, "소스 분석이 완료된 뒤 정책 후보를 검토해 주세요.")
    candidate.decision, candidate.reviewed_at = CandidateDecision.REJECTED, utc_now_naive()
    db.commit()
