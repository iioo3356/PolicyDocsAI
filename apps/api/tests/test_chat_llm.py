import json
import sys
from types import SimpleNamespace

import pytest
from pydantic import ValidationError
from app.application.dto.chat_request import ChatRequest
from app.config import settings
from app.infrastructure import chat_llm


def test_structured_llm_contract_and_history(monkeypatch):
    captured = {}
    payload = {'action': 'answer', 'answer': '승인 전 취소할 수 있습니다.',
               'policy_ids': ['policy-id']}
    def completion(**kwargs):
        captured.update(kwargs)
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=json.dumps(payload)))])
    monkeypatch.setitem(sys.modules, 'litellm', SimpleNamespace(completion=completion))
    monkeypatch.setattr(settings, 'llm_min_interval_seconds', 0)
    request = ChatRequest(question='그 정책은?', history=[{'role': 'user', 'content': '취소 조건'}])
    result = chat_llm.decide(request, [{'id': 'policy-id'}])
    assert result.action == 'answer'
    data = json.loads(captured['messages'][1]['content'])
    assert 'edit_allowed' not in data
    assert data['history'][0]['content'] == '취소 조건'
    assert captured['response_format']['json_schema']['strict'] is True
    payload['action'] = 'update'
    with pytest.raises(ValidationError):
        chat_llm.decide(request, [])
