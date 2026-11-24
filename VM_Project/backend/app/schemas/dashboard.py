"""Executive Dashboard Pydantic v2 schemas."""

from datetime import datetime
from typing import Dict, List, Optional
from pydantic import BaseModel, ConfigDict


class ExpirationsByWindow(BaseModel):
    in_7_days: int
    in_15_days: int
    in_30_days: int
    in_60_days: int


class DashboardMetricsResponse(BaseModel):
    # Core Counts
    total_customers: int
    total_active_policies: int
    customers_requiring_attention: int
    high_priority_cases: int  # CRITICAL + HIGH active attention items

    # Operational Deficits
    upcoming_policy_expirations: ExpirationsByWindow
    missing_documents_count: int
    premium_issues_count: int
    total_premium_at_risk: float

    # Categorical Breakdowns
    attention_by_category: Dict[str, int]
    attention_by_urgency: Dict[str, int]
    attention_by_status: Dict[str, int]

    # Portfolio Health
    vip_customers_count: int
    high_risk_customers_count: int

    timestamp: datetime

    model_config = ConfigDict(from_attributes=True)
