"""Premium Billing and Payment Issues API endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_async_db
from app.services.billing_service import BillingService
from app.schemas.billing import PremiumIssuesSummaryResponse

router = APIRouter(prefix="/billing", tags=["Premium Billing & Collections"])


@router.get("/issues", response_model=PremiumIssuesSummaryResponse)
async def get_premium_issues(
    issue_type: Optional[str] = Query(None, description="OVERDUE, GRACE_PERIOD, FAILED_DEBIT, UPCOMING"),
    customer_id: Optional[str] = Query(None, description="Filter by customer ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Retrieve premium payment issues:
    - Overdue payments.
    - Payments in active grace periods.
    - Failed auto-debit retries.
    - Upcoming payments due in the next 30 days.
    Returns amount due, due date, status, days overdue, and customer context.
    """
    return await BillingService.get_premium_issues(
        db=db,
        issue_type=issue_type,
        customer_id=customer_id,
        skip=skip,
        limit=limit,
    )
