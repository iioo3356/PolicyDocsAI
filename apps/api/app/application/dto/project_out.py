from datetime import datetime
from app.application.dto.orm_model import ORMModel

class ProjectOut(ORMModel):
    id: str
    name: str
    description: str | None
    created_at: datetime
