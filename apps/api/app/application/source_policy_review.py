from sqlalchemy.orm import Session
from app.domain.application_error import ApplicationError
from app.domain.clock import utc_now_naive
from app.infrastructure.models import Policy, PolicyCandidate, PolicyEvidence, PolicyRevision, PolicyRule, PolicyStatus, Source, SourceVersion
from .chat_context import snapshot
from .queries import policy_query
from .source_versions import verify_expected


def apply_source_update(candidate: PolicyCandidate, payload, version: SourceVersion, db: Session) -> Policy:
    target_id = payload.target_policy_id or candidate.proposed_policy_id
    policy = db.scalar(policy_query().where(Policy.id == target_id,
                       Policy.project_id == candidate.project_id).with_for_update())
    if not policy or policy.status != PolicyStatus.APPROVED:
        raise ApplicationError(404, '업데이트할 승인 정책을 찾을 수 없습니다.')
    verify_expected(policy, version)
    before = snapshot(policy)
    policy.title, policy.summary, policy.category = payload.title, payload.summary, payload.category
    policy.rules[:] = [PolicyRule(content=content, sort_order=index) for index, content in enumerate(payload.rules)]
    policy.updated_at = utc_now_naive()
    policy.confidence = candidate.confidence
    policy.search_text = ' '.join([policy.title, policy.summary, policy.category, *payload.rules])
    source, chunk = db.get(Source, candidate.source_id), candidate.chunk
    policy.evidence.append(PolicyEvidence(source_chunk_id=chunk.id, source_type=source.role, source_name=source.name,
        source_path=chunk.file.path, start_line=chunk.start_line, end_line=chunk.end_line, excerpt=chunk.content,
        extracted_claim=payload.summary, confidence=candidate.confidence))
    after = {**snapshot(policy), '_source': {'source_id': source.id, 'previous_source_id': version.previous_source_id,
                                           'candidate_id': candidate.id, 'source_chunk_id': chunk.id,
                                           'name': source.name, 'path': chunk.file.path}}
    db.add(PolicyRevision(project_id=policy.project_id, policy_id=policy.id,
                          instruction=f'소스 업데이트 승인: {source.name}', before=before, after=after))
    candidate.proposed_policy_id = policy.id
    return policy
