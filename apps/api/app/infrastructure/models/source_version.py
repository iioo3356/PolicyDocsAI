from sqlalchemy import JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


class SourceVersion(Base):
    __tablename__ = 'source_versions'
    source_id: Mapped[str] = mapped_column(ForeignKey('sources.id', ondelete='CASCADE'), primary_key=True)
    previous_source_id: Mapped[str] = mapped_column(ForeignKey('sources.id', ondelete='RESTRICT'), index=True)
    expected_policies: Mapped[dict] = mapped_column(JSON, default=dict)
