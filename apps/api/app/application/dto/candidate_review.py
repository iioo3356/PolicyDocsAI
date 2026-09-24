from pydantic import BaseModel, Field


class CandidateReview(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    summary: str = Field(min_length=1)
    category: str = Field(default="미분류", max_length=500)
    rules: list[str] = Field(min_length=1)
    target_policy_id: str | None = None
