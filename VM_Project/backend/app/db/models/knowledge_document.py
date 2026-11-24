"""Knowledge Base Document metadata model for RAG subsystem."""

import uuid
from datetime import datetime
from typing import Optional
from sqlalchemy import DateTime, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, utc_now


class KnowledgeDocument(Base):
    """Metadata and indexing status for uploaded Insurance Knowledge Base PDFs."""

    __tablename__ = "knowledge_documents"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    document_name: Mapped[str] = mapped_column(String(255), nullable=False)
    category: Mapped[str] = mapped_column(String(80), index=True, nullable=False)
    policy_type: Mapped[Optional[str]] = mapped_column(String(60), index=True, nullable=True)
    file_hash: Mapped[str] = mapped_column(String(64), unique=True, index=True, nullable=False)
    file_location: Mapped[str] = mapped_column(String(500), nullable=False)
    file_size_bytes: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Processing Status:
    # UPLOADED -> EXTRACTING_TEXT -> CHUNKING -> GENERATING_EMBEDDINGS -> INDEXING -> COMPLETED | FAILED
    processing_status: Mapped[str] = mapped_column(
        String(35), default="UPLOADED", index=True, nullable=False
    )
    page_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    chunk_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    upload_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    last_indexed_timestamp: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True), nullable=True
    )

    __table_args__ = (
        Index("ix_kb_docs_category_status", "category", "processing_status"),
    )
