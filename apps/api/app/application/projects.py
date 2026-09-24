from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.infrastructure.models import CandidateDecision, Policy, PolicyCandidate, PolicyConflict, Project, Source
from app.application.dto import DashboardOut, ProjectCreate

from .queries import require_project


def list_projects(db: Session):
    return db.scalars(select(Project).order_by(Project.created_at.desc())).all()


def create_project(payload: ProjectCreate, db: Session):
    project = Project(name=payload.name.strip(), description=payload.description)
    db.add(project)
    db.commit()
    db.refresh(project)
    return project


def get_project(project_id: str, db: Session):
    return require_project(db, project_id)


def dashboard(project_id: str, db: Session):
    require_project(db, project_id)
    scalar = lambda statement: db.scalar(statement) or 0
    return DashboardOut(
        source_count=scalar(select(func.count()).select_from(Source).where(Source.project_id == project_id)),
        policy_count=scalar(select(func.count()).select_from(Policy).where(Policy.project_id == project_id)),
        review_count=scalar(select(func.count()).select_from(PolicyCandidate).where(
            PolicyCandidate.project_id == project_id, PolicyCandidate.decision == CandidateDecision.PENDING)),
        conflict_count=scalar(select(func.count()).select_from(PolicyConflict).join(Policy).where(
            Policy.project_id == project_id, PolicyConflict.status == "OPEN")),
    )
