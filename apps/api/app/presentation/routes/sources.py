from fastapi import BackgroundTasks, Depends, File, Form, UploadFile
from sqlalchemy.orm import Session
from app.config import settings
from app.db import get_db
from app.application.dto import JobOut, SourceAnalysisOut, SourceOut, SourceRoleUpdate
from fastapi import APIRouter
from app.application import sources as service
from app.infrastructure.jobs import _process_job

router = APIRouter()


@router.get('/projects/{project_id}/sources', response_model=list[SourceOut])
def list_sources(project_id: str, db: Session = Depends(get_db)):
    return service.list_sources(project_id, db)


@router.post('/projects/{project_id}/sources', response_model=SourceOut, status_code=201)
async def upload_source(background: BackgroundTasks, project_id: str, file: UploadFile = File(...),
                        role: str = Form("document"), replaces_source_id: str | None = Form(None),
                        db: Session = Depends(get_db)):
    raw = await file.read(settings.max_upload_bytes + 1)
    source, job_id = service.upload_source(project_id, file.filename, raw, role, db, replaces_source_id)
    background.add_task(_process_job, source.id, job_id)
    return source


@router.patch('/sources/{source_id}/role', response_model=SourceOut)
def update_source_role(source_id: str, payload: SourceRoleUpdate, db: Session = Depends(get_db)):
    return service.update_source_role(source_id, payload, db)


@router.delete('/sources/{source_id}', status_code=204)
def delete_source(source_id: str, db: Session = Depends(get_db)) -> None:
    return service.delete_source(source_id, db)


@router.get('/analysis-jobs/{job_id}', response_model=JobOut)
def get_job(job_id: str, db: Session = Depends(get_db)):
    return service.get_job(job_id, db)


@router.get('/sources/{source_id}/analysis', response_model=SourceAnalysisOut)
def analysis_progress(source_id: str, db: Session = Depends(get_db)):
    return service.analysis_progress(source_id, db)
