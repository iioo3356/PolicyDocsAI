from datetime import datetime
from app.domain import CandidateDecision
from app.application.dto.orm_model import ORMModel

class CandidateOut(ORMModel):
    id: str
    project_id: str
    source_id: str
    proposed_policy_id: str | None
    title: str
    summary: str
    category: str
    rules: list[str]
    confidence: float
    decision: CandidateDecision
    created_at: datetime
