from datetime import datetime
from app.domain import PolicyStatus
from app.application.dto.orm_model import ORMModel
from app.application.dto.rule_out import RuleOut
from app.application.dto.evidence_out import EvidenceOut

class PolicyOut(ORMModel):
    id: str
    project_id: str
    category: str
    title: str
    summary: str
    status: PolicyStatus
    confidence: float
    has_conflict: bool
    rules: list[RuleOut]
    evidence: list[EvidenceOut]
    created_at: datetime
    updated_at: datetime
