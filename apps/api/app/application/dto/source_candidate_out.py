from app.application.dto.orm_model import ORMModel


class SourceCandidateOut(ORMModel):
    id: str
    title: str
    category: str
    confidence: float
