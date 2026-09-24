"""Historical chat proposals; creation and application are no longer supported."""
from datetime import datetime
from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base
from .defaults import uid


class ChatProposal(Base):
    __tablename__ = 'chat_proposals'
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    project_id: Mapped[str] = mapped_column(ForeignKey('projects.id', ondelete='CASCADE'), index=True)
    policy_id: Mapped[str] = mapped_column(ForeignKey('policies.id', ondelete='CASCADE'), index=True)
    instruction: Mapped[str] = mapped_column(Text)
    expected: Mapped[dict] = mapped_column(JSON)
    replacement: Mapped[dict] = mapped_column(JSON)
    expires_at: Mapped[datetime] = mapped_column(DateTime)
    status: Mapped[str] = mapped_column(String(20), default='pending')
    revision_id: Mapped[str | None] = mapped_column(ForeignKey('policy_revisions.id'))
