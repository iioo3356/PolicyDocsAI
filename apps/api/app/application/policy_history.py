from sqlalchemy import select
from sqlalchemy.orm import Session
from app.infrastructure.models import PolicyRevision
from .policies import get_policy


def list_revisions(policy_id: str, db: Session):
    get_policy(policy_id, db)
    return db.scalars(select(PolicyRevision).where(PolicyRevision.policy_id == policy_id)
                      .order_by(PolicyRevision.created_at.desc(), PolicyRevision.id.desc())).all()
