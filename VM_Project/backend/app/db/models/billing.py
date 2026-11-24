"""Premium Billing and Payment Schedule domain model."""

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import Date, DateTime, Float, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, utc_now

if TYPE_CHECKING:
    from app.db.models.policy import Policy


class PremiumSchedule(Base):
    """Installment schedule and billing status for an insurance policy."""
    __tablename__ = "premium_schedules"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    policy_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("policies.id", ondelete="CASCADE"), index=True, nullable=False
    )
    installment_number: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    amount_due: Mapped[float] = mapped_column(Float, nullable=False)

    due_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    grace_period_end: Mapped[date] = mapped_column(Date, index=True, nullable=False)

    # Status: PAID, PENDING, OVERDUE, FAILED, WAIVED
    status: Mapped[str] = mapped_column(String(20), default="PENDING", index=True, nullable=False)
    
    # Method: CREDIT_CARD, AUTO_DEBIT, ACH, WIRE, UPI
    payment_method: Mapped[str] = mapped_column(String(30), default="AUTO_DEBIT", nullable=False)
    paid_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    transaction_reference: Mapped[Optional[str]] = mapped_column(String(60), nullable=True)
    
    retry_attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    failure_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )

    # Relationships
    policy: Mapped["Policy"] = relationship("Policy", back_populates="premium_schedules")

    __table_args__ = (
        Index("ix_premium_due_status", "due_date", "status"),
        Index("ix_premium_grace_status", "grace_period_end", "status"),
    )
