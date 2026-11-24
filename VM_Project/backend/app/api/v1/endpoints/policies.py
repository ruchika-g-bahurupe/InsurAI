"""Policy API endpoints (Inventory, Expiry Tracker, and Status Details)."""

from typing import List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_async_db
from app.services.policy_service import PolicyService
from app.schemas.policy import (
    PolicyDetailResponse,
    PolicyExpirySummaryResponse,
    PolicyResponse,
)

router = APIRouter(prefix="/policies", tags=["Policies"])


@router.get("", response_model=List[PolicyResponse])
async def list_policies(
    policy_type: Optional[str] = Query(None, description="HEALTH, MOTOR, LIFE, PROPERTY, COMMERCIAL"),
    status: Optional[str] = Query(None, description="ACTIVE, GRACE_PERIOD, LAPSED, RENEWAL_PENDING"),
    customer_id: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_async_db),
):
    """List policies with multi-line underwriting filters."""
    return await PolicyService.get_policies(
        db=db,
        customer_id=customer_id,
        policy_type=policy_type,
        status=status,
        skip=skip,
        limit=limit,
    )


@router.get("/expiring", response_model=PolicyExpirySummaryResponse)
async def get_expiring_policies(
    within_days: int = Query(30, description="Window in days: 7, 15, 30, or 60"),
    policy_type: Optional[str] = Query(None, description="Filter by policy type"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Retrieve policies expiring within 7, 15, 30, or 60 days.
    - Accurately calculates remaining days.
    - Excludes already expired policies.
    - Eager-loads full customer details.
    """
    return await PolicyService.get_expiring_policies(
        db=db,
        within_days=within_days,
        policy_type=policy_type,
        skip=skip,
        limit=limit,
    )


@router.get("/{policy_id}", response_model=PolicyDetailResponse)
async def get_policy_detail(policy_id: str, db: AsyncSession = Depends(get_async_db)):
    """Retrieve policy details including document vault, billing schedules, and claims."""
    return await PolicyService.get_policy_detail(db=db, policy_id=policy_id)
