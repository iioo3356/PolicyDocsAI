from typing import Literal
from pydantic import BaseModel


class ChatCitation(BaseModel):
    policy_id: str
    policy_title: str
    source_path: str
    lines: str
    kind: Literal["source", "revision", "policy"] = "source"
    revision_id: str | None = None
