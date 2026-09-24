from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.analysis import pipeline
from app.db import Base
from app.domain.parsed_chunk import ParsedChunk
from app.infrastructure.models import (
    AnalysisJob, JobStatus, PolicyCandidate, Project, Source, SourceChunk, SourceFile, SourceKind,
)


def setup_analysis(tmp_path):
    engine = create_engine(f"sqlite:///{tmp_path / 'progress.db'}")
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        project = Project(name="progress")
        db.add(project)
        db.flush()
        source = Source(project_id=project.id, name="policy.md", kind=SourceKind.MARKDOWN,
                        role="document", storage_key="unused", content_hash="hash")
        db.add(source)
        db.flush()
        job = AnalysisJob(project_id=project.id, source_id=source.id)
        db.add(job)
        db.commit()
        return engine, source.id, job.id


def extracted(number: int):
    return {
        "title": f"정책 {number}", "summary": f"요약 {number}", "category": "테스트",
        "rules": [f"규칙 {number}"], "confidence": .9,
    }, {"extractor": "test"}


def test_candidate_is_visible_while_analysis_is_running(tmp_path, monkeypatch):
    engine, source_id, job_id = setup_analysis(tmp_path)
    chunks = [ParsedChunk(kind="section", content=f"내용 {number}", start_line=number, end_line=number)
              for number in (1, 2)]
    monkeypatch.setattr(pipeline, "_documents", lambda source: [("policy.md", b"contents")])
    monkeypatch.setattr(pipeline, "parse_markdown", lambda text: chunks)
    calls = 0

    def extract(item, path):
        nonlocal calls
        calls += 1
        if calls == 2:
            with Session(engine) as observer:
                assert observer.scalar(select(func.count()).select_from(PolicyCandidate)) == 1
                source = observer.get(Source, source_id)
                job = observer.get(AnalysisJob, job_id)
                assert source.status == JobStatus.PROCESSING
                assert source.discovered_policy_count == 1
                assert job.stats["current_policy_title"] == "정책 1"
        return extracted(calls)

    monkeypatch.setattr(pipeline, "extract_candidate_with_metadata", extract)
    with Session(engine) as db:
        pipeline.run_analysis(db, db.get(Source, source_id), db.get(AnalysisJob, job_id))
    with Session(engine) as db:
        assert db.get(Source, source_id).status == JobStatus.COMPLETED
        assert db.get(AnalysisJob, job_id).progress == 100
        assert db.scalar(select(func.count()).select_from(PolicyCandidate)) == 2
    engine.dispose()


def test_failure_removes_candidates_committed_for_live_progress(tmp_path, monkeypatch):
    engine, source_id, job_id = setup_analysis(tmp_path)
    chunks = [ParsedChunk(kind="section", content=f"내용 {number}", start_line=number, end_line=number)
              for number in (1, 2)]
    monkeypatch.setattr(pipeline, "_documents", lambda source: [("policy.md", b"contents")])
    monkeypatch.setattr(pipeline, "parse_markdown", lambda text: chunks)
    calls = 0

    def extract(item, path):
        nonlocal calls
        calls += 1
        if calls == 2:
            raise ValueError("broken second chunk")
        return extracted(calls)

    monkeypatch.setattr(pipeline, "extract_candidate_with_metadata", extract)
    with Session(engine) as db:
        pipeline.run_analysis(db, db.get(Source, source_id), db.get(AnalysisJob, job_id))
    with Session(engine) as db:
        assert db.get(Source, source_id).status == JobStatus.FAILED
        assert db.get(Source, source_id).discovered_policy_count == 0
        for model in (PolicyCandidate, SourceChunk, SourceFile):
            assert db.scalar(select(func.count()).select_from(model)) == 0
    engine.dispose()
