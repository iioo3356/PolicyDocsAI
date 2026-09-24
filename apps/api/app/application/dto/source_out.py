from datetime import datetime
from app.domain import JobStatus, SourceKind
from app.application.dto.orm_model import ORMModel

class SourceOut(ORMModel):
    id: str
    project_id: str
    kind: SourceKind
    role: str
    name: str
    status: JobStatus
    error_message: str | None
    discovered_policy_count: int
    created_at: datetime
