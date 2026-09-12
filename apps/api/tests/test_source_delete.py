from fastapi import HTTPException
import pytest
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app import main
from app.db import Base
from app.models import (
    AnalysisJob, JobStatus, Policy, PolicyEvidence, PolicyStatus, Project, Source,
    SourceChunk, SourceFile, SourceKind,
)


def database():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    return engine


def source_graph(db: Session, storage_key: str) -> tuple[Source, SourceChunk]:
    project = Project(name="삭제 테스트")
    db.add(project)
    db.flush()
    source = Source(project_id=project.id, kind=SourceKind.CODE_ZIP, role="backend", name="code.zip",
                    storage_key=storage_key, content_hash="a" * 64, status=JobStatus.COMPLETED)
    db.add(source)
    db.flush()
    source_file = SourceFile(source_id=source.id, project_id=project.id, path="policy.ts",
                             language="typescript", content_hash="b" * 64, size_bytes=10)
    db.add(source_file)
    db.flush()
    chunk = SourceChunk(source_file_id=source_file.id, project_id=project.id, chunk_type="code",
                        start_line=1, end_line=2, content="if (blocked) return false")
    db.add(chunk)
    db.add(AnalysisJob(source_id=source.id, project_id=project.id, status=JobStatus.COMPLETED))
    db.commit()
    return source, chunk


def test_delete_source_removes_records_and_stored_file(tmp_path, monkeypatch):
    monkeypatch.setattr(main.settings, "storage_path", tmp_path)
    stored_file = tmp_path / "project" / "code.zip"
    stored_file.parent.mkdir()
    stored_file.write_bytes(b"zip")

    with Session(database()) as db:
        source, _ = source_graph(db, "project/code.zip")
        source_id = source.id
        main.delete_source(source_id, db)

        assert db.get(Source, source_id) is None
        assert db.scalar(select(func.count()).select_from(SourceFile)) == 0
        assert db.scalar(select(func.count()).select_from(SourceChunk)) == 0
        assert db.scalar(select(func.count()).select_from(AnalysisJob)) == 0
        assert not stored_file.exists()


def test_delete_source_preserves_approved_policy_evidence(tmp_path, monkeypatch):
    monkeypatch.setattr(main.settings, "storage_path", tmp_path)
    with Session(database()) as db:
        source, chunk = source_graph(db, "project/code.zip")
        policy = Policy(project_id=source.project_id, title="정책", summary="요약", category="테스트",
                        status=PolicyStatus.APPROVED)
        db.add(policy)
        db.flush()
        db.add(PolicyEvidence(policy_id=policy.id, source_chunk_id=chunk.id, source_type="backend",
                              source_name=source.name, source_path="policy.ts", start_line=1, end_line=2,
                              excerpt=chunk.content, extracted_claim="테스트 정책", confidence=0.9))
        db.commit()

        with pytest.raises(HTTPException) as error:
            main.delete_source(source.id, db)

        assert error.value.status_code == 409
        assert db.get(Source, source.id) is not None


def test_startup_recovery_marks_interrupted_analysis_as_failed(monkeypatch):
    engine = database()
    monkeypatch.setattr(main, "engine", engine)
    with Session(engine) as db:
        source, _ = source_graph(db, "project/code.zip")
        source.status = JobStatus.PROCESSING
        job = db.scalar(select(AnalysisJob).where(AnalysisJob.source_id == source.id))
        job.status = JobStatus.PROCESSING
        db.commit()
        source_id, job_id = source.id, job.id

    main._recover_interrupted_analysis_jobs()

    with Session(engine) as db:
        source, job = db.get(Source, source_id), db.get(AnalysisJob, job_id)
        assert source.status == JobStatus.FAILED
        assert job.status == JobStatus.FAILED
        assert "재시작" in source.error_message
        assert job.completed_at is not None
