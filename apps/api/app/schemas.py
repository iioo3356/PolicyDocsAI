from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field

from .models import CandidateDecision, JobStatus, PolicyStatus, SourceKind


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class ProjectCreate(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    description: str | None = None


class ProjectOut(ORMModel):
    id: str
    name: str
    description: str | None
    created_at: datetime


class DashboardOut(BaseModel):
    source_count: int
    policy_count: int
    review_count: int
    conflict_count: int


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


class SourceRoleUpdate(BaseModel):
    role: str = Field(min_length=1, max_length=50, pattern=r"^[\w가-힣 ./_-]+$")


class JobOut(ORMModel):
    id: str
    status: JobStatus
    stage: str
    progress: int
    error_message: str | None
    stats: dict


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


class CandidateDetail(CandidateOut):
    source_path: str
    start_line: int
    end_line: int
    excerpt: str
    source_type: str
    source_name: str


class CandidateReview(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    summary: str = Field(min_length=1)
    category: str = Field(default="미분류", max_length=500)
    rules: list[str] = Field(min_length=1)
    target_policy_id: str | None = None


class RuleOut(ORMModel):
    id: str
    rule_type: str
    content: str
    normalized_data: dict
    sort_order: int


class EvidenceOut(ORMModel):
    id: str
    source_type: str
    source_name: str
    source_path: str
    start_line: int
    end_line: int
    excerpt: str
    extracted_claim: str
    confidence: float


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


class PolicyUpdate(BaseModel):
    title: str | None = None
    summary: str | None = None
    category: str | None = None
    rules: list[str] | None = None


class NavigationItem(BaseModel):
    category: str
    policies: list[dict[str, str]]


class ChatRequest(BaseModel):
    question: str = Field(min_length=2, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=10)


class ChatCitation(BaseModel):
    policy_id: str
    policy_title: str
    source_path: str
    lines: str


class ChatResponse(BaseModel):
    answer: str
    grounded: bool
    related_policies: list[PolicyOut]
    citations: list[ChatCitation]
