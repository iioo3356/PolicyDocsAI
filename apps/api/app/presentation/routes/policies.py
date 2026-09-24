from fastapi import Depends
from sqlalchemy.orm import Session
from app.db import get_db
from app.domain import PolicyStatus
from app.application.dto import NavigationItem, PolicyOut, PolicyUpdate
from fastapi import APIRouter
from app.application import policies as service

from app.application.dto.policy_revision_out import PolicyRevisionOut
from app.application.policy_history import list_revisions

router = APIRouter()


@router.get('/projects/{project_id}/policies', response_model=list[PolicyOut])
def list_policies(project_id: str, status: PolicyStatus | None = None, db: Session = Depends(get_db)):
    return service.list_policies(project_id, status, db)


@router.get('/policies/{policy_id}', response_model=PolicyOut)
def get_policy(policy_id: str, db: Session = Depends(get_db)):
    return service.get_policy(policy_id, db)


@router.patch('/policies/{policy_id}', response_model=PolicyOut)
def update_policy(policy_id: str, payload: PolicyUpdate, db: Session = Depends(get_db)):
    return service.update_policy(policy_id, payload, db)


@router.get('/projects/{project_id}/docs/navigation', response_model=list[NavigationItem])
def docs_navigation(project_id: str, db: Session = Depends(get_db)):
    return service.docs_navigation(project_id, db)


@router.get('/policies/{policy_id}/revisions', response_model=list[PolicyRevisionOut])
def policy_revisions(policy_id: str, db: Session = Depends(get_db)):
    return list_revisions(policy_id, db)
