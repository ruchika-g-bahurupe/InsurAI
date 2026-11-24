"""Activity Audit Log domain model."""

import uuid
from datetime import datetime
from typing import TYPE_CHECKING, Any, Dict, Optional
from sqlalchemy import DateTime, ForeignKey, Index, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, utc_now

if TYPE_CHECKING:
    from app.db.models.customer import Customer


class ActivityAuditLog(Base):
    """Immutable audit trail for all employee and AI agent actions."""
    __tablename__ = "activity_audit_logs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    customer_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("customers.id", ondelete="SET NULL"), index=True, nullable=True
    )

    # Action: ATTENTION_FLAGGED, OUTREACH_SENT, STATUS_CHANGED, DOCUMENT_VERIFIED, GRACE_EXTENDED, RESOLUTION_LOGGED
    action_type: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    
    # Actor: SYSTEM_AI, EMPLOYEE, AGENT_COPILOT
    actor: Mapped[str] = mapped_column(String(30), default="SYSTEM_AI", index=True, nullable=False)
    actor_name: Mapped[str] = mapped_column(String(80), default="Automated AI Watchdog", nullable=False)

    description: Mapped[str] = mapped_column(Text, nullable=False)
    metadata_payload: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True, nullable=False
    )

    # Relationships
    customer: Mapped[Optional["Customer"]] = relationship("Customer", back_populates="audit_logs")

    __table_args__ = (
        Index("ix_audit_customer_action", "customer_id", "action_type"),
        Index("ix_audit_created_actor", "created_at", "actor"),
    )
