from pydantic import BaseModel, Field


class SourceRoleUpdate(BaseModel):
    role: str = Field(min_length=1, max_length=50, pattern=r"^[\w가-힣 ./_-]+$")
