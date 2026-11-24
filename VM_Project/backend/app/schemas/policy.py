"""Policy Pydantic v2 schemas."""

from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field
from app.schemas.document import PolicyDocumentResponse
from app.schemas.billing import PremiumScheduleResponse
from app.schemas.claim import ClaimResponse


class PolicyBase(BaseModel):
    customer_id: str
    policy_number: str
    policy_type: str = Field(..., description="HEALTH, MOTOR, LIFE, PROPERTY, COMMERCIAL")
    plan_name: str
    sum_insured: float
    premium_amount: float
    payment_frequency: str = Field(default="ANNUAL", description="MONTHLY, QUARTERLY, SEMI_ANNUAL, ANNUAL")
    start_date: date
    expiry_date: date
    status: str = Field(default="ACTIVE", description="ACTIVE, GRACE_PERIOD, LAPSED, RENEWAL_PENDING, CANCELLED")
    auto_renew: bool = False
    renewal_probability: float = Field(default=0.75, ge=0.0, le=1.0)


class PolicyCreate(PolicyBase):
    pass


class PolicyResponse(PolicyBase):
    id: str
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PolicyDetailResponse(PolicyResponse):
    documents: List[PolicyDocumentResponse] = []
    premium_schedules: List[PremiumScheduleResponse] = []
    claims: List[ClaimResponse] = []

    model_config = ConfigDict(from_attributes=True)


class PolicyExpiryItem(BaseModel):
    policy_id: str
    policy_number: str
    policy_type: str
    plan_name: str
    premium_amount: float
    sum_insured: float
    start_date: date
    expiry_date: date
    days_remaining: int
    status: str
    auto_renew: bool
    renewal_probability: float

    # Associated Customer Details
    customer_id: str
    customer_name: str
    customer_code: str
    customer_email: str
    customer_phone: str
    customer_tier: str
    assigned_agent: str

    model_config = ConfigDict(from_attributes=True)


class PolicyExpirySummaryResponse(BaseModel):
    filter_window_days: int
    total_expiring: int
    total_premium_at_stake: float
    items: List[PolicyExpiryItem] = []
