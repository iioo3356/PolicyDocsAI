from typing import Literal
from pydantic import BaseModel, Field
from .policy_out import PolicyOut
from .chat_citation import ChatCitation
from .chat_source_suggestion import ChatSourceSuggestion


class ChatResponse(BaseModel):
    answer: str
    grounded: bool
    related_policies: list[PolicyOut]
    citations: list[ChatCitation]
    action: Literal['answer', 'clarify', 'update_source'] = 'answer'
    source_suggestions: list[ChatSourceSuggestion] = Field(default_factory=list)
