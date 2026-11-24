"""Customer Attention Items API endpoints."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.concurrency import run_in_threadpool
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession
from app.agent.tool_registry import tool_registry
from app.core.database import get_async_db
from app.db.models import ActivityAuditLog
from app.services.attention_service import AttentionService
from app.schemas.attention import (
    CustomerAttentionItemResponse,
    AttentionItemDetailResponse,
    AttentionStatusUpdate,
    AttentionOverviewMetrics,
)

router = APIRouter(prefix="/attention", tags=["Customer Attention & Intelligence Queue"])


class OutreachDraftRequest(BaseModel):
    channel: str = Field(default="EMAIL", description="EMAIL or SMS")
    approved_by: str = Field(default="Retention Desk", description="Employee preparing the draft")


@router.get("", response_model=List[CustomerAttentionItemResponse])
async def list_attention_items(
    category: Optional[str] = Query(None, description="POLICY_EXPIRY, MISSING_DOCS, PREMIUM_OVERDUE, RENEWAL_FOLLOWUP, RISK_ALERT"),
    urgency_level: Optional[str] = Query(None, description="CRITICAL, HIGH, MEDIUM, LOW"),
    status: Optional[str] = Query(None, description="OPEN, IN_PROGRESS, RESOLVED, DISMISSED, ACTIVE"),
    customer_id: Optional[str] = Query(None, description="Filter by customer ID"),
    sort_by: str = Query("attention_score", description="attention_score, detected_at, urgency_level"),
    order: str = Query("desc", description="asc or desc"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Retrieve prioritized customer attention items with multi-dimensional filtering,
    sorting, pagination, and customer/policy context.
    """
    return await AttentionService.get_attention_items(
        db=db,
        category=category,
        urgency_level=urgency_level,
        status=status,
        customer_id=customer_id,
        sort_by=sort_by,
        order=order,
        skip=skip,
        limit=limit,
    )


@router.get("/overview", response_model=AttentionOverviewMetrics)
async def get_attention_overview(db: AsyncSession = Depends(get_async_db)):
    """Retrieve categorical alert counts, urgency distribution, and total premium at risk."""
    return await AttentionService.get_attention_overview(db)


@router.get("/{attention_id}", response_model=AttentionItemDetailResponse)
async def get_attention_item_detail(
    attention_id: str,
    db: AsyncSession = Depends(get_async_db),
):
    """Retrieve detailed information for an individual attention item including customer, policy, and audit trail."""
    return await AttentionService.get_attention_item_detail(db, attention_id)


@router.patch("/{attention_id}/status", response_model=CustomerAttentionItemResponse)
async def update_attention_status(
    attention_id: str,
    payload: AttentionStatusUpdate,
    db: AsyncSession = Depends(get_async_db),
):
    """
    Update recommendation status (OPEN, IN_PROGRESS, RESOLVED, DISMISSED).
    Automatically records employee action and resolution notes in the audit log.
    """
    return await AttentionService.update_attention_status(
        db=db,
        attention_id=attention_id,
        status=payload.status,
        assigned_to=payload.assigned_to,
        resolved_by=payload.resolved_by,
        resolution_notes=payload.resolution_notes,
    )


@router.post("/{attention_id}/draft-outreach")
async def prepare_outreach_draft(
    attention_id: str,
    payload: OutreachDraftRequest,
    db: AsyncSession = Depends(get_async_db),
) -> Dict[str, Any]:
    """
    Phase 5 Human-in-the-Loop Workflow:
    Generates an outreach draft for employee review using the Python Tool Registry
    and records an audit log entry. Never auto-sends communications.
    """
    item = await AttentionService.get_attention_item_detail(db, attention_id)

    purpose = "RENEWAL_OFFER"
    if item.category == "MISSING_DOCS":
        purpose = "MISSING_KYC_REQUEST"
    elif item.category == "PREMIUM_OVERDUE":
        purpose = "PAYMENT_GRACE_REMINDER"

    draft = await run_in_threadpool(
        tool_registry.execute_tool,
        "generate_outreach_draft",
        {
            "customer_id_or_code": item.customer_id,
            "purpose": purpose,
            "channel": payload.channel.upper(),
        },
    )
    if "error" in draft:
        raise HTTPException(status_code=400, detail=draft["error"])

    db.add(
        ActivityAuditLog(
            customer_id=item.customer_id,
            action_type="OUTREACH_DRAFT_PREPARED",
            actor="EMPLOYEE",
            actor_name=payload.approved_by,
            description=f"Prepared {payload.channel.upper()} outreach draft for attention item '{item.title}'.",
            metadata_payload={"attention_id": attention_id, "channel": payload.channel.upper(), "purpose": purpose},
        )
    )
    await db.commit()
    return draft
