from sqlalchemy.orm import Session
from app.analysis.pipeline import run_analysis
from app.db import engine
from app.infrastructure.models import AnalysisJob, Source

def _process_job(source_id: str, job_id: str) -> None:
    with Session(engine) as db:
        run_analysis(db, db.get(Source, source_id), db.get(AnalysisJob, job_id))
