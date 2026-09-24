import json
import logging
from sqlalchemy.orm import Session
from app.application.dto import ChatRequest, ChatResponse
from app.config import settings
from app.domain.application_error import ApplicationError
from app.domain.chat_intent import requests_policy_edit
from app.domain.search import tokens
from app.infrastructure import chat_llm
from app.infrastructure.models import Policy, PolicyStatus
from .chat_context import citations_for, context_for, rank_policies
from .chat_source_guidance import source_guidance
from .queries import require_project, policy_query

logger = logging.getLogger(__name__)


def reply(answer: str, action: str = 'clarify') -> ChatResponse:
    return ChatResponse(answer=answer, grounded=False, related_policies=[], citations=[], action=action)


def fallback(db: Session, project_id: str, payload: ChatRequest, unavailable: bool) -> ChatResponse:
    policies = db.scalars(policy_query().where(Policy.project_id == project_id, Policy.status == PolicyStatus.APPROVED)).all()
    selected = [p for p in rank_policies(policies, payload.question, payload.policy_id)
                if p.id == payload.policy_id or tokens(payload.question) & tokens(p.search_text)][:payload.top_k]
    if not selected:
        return reply('현재 승인된 정책에서 질문의 근거를 찾지 못했습니다. 정책 이름이나 조건을 구체적으로 알려주세요.')
    text = '\n\n'.join(f'{p.title}\n{p.summary}\n' + '\n'.join(f'• {r.content}' for r in p.rules) for p in selected)
    notice = 'AI 답변을 사용할 수 없어 관련 승인 정책을 그대로 안내합니다.\n\n' if unavailable else ''
    return ChatResponse(answer=notice + text, grounded=True, related_policies=selected,
                        citations=citations_for(db, selected))


def chat(project_id: str, payload: ChatRequest, db: Session) -> ChatResponse:
    require_project(db, project_id)
    policies = list(db.scalars(policy_query().where(Policy.project_id == project_id, Policy.status == PolicyStatus.APPROVED)))
    if payload.policy_id and not any(p.id == payload.policy_id for p in policies):
        raise ApplicationError(404, '이 프로젝트의 승인된 정책을 선택해 주세요.')
    if not policies:
        return reply('승인된 정책이 없습니다. 정책 관리에서 후보를 먼저 승인해 주세요.')
    if requests_policy_edit(payload.question):
        targets = ([p for p in policies if p.id == payload.policy_id] if payload.policy_id
                   else [p for p in rank_policies(policies, payload.question, None)
                         if p.title in payload.question or tokens(payload.question) & tokens(p.search_text)][:payload.top_k])
        return source_guidance(db, targets)
    if not settings.llm_api_key:
        return fallback(db, project_id, payload, True)
    selected = ([p for p in policies if p.id == payload.policy_id] if payload.policy_id
                else rank_policies(policies, payload.question, None)[:40])
    context = context_for(db, selected)
    if len(json.dumps(context, ensure_ascii=False)) > 100000:
        return reply('정책 내용이 많습니다. 대상 정책을 선택해 질문해 주세요.') if not payload.policy_id else reply(
            '선택한 정책의 내용이 너무 길어 처리하지 못했습니다. 정책은 변경되지 않았습니다.')
    # Do not retain a database transaction during a remote model call.
    db.rollback()
    try:
        decision = chat_llm.decide(payload, context)
    except Exception as exc:
        logger.warning('Policy chat unavailable error_type=%s', type(exc).__name__)
        return fallback(db, project_id, payload, True)
    allowed = {item['id']: item for item in context}
    if any(key not in allowed for key in decision.policy_ids):
        return reply('답변의 정책 근거를 확인하지 못했습니다. 정책을 선택해 다시 질문해 주세요.')
    if decision.action == 'update_source':
        ids = decision.policy_ids or ([payload.policy_id] if payload.policy_id else [])
        current = list(db.scalars(policy_query().where(Policy.id.in_(ids), Policy.project_id == project_id,
                                                       Policy.status == PolicyStatus.APPROVED)))
        return source_guidance(db, current)
    if decision.action == 'clarify' or not decision.policy_ids:
        return reply(decision.answer)
    ids = list(dict.fromkeys(decision.policy_ids))
    if len(ids) > payload.top_k:
        return reply('관련 정책이 많습니다. 대상 정책을 선택해 질문 범위를 좁혀 주세요.')
    current = list(db.scalars(policy_query().where(Policy.id.in_(ids), Policy.project_id == project_id,
                                                 Policy.status == PolicyStatus.APPROVED)))
    current_context = {item['id']: item for item in context_for(db, current)}
    if any(current_context.get(key) != allowed[key] for key in ids):
        return reply('답변을 만드는 동안 정책이 변경되었습니다. 최신 정책으로 다시 질문해 주세요.')
    note = '\n관련 정책에 해결되지 않은 충돌이 있습니다.' if any(p.has_conflict for p in current) else ''
    return ChatResponse(answer=decision.answer + note, grounded=True, related_policies=current,
                        citations=citations_for(db, current))
