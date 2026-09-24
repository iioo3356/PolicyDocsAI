"""Source revisions remain proposals until reviewed; use isolated fake-AI HTTP flows."""
from io import BytesIO
import pytest
from openpyxl import Workbook
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.application.candidates import approve_candidate
from app.application.dto.candidate_review import CandidateReview
from app.infrastructure import jobs
from app.infrastructure.models import PolicyRevision, PolicyCandidate
from test_api_workflow import client, project, upload


REVIEW = {'title': '취소 정책', 'summary': '승인 전 취소 가능', 'rules': ['승인 전 취소 가능']}
UPDATED = {'title': '취소 정책', 'summary': '승인 후 7일 내 취소 가능', 'rules': ['승인 후 7일 내 취소 가능']}


def setup_policy(client):
    project_id = project(client)
    source = upload(client, project_id)
    candidate = client.get(f'/projects/{project_id}/policy-candidates').json()[0]
    policy = client.post(f'/policy-candidates/{candidate["id"]}/approve', json=REVIEW).json()
    return project_id, source, policy


def replacement(client, project_id, source, content='# 취소\n승인 후 7일 내 취소할 수 있습니다.'):
    response = client.post(f'/projects/{project_id}/sources', data={'replaces_source_id': source, 'role': 'ignored'},
                           files={'file': ('updated.md', content, 'text/markdown')})
    assert response.status_code == 201, response.text
    return response.json()['id']


def candidates(client, project_id, source):
    return [c for c in client.get(f'/projects/{project_id}/policy-candidates').json() if c['source_id'] == source]


def test_upload_review_updates_same_policy_and_preserves_history(client):
    project_id, original, policy = setup_policy(client)
    updated = replacement(client, project_id, original)
    candidate = candidates(client, project_id, updated)[0]
    assert candidate['proposed_policy_id'] == policy['id']
    detail = client.get(f'/policy-candidates/{candidate["id"]}').json()
    assert detail['previous_source_id'] == original
    assert detail['related_policies'][0]['id'] == policy['id']
    assert client.get(f'/policies/{policy["id"]}').json() == policy
    assert client.get(f'/policies/{policy["id"]}/revisions').json() == []
    response = client.post(f'/policy-candidates/{candidate["id"]}/approve', json=UPDATED)
    assert response.status_code == 200, response.text
    current = response.json()
    assert current['id'] == policy['id']
    assert current['rules'][0]['content'] == UPDATED['rules'][0]
    assert len(current['evidence']) == 2
    assert client.get(f'/projects/{project_id}/dashboard').json()['policy_count'] == 1
    history = client.get(f'/policies/{policy["id"]}/revisions').json()
    assert len(history) == 1
    assert history[0]['before']['rules'] == REVIEW['rules']
    assert history[0]['after']['rules'] == UPDATED['rules']
    assert history[0]['after']['_source']['source_id'] == updated
    assert history[0]['after']['_source']['previous_source_id'] == original
    answer = client.post(f'/projects/{project_id}/chat', json={'question': '취소 정책', 'policy_id': policy['id']}).json()
    assert '7일' in answer['answer']
    assert len(answer['citations']) == 1
    assert answer['citations'][0]['source_path'] == 'updated.md'
    guidance = client.post(f'/projects/{project_id}/chat', json={'question': '8일로 바꿔줘', 'policy_id': policy['id']}).json()
    assert guidance['source_suggestions'][0]['source_id'] == updated
    assert client.post(f'/policy-candidates/{candidate["id"]}/approve', json=UPDATED).status_code == 409
    assert client.post(f'/policy-candidates/{candidate["id"]}/reject').status_code == 409
    for source in [original, updated]:
        assert client.delete(f'/sources/{source}').status_code == 409


def test_rejected_update_leaves_policy_unchanged(client):
    project_id, source, policy = setup_policy(client)
    updated = replacement(client, project_id, source)
    candidate = candidates(client, project_id, updated)[0]
    assert client.post(f'/policy-candidates/{candidate["id"]}/reject').status_code == 204
    assert client.get(f'/policies/{policy["id"]}').json() == policy
    assert client.get(f'/policies/{policy["id"]}/revisions').json() == []


def test_stale_update_cannot_overwrite_another_approved_revision(client):
    project_id, source, policy = setup_policy(client)
    first = replacement(client, project_id, source)
    second = replacement(client, project_id, source)
    a, b = candidates(client, project_id, first)[0], candidates(client, project_id, second)[0]
    assert client.post(f'/policy-candidates/{a["id"]}/approve', json=UPDATED).status_code == 200
    response = client.post(f'/policy-candidates/{b["id"]}/approve', json=REVIEW)
    assert response.status_code == 409, response.text
    assert len(client.get(f'/policies/{policy["id"]}/revisions').json()) == 1


def test_unmatched_location_requires_manual_policy_mapping(client):
    project_id, source, policy = setup_policy(client)
    updated = replacement(client, project_id, source, '# 새 취소 기준\n승인 후 7일 내 취소할 수 있습니다.')
    candidate = candidates(client, project_id, updated)[0]
    assert candidate['proposed_policy_id'] is None
    deprecated = client.get(f'/policies/{policy["id"]}').json()
    assert deprecated['status'] == 'DEPRECATED'
    assert deprecated['deprecated_at'] is not None
    response = client.post(f'/policy-candidates/{candidate["id"]}/approve', json={**UPDATED, 'target_policy_id': policy['id']})
    assert response.status_code == 200, response.text
    assert response.json()['id'] == policy['id']
    assert response.json()['status'] == 'APPROVED'
    assert response.json()['deprecated_at'] is None


