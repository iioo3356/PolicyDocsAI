from pydantic import BaseModel


class NavigationItem(BaseModel):
    category: str
    policies: list[dict[str, str]]
