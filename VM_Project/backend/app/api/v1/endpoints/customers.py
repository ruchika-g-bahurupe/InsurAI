"""Customer API endpoints (Directory, Search, and 360° Profile)."""

from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_async_db
from app.services.customer_service import CustomerService
from app.schemas.customer import CustomerSummary

router = APIRouter(prefix="/customers", tags=["Customers"])


@router.get("", response_model=List[CustomerSummary])
async def list_customers(
    search: Optional[str] = Query(None, description="Search by name, email, code, city"),
    tier: Optional[str] = Query(None, description="Filter by VIP, STANDARD, HIGH_NET_WORTH"),
    risk_segment: Optional[str] = Query(None, description="Filter by LOW, MEDIUM, HIGH"),
    status: Optional[str] = Query("ACTIVE", description="ACTIVE, INACTIVE, ALL"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: AsyncSession = Depends(get_async_db),
):
    """Retrieve paginated customer directory with active policies and open attention counts."""
    return await CustomerService.list_customers(
        db=db,
        search=search,
        tier=tier,
        risk_segment=risk_segment,
        status=status,
        skip=skip,
        limit=limit,
    )


@router.get("/{customer_id}", response_model=Dict[str, Any])
async def get_customer_360(customer_id: str, db: AsyncSession = Depends(get_async_db)):
    """
    Retrieve complete 360° customer profile including:
    - Customer demographics & risk tier
    - All policies with premium schedules
    - Compliance documents vault
    - Claims history
    - Attention items & recommendations
    - Activity audit trail
    """
    return await CustomerService.get_customer_360(db=db, customer_id=customer_id)
