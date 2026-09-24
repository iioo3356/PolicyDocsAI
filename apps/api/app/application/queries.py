from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload
from app.infrastructure.models import Policy, Project
from app.domain.application_error import ApplicationError


def require_project(db: Session, project_id: str) -> Project:
    project = db.get(Project, project_id)
    if not project:
        raise ApplicationError(404, "Project를 찾을 수 없습니다.")
    return project

def policy_query():
    return select(Policy).options(selectinload(Policy.rules), selectinload(Policy.evidence))
