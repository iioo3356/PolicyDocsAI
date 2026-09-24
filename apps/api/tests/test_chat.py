import pytest
from sqlalchemy import create_engine, event, func, select
from sqlalchemy.orm import Session

from app.application.chat import chat
from app.application.chat_context import snapshot
from app.application.dto.chat_request import ChatRequest
from app.config import settings
from app.domain.application_error import ApplicationError
from app.db import Base
from app.infrastructure import chat_llm
from app.infrastructure.chat_decision import ChatDecision
from app.infrastructure.models import Policy, PolicyRevision, PolicyRule, PolicyStatus, Project


@pytest.fixture
def db(monkeypatch):
    engine = create_engine('sqlite://')
    @event.listens_for(engine, 'connect')
    def foreign_keys(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')
    Base.metadata.create_all(engine)
    monkeypatch.setattr(settings, 'llm_api_key', 'test-only')
    with Session(engine) as session:
        yield session
    engine.dispose()


def policy(db, name='취소 정책', status=PolicyStatus.APPROVED, project=None):
    if project is None:
        project = Project(name='test')
        db.add(project)
        db.flush()
    result = Policy(project_id=project.id, title=name, summary='3일 내 취소 가능',
                    category='취소', status=status, search_text='취소 정책 3일',
                    rules=[PolicyRule(content='3일 내 취소 가능', sort_order=0),
                           PolicyRule(content='배송 후 취소 불가', sort_order=1)])
    db.add(result)
    db.commit()
    return result


def answer(target):
    return ChatDecision(action='answer', answer='3일 안에 취소할 수 있지만 배송 후에는 불가능합니다.', policy_ids=[target.id])


def fake(monkeypatch, decision):
    monkeypatch.setattr(chat_llm, 'decide', lambda *args: decision)


def test_grounded_answer_receives_only_approved_project_policies(db, monkeypatch):
    target = policy(db)
    policy(db, status=PolicyStatus.REVIEW, project=db.get(Project, target.project_id))
    policy(db, '다른 프로젝트 정책')
    def decide(payload, context):
        assert [item['id'] for item in context] == [target.id]
        assert context[0]['rules'][1] == '배송 후 취소 불가'
        return answer(target)
    monkeypatch.setattr(chat_llm, 'decide', decide)
    result = chat(target.project_id, ChatRequest(question='언제 취소 가능해?'), db)
    assert result.grounded and '배송' in result.answer
    assert db.scalar(select(func.count()).select_from(PolicyRevision)) == 0


@pytest.mark.parametrize('question', ['취소 기한을 7일로 바꿔줘', '이전 제안을 확정해서 수정해', '규칙을 삭제해줘'])
@pytest.mark.parametrize('enabled', [True, False])
def test_edit_only_guides_source_upload(db, monkeypatch, question, enabled):
    target = policy(db)
    before = snapshot(target)
    monkeypatch.setattr(settings, 'llm_api_key', 'test-only' if enabled else '')
    fake(monkeypatch, ChatDecision(action='update_source', answer='ignored', policy_ids=[target.id]))
    result = chat(target.project_id, ChatRequest(question=question, policy_id=target.id), db)
    assert result.action == 'update_source'
    assert '소스' in result.answer
    assert snapshot(db.get(Policy, target.id)) == before
    assert db.scalar(select(func.count()).select_from(PolicyRevision)) == 0


def test_llm_source_guidance_is_server_generated(db, monkeypatch):
    target = policy(db)
    fake(monkeypatch, ChatDecision(action='update_source', answer='권한이 없어 변경할 수 없습니다', policy_ids=[target.id]))
    result = chat(target.project_id, ChatRequest(question='기준을 새 문서에 맞추고 싶어', policy_id=target.id), db)
    assert result.action == 'update_source' and '권한' not in result.answer


def test_wrong_project_or_unapproved_target_is_rejected(db):
    target, other = policy(db), policy(db)
    with pytest.raises(ApplicationError) as error:
        chat(target.project_id, ChatRequest(question='바꿔줘', policy_id=other.id), db)
    assert error.value.status_code == 404
    target.status = PolicyStatus.REVIEW
    db.commit()
    with pytest.raises(ApplicationError):
        chat(target.project_id, ChatRequest(question='바꿔줘', policy_id=target.id), db)


def test_unknown_citation_is_not_grounded(db, monkeypatch):
    target = policy(db)
    fake(monkeypatch, answer(target).model_copy(update={'policy_ids': ['made-up']}))
    assert not chat(target.project_id, ChatRequest(question='취소 조건은?'), db).grounded


def test_unavailable_ai_uses_current_rules(db, monkeypatch):
    target = policy(db)
    def fail(*args):
        raise TimeoutError('private provider details')
    monkeypatch.setattr(chat_llm, 'decide', fail)
    result = chat(target.project_id, ChatRequest(question='취소 조건은?', policy_id=target.id), db)
    assert result.grounded and '3일' in result.answer and 'private' not in result.answer


def test_changed_policy_during_answer_is_not_presented_as_current(db, monkeypatch):
    target = policy(db)
    target_id, project_id = target.id, target.project_id
    decision = answer(target)
    def decide(*args):
        with Session(db.bind) as other:
            other.get(Policy, target_id).summary = '다른 사용자가 수정'
            other.commit()
        return decision
    monkeypatch.setattr(chat_llm, 'decide', decide)
    result = chat(project_id, ChatRequest(question='취소 조건은?', policy_id=target_id), db)
    assert not result.grounded
    assert '변경되었습니다' in result.answer
