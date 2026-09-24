from datetime import datetime
from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base
from .defaults import uid, now


class PolicyConflict(Base):
    __tablename__ = "policy_conflicts"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    policy_id: Mapped[str] = mapped_column(ForeignKey("policies.id", ondelete="CASCADE"), index=True)
    description: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), default="OPEN")
    details: Mapped[dict] = mapped_column(JSON, default=dict)
    resolution_note: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=now)
