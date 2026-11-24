"""Executive Intelligence Dashboard metrics endpoint."""

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_async_db
from app.services.dashboard_service import DashboardService
from app.schemas.dashboard import DashboardMetricsResponse

router = APIRouter(prefix="/dashboard", tags=["Executive Dashboard"])


@router.get("/metrics", response_model=DashboardMetricsResponse)
async def get_dashboard_metrics(db: AsyncSession = Depends(get_async_db)):
    """
    Dynamically computes high-level executive KPIs:
    - Total customers & active policies
    - Customers requiring immediate attention
    - Upcoming expirations (7, 15, 30, 60 days)
    - Missing mandatory documents count
    - Premium issues count & total premium at risk
    - High-priority cases count (CRITICAL + HIGH)
    - Categorical & urgency distributions
    """
    return await DashboardService.get_dashboard_metrics(db)
