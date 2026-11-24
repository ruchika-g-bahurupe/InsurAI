"""Customer Attention Items and AI Recommendation Lifecycle model."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, List, Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, utc_now

if TYPE_CHECKING:
    from app.db.models.customer import Customer
    from app.db.models.policy import Policy


class CustomerAttentionItem(Base):
    """Proactive attention item flagged by autonomous AI investigation with full lifecycle management."""
    __tablename__ = "customer_attention_items"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    customer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("customers.id", ondelete="CASCADE"), index=True, nullable=False
    )
    policy_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("policies.id", ondelete="SET NULL"), index=True, nullable=True
    )

    # Category: POLICY_EXPIRY, MISSING_DOCS, PREMIUM_OVERDUE, RENEWAL_FOLLOWUP, RISK_ALERT
    category: Mapped[str] = mapped_column(String(30), index=True, nullable=False)

    # Urgency: CRITICAL, HIGH, MEDIUM, LOW
    urgency_level: Mapped[str] = mapped_column(String(20), default="MEDIUM", index=True, nullable=False)

    # Operational priority score: 0.0 to 100.0
    attention_score: Mapped[float] = mapped_column(Float, default=50.0, index=True, nullable=False)

    # Autonomous agent confidence: HIGH, MEDIUM, LOW
    confidence_level: Mapped[Optional[str]] = mapped_column(String(20), default="MEDIUM", nullable=True)

    # Deduplication key to prevent duplicate active alerts for the same issue
    dedup_key: Mapped[str] = mapped_column(String(150), index=True, nullable=False)

    # Flag to quickly filter active unresolved issues vs historical
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, index=True, nullable=False)

    # Detailed AI Investigation Insights
    title: Mapped[str] = mapped_column(String(160), nullable=False)
    reasoning_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    root_cause: Mapped[str] = mapped_column(String(255), nullable=False)
    ai_summary: Mapped[str] = mapped_column(Text, nullable=False)
    ai_recommendation: Mapped[str] = mapped_column(Text, nullable=False)

    # Structured Investigation Traceability
    identified_risk_factors: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    investigation_steps: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    supporting_evidence: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)
    data_gaps: Mapped[Optional[List[str]]] = mapped_column(JSON, nullable=True)

    # Action Payload (JSON structure for employee-approved execution)
    suggested_action: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    # Recommendation Lifecycle: OPEN -> IN_PROGRESS -> RESOLVED / DISMISSED
    status: Mapped[str] = mapped_column(String(20), default="OPEN", index=True, nullable=False)

    assigned_to: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    detected_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True, nullable=False
    )

    # Resolution Audit
    resolved_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    resolved_by: Mapped[Optional[str]] = mapped_column(String(80), nullable=True)
    resolution_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    customer: Mapped["Customer"] = relationship("Customer", back_populates="attention_items")
    policy: Mapped[Optional["Policy"]] = relationship("Policy", back_populates="attention_items")

    __table_args__ = (
        Index("ix_attention_dedup_active", "dedup_key", "is_active"),
        Index("ix_attention_status_score", "status", "attention_score"),
        Index("ix_attention_cat_urgency", "category", "urgency_level"),
        Index("ix_attention_customer_active", "customer_id", "is_active"),
    )
