from pydantic import BaseModel, Field

class PolicyInterpretation(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    summary: str = Field(min_length=1, max_length=1000)
    category: str = Field(min_length=1, max_length=500)
    rules: list[str] = Field(min_length=1, max_length=8)
    confidence: float = Field(ge=0, le=1)
    warnings: list[str] = Field(default_factory=list, max_length=5)
