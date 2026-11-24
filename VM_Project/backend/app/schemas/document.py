"""Policy Document Pydantic v2 schemas."""

from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class PolicyDocumentBase(BaseModel):
    policy_id: str
    customer_id: str
    document_type: str = Field(
        ...,
        description="KYC_ID, MEDICAL_DECLARATION, VEHICLE_INSPECTION, PROOF_OF_ADDRESS, INCOME_PROOF, PROPERTY_SURVEY"
    )
    document_name: str
    file_url: Optional[str] = None
    status: str = Field(default="PENDING_SUBMISSION", description="VERIFIED, PENDING_SUBMISSION, REJECTED, EXPIRED")
    is_mandatory: bool = True
    rejection_reason: Optional[str] = None
    expiry_date: Optional[date] = None


class PolicyDocumentResponse(PolicyDocumentBase):
    id: str
    submitted_at: Optional[datetime] = None
    verified_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class MissingDocumentItem(BaseModel):
    document_id: str
    document_type: str
    document_name: str
    status: str  # PENDING_SUBMISSION, REJECTED, EXPIRED
    is_mandatory: bool
    rejection_reason: Optional[str] = None
    expiry_date: Optional[date] = None
    submitted_at: Optional[datetime] = None

    # Associated Policy Info
    policy_id: str
    policy_number: str
    policy_type: str
    plan_name: str
    policy_status: str

    # Associated Customer Info
    customer_id: str
    customer_name: str
    customer_code: str
    customer_email: str
    customer_phone: str
    customer_tier: str
    assigned_agent: str

    model_config = ConfigDict(from_attributes=True)


class MissingDocumentsSummaryResponse(BaseModel):
    total_deficits: int
    pending_count: int
    rejected_count: int
    expired_count: int
    affected_customers_count: int
    items: List[MissingDocumentItem] = []
