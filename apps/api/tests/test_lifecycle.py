from datetime import UTC, datetime

from fastapi.testclient import TestClient
from sqlalchemy import create_engine, inspect, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app import main
from app.domain.clock import utc_now_naive
from app.infrastructure.models import AnalysisJob, JobStatus, Project, Source, SourceKind
from app.infrastructure.models.defaults import now
from app.infrastructure.schema import ensure_policy_deprecated_at_column


def test_clock_keeps_naive_utc_storage_contract():
    before = datetime.now(UTC).replace(tzinfo=None)
    current, model_default = utc_now_naive(), now()
    after = datetime.now(UTC).replace(tzinfo=None)
    assert current.tzinfo is None
    assert model_default.tzinfo is None
    assert before <= current <= model_default <= after


def test_existing_policy_table_gets_deprecated_at_column():
    engine = create_engine('sqlite://')
    try:
        with engine.begin() as connection:
            connection.exec_driver_sql('CREATE TABLE policies (id VARCHAR(36) PRIMARY KEY)')
        ensure_policy_deprecated_at_column(engine)
        ensure_policy_deprecated_at_column(engine)
        assert 'deprecated_at' in {column['name'] for column in inspect(engine).get_columns('policies')}
    finally:
        engine.dispose()


def test_lifespan_initializes_storage_and_recovers_interrupted_jobs(tmp_path, monkeypatch):
    engine = create_engine('sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
    monkeypatch.setattr(main, 'engine', engine)
    storage = tmp_path / 'uploads'
    monkeypatch.setattr(main.settings, 'storage_path', storage)
    try:
        # Exercise the actual ASGI lifespan, including table creation on a fresh DB.
        with TestClient(main.app) as client:
            assert client.get('/health').json() == {'status': 'ok'}
            assert storage.is_dir()
            assert 'analysis_jobs' in inspect(engine).get_table_names()
            with Session(engine) as db:
                project = Project(name='recovery')
                db.add(project)
                db.flush()
                source = Source(project_id=project.id, kind=SourceKind.MARKDOWN,
                                name='policy.md', storage_key='policy.md', content_hash='a' * 64,
                                status=JobStatus.PROCESSING)
                db.add(source)
                db.flush()
                job = AnalysisJob(project_id=project.id, source_id=source.id, status=JobStatus.PROCESSING)
                db.add(job)
                db.commit()

        with TestClient(main.app):
            with Session(engine) as db:
                assert db.scalar(select(Source)).status == JobStatus.FAILED
                job = db.scalar(select(AnalysisJob))
                assert job.status == JobStatus.FAILED
                assert job.completed_at is not None
                assert job.completed_at.tzinfo is None
    finally:
        engine.dispose()
