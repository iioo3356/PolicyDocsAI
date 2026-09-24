from pydantic import BaseModel


class DashboardOut(BaseModel):
    source_count: int
    policy_count: int
    review_count: int
    conflict_count: int
