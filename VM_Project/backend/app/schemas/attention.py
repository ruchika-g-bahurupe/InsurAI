"""Customer Attention Item Pydantic v2 schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class CustomerAttentionItemBase(BaseModel):
    customer_id: str
    policy_id: Optional[str] = None
    category: str = Field(
        ...,
        description="POLICY_EXPIRY, MISSING_DOCS, PREMIUM_OVERDUE, RENEWAL_FOLLOWUP, RISK_ALERT",
    )
    urgency_level: str = Field(
        default="MEDIUM",
        description="CRITICAL, HIGH, MEDIUM, LOW",
    )
    attention_score: float = Field(
        default=50.0,
        ge=0.0,
        le=100.0,
        description="0-100 operational priority score assigned by the agent",
    )
    confidence_level: Optional[str] = Field(
        default="MEDIUM",
        description="HIGH, MEDIUM, LOW",
    )
    dedup_key: str = Field(..., description="Unique issue deduplication key")
    is_active: bool = True
    title: str
    reasoning_summary: Optional[str] = None
    root_cause: str
    ai_summary: str
    ai_recommendation: str
    identified_risk_factors: Optional[List[str]] = None
    investigation_steps: Optional[List[str]] = None
    supporting_evidence: Optional[List[str]] = None
    data_gaps: Optional[List[str]] = None
    suggested_action: Optional[Dict[str, Any]] = None
    status: str = Field(
        default="OPEN",
        description="OPEN, IN_PROGRESS, RESOLVED, DISMISSED",
    )
    assigned_to: Optional[str] = None


class CustomerAttentionItemCreate(CustomerAttentionItemBase):
    pass


class AttentionStatusUpdate(BaseModel):
    status: str = Field(
        ...,
        description="New lifecycle status: OPEN, IN_PROGRESS, RESOLVED, DISMISSED",
    )
    assigned_to: Optional[str] = None
    resolved_by: Optional[str] = None
    resolution_notes: Optional[str] = None


class AttentionResolveRequest(BaseModel):
    resolved_by: str
    resolution_notes: str
    dismissed: bool = False


class CustomerAttentionItemResponse(CustomerAttentionItemBase):
    id: str
    detected_at: datetime
    resolved_at: Optional[datetime] = None
    resolved_by: Optional[str] = None
    resolution_notes: Optional[str] = None
    customer_name: Optional[str] = None
    customer_code: Optional[str] = None
    customer_tier: Optional[str] = None
    customer_email: Optional[str] = None
    customer_phone: Optional[str] = None
    policy_number: Optional[str] = None
    policy_type: Optional[str] = None

    model_config = ConfigDict(from_attributes=True)


class AttentionOverviewMetrics(BaseModel):
    total_active_alerts: int
    critical_alerts: int
    high_alerts: int
    medium_alerts: int
    low_alerts: int
    policy_expiry_count: int
    missing_docs_count: int
    premium_issues_count: int
    renewal_followup_count: int
    risk_alert_count: int
    total_premium_at_risk: float


class AttentionAuditEntry(BaseModel):
    id: str
    action_type: str
    actor: str
    actor_name: str
    description: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AttentionItemDetailResponse(CustomerAttentionItemResponse):
    customer_details: Optional[Dict[str, Any]] = None
    policy_details: Optional[Dict[str, Any]] = None
    audit_history: List[AttentionAuditEntry] = []

    model_config = ConfigDict(from_attributes=True)
