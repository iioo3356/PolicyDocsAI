from sqlalchemy import select
from sqlalchemy.orm import Session
from app.application.dto import ChatCitation
from app.domain.search import tokens
from app.infrastructure.models import Policy, PolicyRevision


def snapshot(policy: Policy) -> dict:
    return {'title': policy.title, 'summary': policy.summary, 'category': policy.category,
            'rules': [rule.content for rule in policy.rules]}


def latest_revision(db: Session, policy_id: str) -> PolicyRevision | None:
    return db.scalar(select(PolicyRevision).where(PolicyRevision.policy_id == policy_id)
                     .order_by(PolicyRevision.created_at.desc(), PolicyRevision.id.desc()).limit(1))


def rank_policies(policies: list[Policy], question: str, target: str | None) -> list[Policy]:
    words = tokens(question)
    def score(policy):
        text = ' '.join([policy.title, policy.category, policy.summary, *[r.content for r in policy.rules]])
        return (policy.id == target, len(words & tokens(text)), policy.title in question)
    return sorted(policies, key=score, reverse=True)


def context_for(db: Session, policies: list[Policy]) -> list[dict]:
    context = []
    for policy in policies:
        revision = latest_revision(db, policy.id)
        context.append({'id': policy.id, **snapshot(policy), 'has_conflict': policy.has_conflict,
                        'last_revision': revision.instruction if revision else None,
                        'updated_at': policy.updated_at.isoformat()})
    return context


def citations_for(db: Session, policies: list[Policy]) -> list[ChatCitation]:
    citations = []
    for policy in policies:
        revision = latest_revision(db, policy.id)
        source_update = revision.after.get('_source') if revision else None
        if source_update:
            evidence = [e for e in policy.evidence if e.source_chunk_id == source_update['source_chunk_id']]
            citations.extend(ChatCitation(policy_id=policy.id, policy_title=policy.title, source_path=e.source_path,
                                          lines=f'{e.start_line}-{e.end_line}') for e in evidence)
        elif revision:
            citations.append(ChatCitation(policy_id=policy.id, policy_title=policy.title,
                                          source_path='이전 정책 수정 이력', lines='', kind='revision', revision_id=revision.id))
        else:
            citations.extend(ChatCitation(policy_id=policy.id, policy_title=policy.title,
                                          source_path=e.source_path, lines=f'{e.start_line}-{e.end_line}')
                             for e in policy.evidence)
        if not revision and not policy.evidence:
            citations.append(ChatCitation(policy_id=policy.id, policy_title=policy.title,
                                          source_path='승인된 정책 문서', lines='', kind='policy'))
    return citations
