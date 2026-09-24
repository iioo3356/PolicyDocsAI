from pydantic import BaseModel, ConfigDict, Field
from .chat_turn import ChatTurn


class ChatRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    question: str = Field(min_length=2, max_length=2000)
    top_k: int = Field(default=5, ge=1, le=10)
    policy_id: str | None = Field(default=None, max_length=36)
    history: list[ChatTurn] = Field(default_factory=list, max_length=8)
