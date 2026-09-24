"""Exercise HTTP wiring, serialization, review, search and source protection."""
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.config import settings
from app.infrastructure import jobs


@pytest.fixture
def client(tmp_path, monkeypatch):
    engine = create_engine(
        "sqlite://", connect_args={"check_same_thread": False}, poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(engine)
    monkeypatch.setattr(jobs, "engine", engine)
    monkeypatch.setattr(settings, "storage_path", tmp_path)
    monkeypatch.setattr(settings, "llm_api_key", "")

    def database():
        with Session(engine) as session:
            yield session

    app.dependency_overrides[get_db] = database
    # Avoid production startup, which intentionally performs DB initialization.
    client = TestClient(app)
    try:
        yield client
    finally:
        client.close()
        app.dependency_overrides.clear()
        engine.dispose()


def project(client):
    response = client.post('/projects', json={"name": "테스트"})
    assert response.status_code == 201
    return response.json()['id']


def upload(client, project_id):
    response = client.post(
        f'/projects/{project_id}/sources', data={"role": "document"},
        files={"file": ("policy.md", "# 취소\n승인 전에는 취소할 수 있습니다.", "text/markdown")},
    )
    assert response.status_code == 201, response.text
    return response.json()['id']


def test_review_search_and_evidence_protection(client):
    project_id = project(client)
    source_id = upload(client, project_id)
    candidates = client.get(f'/projects/{project_id}/policy-candidates').json()
    assert len(candidates) == 1
    candidate_id = candidates[0]['id']
    detail = client.get(f'/policy-candidates/{candidate_id}').json()
    assert detail['source_name'] == 'policy.md'
    assert '취소' in detail['excerpt']
    review = {"title": "취소 정책", "summary": "승인 전 취소 가능", "rules": ["승인 전에 취소 가능"]}
    approved = client.post(f'/policy-candidates/{candidate_id}/approve', json=review)
    assert approved.status_code == 200, approved.text
    policy = approved.json()
    assert policy['status'] == 'APPROVED'
    assert len(policy['rules']) == len(policy['evidence']) == 1
    assert client.post(f'/policy-candidates/{candidate_id}/approve', json=review).status_code == 409
    protected = client.delete(f'/sources/{source_id}')
    assert protected.status_code == 409
    assert '근거' in protected.json()['detail']
    answer = client.post(f'/projects/{project_id}/chat', json={"question": "취소 정책"})
    assert answer.status_code == 200, answer.text
    assert answer.json()['grounded'] is True
    assert answer.json()['citations'][0]['policy_id'] == policy['id']
    assert client.get(f'/projects/{project_id}/dashboard').json()['policy_count'] == 1
    assert client.get(f'/projects/{project_id}/docs/navigation').json()[0]['policies'][0]['id'] == policy['id']
    changed = client.patch(f'/policies/{policy["id"]}', json={"title": "수정 정책"})
    assert changed.status_code == 409
    assert client.get(f'/policies/{policy["id"]}').json()['title'] == '취소 정책'


def test_source_validation_and_delete(client):
    project_id = project(client)
    invalid = client.post(
        f'/projects/{project_id}/sources', files={"file": ("bad.txt", b"test")},
    )
    assert invalid.status_code == 400
    assert 'detail' in invalid.json()
    source_id = upload(client, project_id)
    changed = client.patch(f'/sources/{source_id}/role', json={"role": " backend "})
    assert changed.status_code == 200
    assert changed.json()['role'] == 'backend'
    assert client.delete(f'/sources/{source_id}').status_code == 204
    assert client.get(f'/projects/{project_id}/sources').json() == []
    assert client.delete(f'/sources/{source_id}').status_code == 404
    assert client.get('/projects/missing').status_code == 404


def test_chat_edit_guides_source_and_retired_confirmation_is_blocked(client):
    project_id = project(client)
    source_id = upload(client, project_id)
    candidate = client.get(f'/projects/{project_id}/policy-candidates').json()[0]
    policy = client.post(f'/policy-candidates/{candidate["id"]}/approve', json={
        'title': '취소 정책', 'summary': '승인 전 취소 가능', 'rules': ['승인 전 취소 가능'],
    }).json()
    response = client.post(f'/projects/{project_id}/chat', json={
        'question': '승인 후 7일 내 취소 가능으로 바꿔줘', 'policy_id': policy['id'],
    })
    assert response.status_code == 200, response.text
    body = response.json()
    assert body['action'] == 'update_source'
    assert body['source_suggestions'][0]['source_id'] == source_id
    assert 'proposal' not in body and 'change' not in body
    for action in ['confirm', 'cancel']:
        assert client.post(f'/projects/{project_id}/chat/proposals/old/{action}', json={'confirmed': True}).status_code == 410
    assert client.get(f'/policies/{policy["id"]}').json() == policy
