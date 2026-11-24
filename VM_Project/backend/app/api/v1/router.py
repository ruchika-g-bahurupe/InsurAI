"""Master API Router for v1 endpoints."""

from fastapi import APIRouter
from app.api.v1.endpoints import (
    health,
    dashboard,
    customers,
    policies,
    attention,
    documents,
    billing,
    renewals,
    analysis,
    copilot,
    knowledge_base,
)

api_router = APIRouter()

api_router.include_router(health.router)
api_router.include_router(dashboard.router)
api_router.include_router(customers.router)
api_router.include_router(policies.router)
api_router.include_router(attention.router)
api_router.include_router(documents.router)
api_router.include_router(billing.router)
api_router.include_router(renewals.router)
api_router.include_router(analysis.router)
api_router.include_router(copilot.router)
api_router.include_router(knowledge_base.router)
