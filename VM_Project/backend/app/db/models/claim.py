"""Claims domain model."""

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import Date, DateTime, Float, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, utc_now

if TYPE_CHECKING:
    from app.db.models.customer import Customer
    from app.db.models.policy import Policy


class Claim(Base):
    """Insurance claim filed by a customer against a specific policy."""
    __tablename__ = "claims"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    policy_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("policies.id", ondelete="CASCADE"), index=True, nullable=False
    )
    customer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("customers.id", ondelete="CASCADE"), index=True, nullable=False
    )
    claim_number: Mapped[str] = mapped_column(
        String(30), unique=True, index=True, nullable=False
    )
    claim_amount: Mapped[float] = mapped_column(Float, nullable=False)
    payout_amount: Mapped[Optional[float]] = mapped_column(Float, nullable=True)

    # Status: FILED, UNDER_INVESTIGATION, APPROVED, SETTLED, REJECTED
    status: Mapped[str] = mapped_column(String(30), default="FILED", index=True, nullable=False)
    incident_date: Mapped[date] = mapped_column(Date, nullable=False)
    filed_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    settled_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    adjuster_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Relationships
    policy: Mapped["Policy"] = relationship("Policy", back_populates="claims")
    customer: Mapped["Customer"] = relationship("Customer", back_populates="claims")

    __table_args__ = (
        Index("ix_claims_customer_status", "customer_id", "status"),
        Index("ix_claims_policy_incident", "policy_id", "incident_date"),
    )