def test_missing_policy_is_deprecated_with_date_and_history(client):
    project_id = project(client)
    original = client.post(
        f'/projects/{project_id}/sources', data={'role': 'document'},
        files={'file': ('policies.md', '# 취소\n승인 전 취소 가능\n# 환불\n구매 후 환불 가능', 'text/markdown')},
    ).json()['id']
    original_candidates = candidates(client, project_id, original)
    assert len(original_candidates) == 2
    approved = {}
    for candidate in original_candidates:
        title = '취소 정책' if '취소' in candidate['title'] else '환불 정책'
        approved[title] = client.post(f'/policy-candidates/{candidate["id"]}/approve', json={
            'title': title, 'summary': candidate['summary'], 'rules': candidate['rules'],
        }).json()

    replacement(client, project_id, original, '# 취소\n승인 전 취소 가능')
    current = {policy['title']: policy for policy in client.get(f'/projects/{project_id}/policies').json()}
    assert current['취소 정책']['status'] == 'APPROVED'
    retired = current['환불 정책']
    assert retired['status'] == 'DEPRECATED'
    assert retired['deprecated_at'] is not None
    assert [policy['id'] for policy in client.get(
        f'/projects/{project_id}/policies?status=APPROVED').json()
    ] == [approved['취소 정책']['id']]
    history = client.get(f'/policies/{retired["id"]}/revisions').json()
    assert history[0]['after']['_deprecation']['deprecated_at'] == retired['deprecated_at']
    assert '정책 폐기' in history[0]['instruction']
    chat = client.post(f'/projects/{project_id}/chat', json={'question': '환불 정책'})
    assert all(item['id'] != retired['id'] for item in chat.json()['related_policies'])


def test_source_update_validation_and_foreign_target(client):
    project_id, source, policy = setup_policy(client)
    other_id, other_source, other_policy = setup_policy(client)
    for replace_id, name, status in [(other_source, 'p.md', 404), (source, 'p.csv', 400), ('missing', 'p.md', 404)]:
        response = client.post(f'/projects/{project_id}/sources', data={'replaces_source_id': replace_id}, files={'file': (name, 'text')})
        assert response.status_code == status
    updated = replacement(client, project_id, source)
    candidate = candidates(client, project_id, updated)[0]
    response = client.post(f'/policy-candidates/{candidate["id"]}/approve', json={**UPDATED, 'target_policy_id': other_policy['id']})
    assert response.status_code == 404
    assert client.get(f'/policies/{policy["id"]}').json() == policy


def test_revision_commit_failure_rolls_back_all_changes(client, monkeypatch):
    project_id, source, policy = setup_policy(client)
    updated = replacement(client, project_id, source)
    candidate = candidates(client, project_id, updated)[0]
    with Session(jobs.engine) as db:
        def fail():
            raise RuntimeError('commit failed')
        monkeypatch.setattr(db, 'commit', fail)
        with pytest.raises(RuntimeError):
            approve_candidate(candidate['id'], CandidateReview(**UPDATED), db)
        assert db.scalar(select(PolicyRevision)) is None
        assert db.get(PolicyCandidate, candidate['id']).decision.value == 'PENDING'
    assert client.get(f'/policies/{policy["id"]}').json() == policy


def test_real_xlsx_upload_is_not_skipped_as_binary(client):
    project_id = project(client)
    workbook = Workbook()
    workbook.active.append(['제목', '규칙'])
    workbook.active.append(['취소 정책', '승인 전에는 취소할 수 있습니다.'])
    stream = BytesIO()
    workbook.save(stream)
    workbook.close()
    response = client.post(f'/projects/{project_id}/sources', files={'file': ('policy.xlsx', stream.getvalue())})
    assert response.status_code == 201
    found = candidates(client, project_id, response.json()['id'])
    assert found


def test_failed_reanalysis_preserves_approved_policy(client, monkeypatch):
    from app.analysis import pipeline
    project_id, source, policy = setup_policy(client)
    def fail(_):
        raise ValueError('invalid document')
    monkeypatch.setattr(pipeline, 'parse_markdown', fail)
    updated = replacement(client, project_id, source)
    uploaded = next(s for s in client.get(f'/projects/{project_id}/sources').json() if s['id'] == updated)
    assert uploaded['status'] == 'FAILED'
    assert candidates(client, project_id, updated) == []
    assert client.get(f'/policies/{policy["id"]}').json() == policy
    assert client.get(f'/policies/{policy["id"]}/revisions').json() == []


def test_second_update_extends_revision_chain(client):
    project_id, source, policy = setup_policy(client)
    previous = source
    for days in [7, 8]:
        updated = replacement(client, project_id, previous, f'# 취소\n승인 후 {days}일 내 취소할 수 있습니다.')
        candidate = candidates(client, project_id, updated)[0]
        response = client.post(f'/policy-candidates/{candidate["id"]}/approve', json={
            **UPDATED, 'summary': f'{days}일 내 취소', 'rules': [f'{days}일 내 취소'],
        })
        assert response.status_code == 200, response.text
        assert response.json()['id'] == policy['id']
        previous = updated
    history = client.get(f'/policies/{policy["id"]}/revisions').json()
    assert len(history) == 2
    assert history[0]['before']['rules'] == history[1]['after']['rules'] == ['7일 내 취소']
    assert history[0]['after']['rules'] == ['8일 내 취소']
    assert history[0]['after']['_source']['previous_source_id'] == history[1]['after']['_source']['source_id']
