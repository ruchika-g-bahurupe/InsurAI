"""Renewal Follow-up Pydantic v2 schemas."""

from datetime import date
from typing import Optional
from pydantic import BaseModel, ConfigDict, Field


class RenewalFollowUpItem(BaseModel):
    policy_id: str
    policy_number: str
    policy_type: str
    plan_name: str
    premium_amount: float
    expiry_date: date
    days_to_expiry: int
    renewal_probability: float = Field(..., ge=0.0, le=1.0)
    auto_renew: bool
    policy_status: str
    
    # Customer Info
    customer_id: str
    customer_name: str
    customer_code: str
    customer_tier: str
    customer_clv: float
    assigned_agent: str

    # Follow-up State
    has_active_attention_item: bool
    attention_item_id: Optional[str] = None
    follow_up_priority: str = Field(..., description="CRITICAL, HIGH, MEDIUM, LOW")
    recommended_action: str

    model_config = ConfigDict(from_attributes=True)


class RenewalFollowUpSummary(BaseModel):
    total_in_window: int
    critical_followups: int
    high_followups: int
    medium_followups: int
    already_actioned_count: int
    total_premium_in_pipeline: float
    items: list[RenewalFollowUpItem] = []
