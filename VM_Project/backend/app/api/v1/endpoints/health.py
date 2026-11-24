"""Health check and system telemetry endpoint."""

from fastapi import APIRouter, Depends, Query
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.agent.gemini_client import gemini_client
from app.core.config import settings
from app.core.database import get_async_db

router = APIRouter(prefix="/health", tags=["System Health"])


@router.get("")
async def health_check(db: AsyncSession = Depends(get_async_db)):
    """Validates system, database connectivity, and AI execution mode."""
    db_status = "healthy"
    db_error = None
    try:
        await db.execute(text("SELECT 1"))
    except Exception as e:
        db_status = "unhealthy"
        db_error = str(e)

    is_live = gemini_client.is_live()
    return {
        "status": "online" if db_status == "healthy" else "degraded",
        "app_name": settings.APP_NAME,
        "environment": settings.APP_ENV,
        "database": {
            "status": db_status,
            "engine": "sqlite" if "sqlite" in settings.DATABASE_URL else "postgresql",
            "error": db_error,
        },
        "gemini_live": is_live,
        "ai_mode": "LIVE_GEMINI" if is_live else "COGNITIVE_EMULATION",
        "gemini_model_configured": settings.GEMINI_MODEL,
        "analysis_model_configured": settings.GEMINI_ANALYSIS_MODEL,
    }


@router.get("/gemini")
async def gemini_connectivity_check(
    use_analysis_model: bool = Query(False, description="Test the configured analysis model instead of chat model"),
):
    """Safely tests Gemini API key and model accessibility without exposing secrets."""
    return await run_in_threadpool(gemini_client.test_connectivity, use_analysis_model=use_analysis_model)
