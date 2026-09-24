from app.application.dto.orm_model import ORMModel

class RuleOut(ORMModel):
    id: str
    rule_type: str
    content: str
    normalized_data: dict
    sort_order: int
