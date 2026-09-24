from sqlalchemy import JSON, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db import Base
from .defaults import uid
from app.infrastructure.models.source_file import SourceFile

class SourceChunk(Base):
    __tablename__ = "source_chunks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=uid)
    source_file_id: Mapped[str] = mapped_column(ForeignKey("source_files.id", ondelete="CASCADE"), index=True)
    project_id: Mapped[str] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"), index=True)
    chunk_type: Mapped[str] = mapped_column(String(30))
    symbol_name: Mapped[str | None] = mapped_column(String(255))
    document_path: Mapped[str | None] = mapped_column(String(1000))
    start_line: Mapped[int] = mapped_column(Integer)
    end_line: Mapped[int] = mapped_column(Integer)
    content: Mapped[str] = mapped_column(Text)
    candidate_score: Mapped[float] = mapped_column(Float, default=0)
    chunk_metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    file: Mapped[SourceFile] = relationship()
