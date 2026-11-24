"""Policy and Customer Compliance Document domain model."""

import uuid
from datetime import date, datetime
from typing import TYPE_CHECKING, Optional
from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Index, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base, utc_now

if TYPE_CHECKING:
    from app.db.models.customer import Customer
    from app.db.models.policy import Policy


class PolicyDocument(Base):
    """Regulatory and underwriting document linked to policy and customer."""
    __tablename__ = "policy_documents"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    policy_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("policies.id", ondelete="CASCADE"), index=True, nullable=False
    )
    customer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("customers.id", ondelete="CASCADE"), index=True, nullable=False
    )

    # Document Type: KYC_ID, MEDICAL_DECLARATION, VEHICLE_INSPECTION, PROOF_OF_ADDRESS, INCOME_PROOF, PROPERTY_SURVEY
    document_type: Mapped[str] = mapped_column(String(40), index=True, nullable=False)
    document_name: Mapped[str] = mapped_column(String(120), nullable=False)
    file_url: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)

    # Status: VERIFIED, PENDING_SUBMISSION, REJECTED, EXPIRED
    status: Mapped[str] = mapped_column(String(25), default="PENDING_SUBMISSION", index=True, nullable=False)
    is_mandatory: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    
    rejection_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    expiry_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)

    submitted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    verified_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, onupdate=utc_now, nullable=False
    )

    # Relationships
    policy: Mapped["Policy"] = relationship("Policy", back_populates="documents")
    customer: Mapped["Customer"] = relationship("Customer", back_populates="documents")

    __table_args__ = (
        Index("ix_documents_status_mandatory", "status", "is_mandatory"),
        Index("ix_documents_policy_type", "policy_id", "document_type"),
    )
