"""Claims Pydantic v2 schemas."""

from datetime import date, datetime
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class ClaimBase(BaseModel):
    policy_id: str
    customer_id: str
    claim_number: str
    claim_amount: float
    payout_amount: Optional[float] = None
    status: str = Field(default="FILED", description="FILED, UNDER_INVESTIGATION, APPROVED, SETTLED, REJECTED")
    incident_date: date
    description: str
    adjuster_notes: Optional[str] = None


class ClaimResponse(ClaimBase):
    id: str
    filed_at: datetime
    settled_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)
