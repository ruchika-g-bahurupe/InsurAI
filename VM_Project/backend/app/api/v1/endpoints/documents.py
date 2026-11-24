"""Document Compliance API endpoints."""

from typing import Optional
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.database import get_async_db
from app.services.document_service import DocumentService
from app.schemas.document import MissingDocumentsSummaryResponse

router = APIRouter(prefix="/documents", tags=["Document Compliance"])


@router.get("/missing", response_model=MissingDocumentsSummaryResponse)
async def get_missing_documents(
    status: Optional[str] = Query(None, description="Filter: PENDING_SUBMISSION, REJECTED, EXPIRED"),
    document_type: Optional[str] = Query(None, description="KYC_ID, MEDICAL_DECLARATION, VEHICLE_INSPECTION, etc."),
    customer_id: Optional[str] = Query(None, description="Filter by customer ID"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Identify customers with missing, pending, rejected, or expired compliance documents.
    - Excludes optional documents (strictly is_mandatory == True).
    - Returns document type, rejection reasons, associated policy, and customer info.
    """
    return await DocumentService.get_missing_documents(
        db=db,
        status_filter=status,
        document_type=document_type,
        customer_id=customer_id,
        skip=skip,
        limit=limit,
    )
