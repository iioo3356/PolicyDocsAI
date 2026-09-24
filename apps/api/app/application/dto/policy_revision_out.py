from datetime import datetime
from .orm_model import ORMModel


class PolicyRevisionOut(ORMModel):
    id: str
    instruction: str
    before: dict
    after: dict
    created_at: datetime
