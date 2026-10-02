import json
import sys
from types import SimpleNamespace

import pytest
from app.application import chat as service
from app.application.dto.chat_request import ChatRequest
from app.config import settings
from app.domain.partial_json_answer import partial_answer
from app.infrastructure import chat_llm
from app.infrastructure.chat_decision import ChatDecision
from test_chat import db, policy
from test_api_workflow import client, project


def test_partial_json_escapes_and_unicode():
    assert partial_answer('{"answer":"안녕\\n세') == '안녕\n세'
    assert partial_answer('{"answer":"안녕\\') == '안녕'
    assert partial_answer('{"answer":"\\uD83D') == ''
    assert partial_answer('{"answer":"\\uD83D\\uDE00"}') == '😀'


def test_provider_stream_emits_before_completion(monkeypatch):
    fragments = ['{"action":"answer","answer":"취소', ' 가능합니다.",', '"policy_ids":["p1"]}']
    closed = []
    def chunks():
        try:
            for text in fragments:
                yield SimpleNamespace(choices=[SimpleNamespace(delta=SimpleNamespace(content=text))])
        finally:
            closed.append(True)
    def completion(**kwargs):
        assert kwargs['stream'] is True
        return chunks()
    monkeypatch.setitem(sys.modules, 'litellm', SimpleNamespace(completion=completion))
    monkeypatch.setattr(settings, 'llm_min_interval_seconds', 0)
    stream = chat_llm.stream_decide(ChatRequest(question='취소 조건'), [])
    assert next(stream) == '취소'
    assert not closed
    assert next(stream) == ' 가능합니다.'
    with pytest.raises(StopIteration) as finished:
        next(stream)
    assert finished.value.value.policy_ids == ['p1']
    assert closed


def test_stream_validates_final_response(db, monkeypatch):
    target = policy(db)
    def stream(*args):
        yield '임시 답변'
        return ChatDecision(action='answer', answer='임시 답변', policy_ids=['invalid-id'])
    monkeypatch.setattr(chat_llm, 'stream_decide', stream)
    events = list(service.stream_chat(target.project_id, ChatRequest(question='취소 조건'), db.get_bind()))
    assert events[0] == {'type': 'delta', 'text': '임시 답변'}
    assert events[-1]['type'] == 'done'
    assert not events[-1]['response']['grounded']
    assert '근거를 확인하지 못했습니다' in events[-1]['response']['answer']


def test_stream_failure_replaces_partial_with_fallback(db, monkeypatch):
    target = policy(db)
    def stream(*args):
        yield '불완전한 답변'
        raise RuntimeError('provider failed')
    monkeypatch.setattr(chat_llm, 'stream_decide', stream)
    events = list(service.stream_chat(target.project_id, ChatRequest(question='취소 조건'), db.get_bind()))
    final = events[-1]['response']
    assert final['grounded']
    assert '불완전한 답변' not in final['answer']
    assert 'AI 답변을 사용할 수 없어' in final['answer']


def test_stream_http_contract_and_validation(client):
    project_id = project(client)
    response = client.post(f'/projects/{project_id}/chat/stream', json={'question': '취소 조건'})
    assert response.headers['content-type'].startswith('application/x-ndjson')
    event = json.loads(response.text)
    assert event['type'] == 'done'
    assert '승인된 정책이 없습니다' in event['response']['answer']
    assert client.post('/projects/missing/chat/stream', json={'question': '취소 조건'}).status_code == 404
    assert client.post(f'/projects/{project_id}/chat/stream', json={'question': '취소 조건', 'policy_id': 'missing'}).status_code == 404
    assert client.post(f'/projects/{project_id}/chat/stream', json={'question': 'a'}).status_code == 422
