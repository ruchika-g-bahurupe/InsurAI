"""Agent Analysis Run History domain model."""

import uuid
from datetime import datetime
from typing import Any, Dict, List, Optional
from sqlalchemy import Boolean, DateTime, Float, Index, Integer, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base, utc_now


class AgentAnalysisRun(Base):
    """Execution history and telemetry for proactive and on-demand AI analysis sweeps."""
    __tablename__ = "agent_analysis_runs"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )

    # Run Types: PROACTIVE_SWEEP, ON_DEMAND, TARGETED_AUDIT
    run_type: Mapped[str] = mapped_column(String(30), default="PROACTIVE_SWEEP", index=True, nullable=False)

    # Trigger: SCHEDULED_CRON, DASHBOARD_MANUAL, SYSTEM_EVENT
    trigger_source: Mapped[str] = mapped_column(String(40), default="DASHBOARD_MANUAL", nullable=False)

    # Status: RUNNING, COMPLETED, FAILED, DEGRADED
    status: Mapped[str] = mapped_column(String(20), default="RUNNING", index=True, nullable=False)

    records_scanned: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    issues_detected: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    new_recommendations_created: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    recommendations_updated: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

    # Autonomous Agent Execution Telemetry
    iterations_used: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tool_calls_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    tool_calls_log: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(JSON, nullable=True)
    degraded_mode: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    execution_time_ms: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    model_used: Mapped[str] = mapped_column(String(60), default="gemini-2.5-pro", nullable=False)

    summary_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=utc_now, index=True, nullable=False
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    __table_args__ = (
        Index("ix_analysis_status_started", "status", "started_at"),
        Index("ix_analysis_type_status", "run_type", "status"),
    )
