"""Premium Schedule Pydantic v2 schemas."""

from datetime import date, datetime
from typing import List, Optional
from pydantic import BaseModel, ConfigDict, Field


class PremiumScheduleBase(BaseModel):
    policy_id: str
    installment_number: int = 1
    amount_due: float
    due_date: date
    grace_period_end: date
    status: str = Field(default="PENDING", description="PAID, PENDING, OVERDUE, FAILED, WAIVED")
    payment_method: str = Field(default="AUTO_DEBIT", description="CREDIT_CARD, AUTO_DEBIT, ACH, WIRE, UPI")
    paid_at: Optional[datetime] = None
    transaction_reference: Optional[str] = None
    retry_attempts: int = 0
    failure_reason: Optional[str] = None


class PremiumScheduleResponse(PremiumScheduleBase):
    id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class PremiumIssueItem(BaseModel):
    schedule_id: str
    installment_number: int
    amount_due: float
    due_date: date
    grace_period_end: date
    status: str  # OVERDUE, FAILED, PENDING
    payment_method: str
    retry_attempts: int
    failure_reason: Optional[str] = None
    
    # Issue Classification
    issue_type: str = Field(..., description="GRACE_PERIOD, OVERDUE, FAILED_DEBIT, UPCOMING_DUE")
    days_overdue: int  # > 0 if past due_date
    days_grace_remaining: int  # > 0 if today <= grace_period_end

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


class PremiumIssuesSummaryResponse(BaseModel):
    total_issues: int
    in_grace_period_count: int
    overdue_count: int
    failed_auto_debit_count: int
    total_amount_at_risk: float
    items: List[PremiumIssueItem] = []
