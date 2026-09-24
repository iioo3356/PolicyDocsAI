from pydantic import BaseModel


class ChatSourceSuggestion(BaseModel):
    source_id: str
    source_name: str
    policy_id: str
    policy_title: str
