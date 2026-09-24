from app.application.dto.orm_model import ORMModel
from app.application.dto.source_candidate_out import SourceCandidateOut
from app.domain import JobStatus


class SourceAnalysisOut(ORMModel):
    source_id: str
    status: JobStatus
    stage: str
    progress: int
    current_file: str | None = None
    current_policy_title: str | None = None
    processed_files: int = 0
    total_files: int = 0
    candidates: list[SourceCandidateOut]
