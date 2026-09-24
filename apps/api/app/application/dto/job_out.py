from app.domain import JobStatus
from app.application.dto.orm_model import ORMModel

class JobOut(ORMModel):
    id: str
    status: JobStatus
    stage: str
    progress: int
    error_message: str | None
    stats: dict
