from sqlalchemy import Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base
from .defaults import uid


class PolicyEvidence(Base):
    __tablename__ = "policy_evidence"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    policy_id: Mapped[str] = mapped_column(ForeignKey("policies.id", ondelete="CASCADE"), index=True)
    policy_rule_id: Mapped[str | None] = mapped_column(ForeignKey("policy_rules.id", ondelete="SET NULL"))
    source_chunk_id: Mapped[str] = mapped_column(ForeignKey("source_chunks.id"))
    source_type: Mapped[str] = mapped_column(String(30))
    source_name: Mapped[str] = mapped_column(String(255))
    source_path: Mapped[str] = mapped_column(String(1000))
    start_line: Mapped[int] = mapped_column(Integer)
    end_line: Mapped[int] = mapped_column(Integer)
    excerpt: Mapped[str] = mapped_column(Text)
    extracted_claim: Mapped[str] = mapped_column(Text)
    confidence: Mapped[float] = mapped_column(Float, default=0)
