from pydantic import BaseModel


class PolicyUpdate(BaseModel):
    title: str | None = None
    summary: str | None = None
    category: str | None = None
    rules: list[str] | None = None
