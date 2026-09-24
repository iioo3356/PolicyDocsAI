from datetime import datetime
from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base
from .defaults import uid, now
from app.domain.candidate_decision import CandidateDecision
from app.infrastructure.models.source_chunk import SourceChunk

class PolicyCandidate(Base):
    __tablename__ = "policy_candidates"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    source_id: Mapped[str] = mapped_column(ForeignKey("sources.id", ondelete="CASCADE"), index=True)
    source_chunk_id: Mapped[str] = mapped_column(ForeignKey("source_chunks.id", ondelete="CASCADE"))
    proposed_policy_id: Mapped[str | None] = mapped_column(ForeignKey("policies.id"))
    title: Mapped[str] = mapped_column(String(300))
    summary: Mapped[str] = mapped_column(Text)
    category: Mapped[str] = mapped_column(String(500), default="미분류")
    rules: Mapped[list] = mapped_column(JSON, default=list)
    confidence: Mapped[float] = mapped_column(Float, default=0)
    decision: Mapped[CandidateDecision] = mapped_column(Enum(CandidateDecision), default=CandidateDecision.PENDING)
    extraction_data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime)
    chunk: Mapped[SourceChunk] = relationship()
