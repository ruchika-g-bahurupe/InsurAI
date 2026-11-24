"""Renewal Pipeline and Follow-up API endpoints."""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_async_db
from app.services.renewal_service import RenewalService
from app.schemas.renewal import RenewalFollowUpSummary

router = APIRouter(prefix="/renewals", tags=["Renewal Pipeline & Follow-ups"])


@router.get("/follow-ups", response_model=RenewalFollowUpSummary)
async def get_renewal_follow_ups(
    within_days: int = Query(60, description="Window in days for upcoming renewals (e.g. 30, 60, 90)"),
    only_unactioned: bool = Query(False, description="Exclude policies that already have an active attention item"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Identify policies requiring renewal follow-up.
    - Evaluates expiry dates, customer tier, and renewal likelihood.
    - Checks previous follow-up history to avoid duplicate recommendations.
    - Categorizes priority (CRITICAL, HIGH, MEDIUM) with recommended actions.
    """
    return await RenewalService.get_renewal_follow_ups(
        db=db,
        within_days=within_days,
        only_unactioned=only_unactioned,
        skip=skip,
        limit=limit,
    )
