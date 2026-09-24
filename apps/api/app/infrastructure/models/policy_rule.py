from sqlalchemy import JSON, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base
from .defaults import uid


class PolicyRule(Base):
    __tablename__ = "policy_rules"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    policy_id: Mapped[str] = mapped_column(ForeignKey("policies.id", ondelete="CASCADE"), index=True)
    rule_type: Mapped[str] = mapped_column(String(30), default="condition")
    content: Mapped[str] = mapped_column(Text)
    normalized_data: Mapped[dict] = mapped_column(JSON, default=dict)
    sort_order: Mapped[int] = mapped_column(Integer, default=0)
