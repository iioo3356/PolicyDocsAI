from typing import Literal
from pydantic import BaseModel, ConfigDict, Field


class ChatDecision(BaseModel):
    model_config = ConfigDict(extra='forbid')
    action: Literal['answer', 'clarify', 'update_source']
    answer: str = Field(min_length=1, max_length=6000)
    policy_ids: list[str] = Field(max_length=10)
