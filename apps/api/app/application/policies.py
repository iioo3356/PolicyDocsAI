from collections import defaultdict
from sqlalchemy import select
from sqlalchemy.orm import Session
from app.infrastructure.models import Policy, PolicyStatus
from app.application.dto import NavigationItem, PolicyUpdate
from app.domain.application_error import ApplicationError

from .queries import require_project, policy_query


def list_policies(project_id: str, status: PolicyStatus | None, db: Session):
    require_project(db, project_id)
    query = policy_query().where(Policy.project_id == project_id)
    if status:
        query = query.where(Policy.status == status)
    return db.scalars(query.order_by(Policy.category, Policy.title)).all()


def get_policy(policy_id: str, db: Session):
    policy = db.scalar(policy_query().where(Policy.id == policy_id))
    if not policy:
        raise ApplicationError(404, "Policy를 찾을 수 없습니다.")
    return policy


def update_policy(policy_id: str, payload: PolicyUpdate, db: Session):
    get_policy(policy_id, db)
    raise ApplicationError(409, '관련 소스를 업데이트하고 정책 관리에서 변경안을 승인해 주세요.')


def docs_navigation(project_id: str, db: Session):
    policies = db.scalars(select(Policy).where(Policy.project_id == project_id, Policy.status == PolicyStatus.APPROVED)
                          .order_by(Policy.category, Policy.title)).all()
    grouped = defaultdict(list)
    for policy in policies:
        grouped[policy.category].append({"id": policy.id, "title": policy.title})
    return [NavigationItem(category=category, policies=items) for category, items in grouped.items()]
