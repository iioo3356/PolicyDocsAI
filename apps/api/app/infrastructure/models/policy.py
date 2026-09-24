from datetime import datetime
from sqlalchemy import DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base
from .defaults import uid, now
from app.domain.policy_status import PolicyStatus

class Policy(Base):
    __tablename__ = "policies"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    category: Mapped[str] = mapped_column(String(500), default="미분류")
    title: Mapped[str] = mapped_column(String(300))
    summary: Mapped[str] = mapped_column(Text)
    status: Mapped[PolicyStatus] = mapped_column(Enum(PolicyStatus), default=PolicyStatus.REVIEW)
    confidence: Mapped[float] = mapped_column(Float, default=0)
    has_conflict: Mapped[bool] = mapped_column(default=False)
    search_text: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=now, onupdate=now)
    approved_at: Mapped[datetime | None] = mapped_column(DateTime)
    deprecated_at: Mapped[datetime | None] = mapped_column(DateTime)
    rules: Mapped[list["PolicyRule"]] = relationship(cascade="all, delete-orphan", order_by="PolicyRule.sort_order")
    evidence: Mapped[list["PolicyEvidence"]] = relationship(cascade="all, delete-orphan")
