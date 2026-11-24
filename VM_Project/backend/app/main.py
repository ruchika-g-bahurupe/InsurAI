"""FastAPI Application Entry Point for VM_project."""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_router
from app.core.config import settings
from app.core.logging import logger
from app.db.init_db import init_database


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan event handler for application startup and shutdown."""
    logger.info(f"Starting {settings.APP_NAME} in [{settings.APP_ENV}] mode...")
    logger.info(f"Using database: {settings.DATABASE_URL}")
    logger.info(f"Configured Gemini Model: {settings.GEMINI_MODEL}")
    
    # Initialize DB tables if they don't already exist
    try:
        init_database()
    except Exception as e:
        logger.error(f"Error ensuring database tables on startup: {e}")

    yield

    logger.info(f"Shutting down {settings.APP_NAME}...")


def create_app() -> FastAPI:
    """Application factory for FastAPI."""
    app = FastAPI(
        title=settings.APP_NAME,
        description=(
            "Enterprise Insurance Customer Intelligence & Retention Platform API. "
            "Features Proactive Autonomous Customer Monitoring and Conversational AI Copilot."
        ),
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url=f"{settings.API_V1_STR}/openapi.json",
        lifespan=lifespan,
    )

    # CORS Middleware Configuration
    origins = settings.CORS_ORIGINS
    if isinstance(origins, str):
        origins = [origins]

    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Register API v1 router
    app.include_router(api_router, prefix=settings.API_V1_STR)

    @app.get("/", tags=["Root"])
    async def root():
        return {
            "platform": settings.APP_NAME,
            "version": "1.0.0",
            "docs": "/docs",
            "api_v1": settings.API_V1_STR,
            "health": f"{settings.API_V1_STR}/health",
        }

    return app


app = create_app()
