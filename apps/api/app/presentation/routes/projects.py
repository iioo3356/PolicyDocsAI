from fastapi import Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.application.dto import DashboardOut, ProjectCreate, ProjectOut
from fastapi import APIRouter
from app.application import projects as service

router = APIRouter()


@router.get('/projects', response_model=list[ProjectOut])
def list_projects(db: Session = Depends(get_db)):
    return service.list_projects(db)


@router.post('/projects', response_model=ProjectOut, status_code=201)
def create_project(payload: ProjectCreate, db: Session = Depends(get_db)):
    return service.create_project(payload, db)


@router.get('/projects/{project_id}', response_model=ProjectOut)
def get_project(project_id: str, db: Session = Depends(get_db)):
    return service.get_project(project_id, db)


@router.get('/projects/{project_id}/dashboard', response_model=DashboardOut)
def dashboard(project_id: str, db: Session = Depends(get_db)):
    return service.dashboard(project_id, db)
