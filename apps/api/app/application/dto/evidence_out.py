from app.application.dto.orm_model import ORMModel

class EvidenceOut(ORMModel):
    id: str
    source_chunk_id: str
    source_type: str
    source_name: str
    source_path: str
    start_line: int
    end_line: int
    excerpt: str
    extracted_claim: str
    confidence: float
