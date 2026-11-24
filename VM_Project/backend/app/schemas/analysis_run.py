"""Agent Analysis Run Pydantic v2 schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class AgentAnalysisRunBase(BaseModel):
    run_type: str = Field(default="PROACTIVE_SWEEP", description="PROACTIVE_SWEEP, ON_DEMAND, TARGETED_AUDIT")
    trigger_source: str = Field(default="DASHBOARD_MANUAL", description="SCHEDULED_CRON, DASHBOARD_MANUAL, SYSTEM_EVENT")
    status: str = Field(default="RUNNING", description="RUNNING, COMPLETED, FAILED, DEGRADED")
    records_scanned: int = 0
    issues_detected: int = 0
    new_recommendations_created: int = 0
    recommendations_updated: int = 0
    iterations_used: int = 0
    tool_calls_count: int = 0
    tool_calls_log: Optional[List[Dict[str, Any]]] = None
    degraded_mode: bool = False
    execution_time_ms: float = 0.0
    model_used: str = "gemini-2.5-pro"
    summary_notes: Optional[str] = None
    error_message: Optional[str] = None


class AgentAnalysisRunCreate(AgentAnalysisRunBase):
    pass


class AgentAnalysisRunResponse(AgentAnalysisRunBase):
    id: str
    started_at: datetime
    completed_at: Optional[datetime] = None

    model_config = ConfigDict(from_attributes=True)


class TriggerAnalysisRequest(BaseModel):
    run_type: str = Field(default="ON_DEMAND", description="PROACTIVE_SWEEP or ON_DEMAND")
    trigger_source: str = Field(default="DASHBOARD_MANUAL")
    category_filter: Optional[str] = None
