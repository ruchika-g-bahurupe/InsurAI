"""Agent Analysis Runs and Telemetry API endpoints."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.agent.proactive_scanner import watchdog_scanner
from app.core.database import get_async_db
from app.db.models import AgentAnalysisRun
from app.schemas.analysis_run import AgentAnalysisRunResponse, TriggerAnalysisRequest

router = APIRouter(prefix="/analysis", tags=["AI Analysis Telemetry & History"])


@router.post("/trigger")
async def trigger_proactive_sweep(payload: Optional[TriggerAnalysisRequest] = None):
    """
    Triggers an autonomous Watchdog customer portfolio investigation.
    - Offloads execution to threadpool (non-blocking).
    - Returns COMPLETED, DEGRADED (if GEMINI_API_KEY is missing), or ALREADY_RUNNING.
    - Raises 500 only on unexpected internal failures.
    """
    trigger_source = payload.trigger_source if payload else "DASHBOARD_MANUAL"
    run_type = payload.run_type if payload else "PROACTIVE_SWEEP"

    result = await run_in_threadpool(
        watchdog_scanner.run_sweep,
        trigger_source=trigger_source,
        run_type=run_type,
    )
    if result.get("status") == "FAILED":
        raise HTTPException(status_code=500, detail=result.get("error"))
    return result


@router.get("/runs", response_model=List[AgentAnalysisRunResponse])
async def list_analysis_runs(
    status: Optional[str] = Query(None, description="RUNNING, COMPLETED, FAILED, DEGRADED"),
    run_type: Optional[str] = Query(None, description="PROACTIVE_SWEEP, ON_DEMAND"),
    limit: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_async_db),
):
    """Retrieve historical autonomous Watchdog investigation runs and tool telemetry."""
    query = select(AgentAnalysisRun)

    if status:
        query = query.where(AgentAnalysisRun.status == status.upper())

    if run_type:
        query = query.where(AgentAnalysisRun.run_type == run_type.upper())

    query = query.order_by(AgentAnalysisRun.started_at.desc()).limit(limit)
    res = await db.execute(query)
    return res.scalars().all()


@router.get("/runs/latest", response_model=AgentAnalysisRunResponse)
async def get_latest_analysis_run(db: AsyncSession = Depends(get_async_db)):
    """Retrieve the most recent AI investigation run."""
    stmt = select(AgentAnalysisRun).order_by(AgentAnalysisRun.started_at.desc()).limit(1)
    res = await db.execute(stmt)
    latest = res.scalars().first()

    if not latest:
        raise HTTPException(status_code=404, detail="No analysis runs found.")

    return latest
