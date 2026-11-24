"""Policy domain model."""

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, utc_now

if TYPE_CHECKING:
    from app.db.models.customer import Customer
    from app.db.models.document import PolicyDocument
    from app.db.models.billing import PremiumSchedule
    from app.db.models.claim import Claim
    from app.db.models.attention import CustomerAttentionItem


class Policy(Base):
    """Insurance policy owned by a customer."""
    __tablename__ = "policies"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    customer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("customers.id", ondelete="CASCADE"), index=True, nullable=False
    )
    policy_number: Mapped[str] = mapped_column(
        String(30), unique=True, index=True, nullable=False
    )
    # Types: HEALTH, MOTOR, LIFE, PROPERTY, COMMERCIAL
    policy_type: Mapped[str] = mapped_column(String(30), index=True, nullable=False)
    plan_name: Mapped[str] = mapped_column(String(100), nullable=False)

    sum_insured: Mapped[float] = mapped_column(Float, nullable=False)
    premium_amount: Mapped[float] = mapped_column(Float, nullable=False)
    # Frequency: MONTHLY, QUARTERLY, SEMI_ANNUAL, ANNUAL
    payment_frequency: Mapped[str] = mapped_column(String(20), default="ANNUAL", nullable=False)

    start_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiry_date: Mapped[date] = mapped_column(Date, index=True, nullable=False)
    
    # Status: ACTIVE, GRACE_PERIOD, LAPSED, RENEWAL_PENDING, CANCELLED
    status: Mapped[str] = mapped_column(String(25), default="ACTIVE", index=True, nullable=False)
    auto_renew: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    
    # Calculated renewal likelihood (0.0 to 1.0)
    renewal_probability: Mapped[float] = mapped_column(Float, default=0.75, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relationships
    customer: Mapped["Customer"] = relationship("Customer", back_populates="policies")
    documents: Mapped[List["PolicyDocument"]] = relationship(
        "PolicyDocument", back_populates="policy", cascade="all, delete-orphan"
    )
    premium_schedules: Mapped[List["PremiumSchedule"]] = relationship(
        "PremiumSchedule", back_populates="policy", cascade="all, delete-orphan"
    )
    claims: Mapped[List["Claim"]] = relationship(
        "Claim", back_populates="policy", cascade="all, delete-orphan"
    )
    attention_items: Mapped[List["CustomerAttentionItem"]] = relationship(
        "CustomerAttentionItem", back_populates="policy"
    )

    __table_args__ = (
        Index("ix_policies_expiry_status", "expiry_date", "status"),
        Index("ix_policies_customer_type", "customer_id", "policy_type"),
    )
