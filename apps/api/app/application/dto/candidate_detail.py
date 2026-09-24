from pydantic import Field
from app.application.dto.policy_out import PolicyOut
from app.application.dto.candidate_out import CandidateOut

class CandidateDetail(CandidateOut):
    source_path: str
    start_line: int
    end_line: int
    excerpt: str
    source_type: str
    source_name: str
    previous_source_id: str | None = None
    related_policies: list[PolicyOut] = Field(default_factory=list)
