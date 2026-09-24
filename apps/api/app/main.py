import logging
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from app.domain.clock import utc_now_naive
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import update
from sqlalchemy.orm import Session
from app.config import settings
from app.db import Base, engine
from app.infrastructure.models import AnalysisJob, JobStatus, Source
from app.infrastructure.schema import ensure_policy_deprecated_at_column
from fastapi.responses import JSONResponse
from app.domain.application_error import ApplicationError
from app.presentation.routes import projects, sources, candidates, policies, chat

@asynccontextmanager
async def lifespan(application: FastAPI) -> AsyncIterator[None]:
    startup()
    yield


app = FastAPI(title="Policy Docs API", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[settings.web_origin], allow_credentials=True,
                   allow_methods=["*"], allow_headers=["*"])


@app.exception_handler(ApplicationError)
async def application_error_handler(request, error):
    return JSONResponse(status_code=error.status_code, content={"detail": error.detail})


def startup() -> None:
    logging.getLogger("uvicorn.error").info(
        "Policy Docs API configuration ai_enabled=%s model=%s",
        bool(settings.llm_api_key), settings.llm_model,
    )
    settings.storage_path.mkdir(parents=True, exist_ok=True)
    if engine.dialect.name == "postgresql":
        with engine.connect().execution_options(isolation_level="AUTOCOMMIT") as connection:
            enum_exists = connection.exec_driver_sql(
                "SELECT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'sourcekind')"
            ).scalar()
            if enum_exists:
                connection.exec_driver_sql("ALTER TYPE sourcekind ADD VALUE IF NOT EXISTS 'XLSX'")
    Base.metadata.create_all(engine)
    ensure_policy_deprecated_at_column(engine)
    _recover_interrupted_analysis_jobs()

def _recover_interrupted_analysis_jobs() -> None:
    """In-process background jobs cannot survive an API process restart."""
    interrupted = {JobStatus.PENDING, JobStatus.PROCESSING}
    message = "API가 재시작되어 분석이 중단되었습니다. Source를 삭제한 뒤 다시 업로드하세요."
    with Session(engine) as db:
        source_count = db.execute(
            update(Source).where(Source.status.in_(interrupted)).values(
                status=JobStatus.FAILED,
                error_message=message,
            )
        ).rowcount
        job_count = db.execute(
            update(AnalysisJob).where(AnalysisJob.status.in_(interrupted)).values(
                status=JobStatus.FAILED,
                stage="failed",
                error_message=message,
                completed_at=utc_now_naive(),
            )
        ).rowcount
        db.commit()
    if source_count or job_count:
        logging.getLogger("uvicorn.error").warning(
            "Recovered interrupted analysis state sources=%s jobs=%s", source_count, job_count,
        )

@app.get("/health")
def health():
    return {"status": "ok"}

for router_module in (projects, sources, candidates, policies, chat):
    app.include_router(router_module.router)
