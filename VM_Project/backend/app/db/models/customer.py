"""Customer domain model."""

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, List, Optional
from sqlalchemy import Date, DateTime, Float, Index, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, utc_now

if TYPE_CHECKING:
    from app.db.models.policy import Policy
    from app.db.models.attention import CustomerAttentionItem
    from app.db.models.document import PolicyDocument
    from app.db.models.claim import Claim
    from app.db.models.conversation import AgentConversation
    from app.db.models.audit import ActivityAuditLog


class Customer(Base):
    """Core insurance customer profile."""
    __tablename__ = "customers"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    customer_code: Mapped[str] = mapped_column(
        String(20), unique=True, index=True, nullable=False
    )
    first_name: Mapped[str] = mapped_column(String(60), nullable=False)
    last_name: Mapped[str] = mapped_column(String(60), nullable=False)
    email: Mapped[str] = mapped_column(String(120), unique=True, index=True, nullable=False)
    phone: Mapped[str] = mapped_column(String(25), nullable=False)
    date_of_birth: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    # Segmentation & Risk Classification
    # Tier: STANDARD, VIP, HIGH_NET_WORTH
    tier: Mapped[str] = mapped_column(String(30), default="STANDARD", index=True, nullable=False)
    # Risk: LOW, MEDIUM, HIGH
    risk_segment: Mapped[str] = mapped_column(String(20), default="LOW", index=True, nullable=False)
    total_clv: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)

    assigned_agent: Mapped[str] = mapped_column(String(80), default="Unassigned", nullable=False)
    city: Mapped[str] = mapped_column(String(60), nullable=False)
    state: Mapped[str] = mapped_column(String(60), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="ACTIVE", index=True, nullable=False)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relationships
    policies: Mapped[List["Policy"]] = relationship(
        "Policy", back_populates="customer", cascade="all, delete-orphan"
    )
    attention_items: Mapped[List["CustomerAttentionItem"]] = relationship(
        "CustomerAttentionItem", back_populates="customer", cascade="all, delete-orphan"
    )
    documents: Mapped[List["PolicyDocument"]] = relationship(
        "PolicyDocument", back_populates="customer", cascade="all, delete-orphan"
    )
    claims: Mapped[List["Claim"]] = relationship(
        "Claim", back_populates="customer", cascade="all, delete-orphan"
    )
    conversations: Mapped[List["AgentConversation"]] = relationship(
        "AgentConversation", back_populates="customer"
    )
    audit_logs: Mapped[List["ActivityAuditLog"]] = relationship(
        "ActivityAuditLog", back_populates="customer"
    )

    @property
    def full_name(self) -> str:
        return f"{self.first_name} {self.last_name}"

    __table_args__ = (
        Index("ix_customers_tier_risk", "tier", "risk_segment"),
        Index("ix_customers_status_created", "status", "created_at"),
    )
