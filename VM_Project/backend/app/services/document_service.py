"""Document Compliance and Missing Documents Business Service."""

from typing import Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db.models import PolicyDocument
from app.schemas.document import MissingDocumentItem, MissingDocumentsSummaryResponse


class DocumentService:
    @staticmethod
    async def get_missing_documents(
        db: AsyncSession,
        status_filter: Optional[str] = None,
        document_type: Optional[str] = None,
        customer_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> MissingDocumentsSummaryResponse:
        """
        Retrieves compliance deficits:
        - Only checks mandatory documents (is_mandatory == True).
        - Statuses: PENDING_SUBMISSION, REJECTED, EXPIRED.
        - Eager loads associated policy and customer details.
        - Applies filters consistently to both summary statistics and paginated items.
        """
        deficit_statuses = ["PENDING_SUBMISSION", "REJECTED", "EXPIRED"]
        target_statuses = [status_filter.upper()] if status_filter else deficit_statuses

        stmt = (
            select(PolicyDocument)
            .options(
                selectinload(PolicyDocument.policy),
                selectinload(PolicyDocument.customer),
            )
            .where(
                PolicyDocument.is_mandatory == True,
                PolicyDocument.status.in_(target_statuses),
            )
        )

        stats_stmt = (
            select(
                func.count(PolicyDocument.id).label("total"),
                func.count(PolicyDocument.id).filter(PolicyDocument.status == "PENDING_SUBMISSION").label("pending"),
                func.count(PolicyDocument.id).filter(PolicyDocument.status == "REJECTED").label("rejected"),
                func.count(PolicyDocument.id).filter(PolicyDocument.status == "EXPIRED").label("expired"),
                func.count(func.distinct(PolicyDocument.customer_id)).label("unique_customers"),
            )
            .where(
                PolicyDocument.is_mandatory == True,
                PolicyDocument.status.in_(target_statuses),
            )
        )

        if document_type:
            dt = document_type.upper()
            stmt = stmt.where(PolicyDocument.document_type == dt)
            stats_stmt = stats_stmt.where(PolicyDocument.document_type == dt)

        if customer_id:
            stmt = stmt.where(PolicyDocument.customer_id == customer_id)
            stats_stmt = stats_stmt.where(PolicyDocument.customer_id == customer_id)

        stats_res = await db.execute(stats_stmt)
        stats_row = stats_res.one()

        total_deficits = stats_row.total or 0
        pending_count = stats_row.pending or 0
        rejected_count = stats_row.rejected or 0
        expired_count = stats_row.expired or 0
        unique_customers = stats_row.unique_customers or 0

        paginated_stmt = stmt.order_by(PolicyDocument.created_at.desc()).offset(skip).limit(limit)
        res = await db.execute(paginated_stmt)
        docs = res.scalars().all()

        items = []
        for d in docs:
            p = d.policy
            c = d.customer
            items.append(
                MissingDocumentItem(
                    document_id=d.id,
                    document_type=d.document_type,
                    document_name=d.document_name,
                    status=d.status,
                    is_mandatory=d.is_mandatory,
                    rejection_reason=d.rejection_reason,
                    expiry_date=d.expiry_date,
                    submitted_at=d.submitted_at,
                    policy_id=p.id if p else "UNKNOWN",
                    policy_number=p.policy_number if p else "N/A",
                    policy_type=p.policy_type if p else "N/A",
                    plan_name=p.plan_name if p else "N/A",
                    policy_status=p.status if p else "N/A",
                    customer_id=c.id if c else "UNKNOWN",
                    customer_name=c.full_name if c else "Unknown Customer",
                    customer_code=c.customer_code if c else "N/A",
                    customer_email=c.email if c else "N/A",
                    customer_phone=c.phone if c else "N/A",
                    customer_tier=c.tier if c else "STANDARD",
                    assigned_agent=c.assigned_agent if c else "Unassigned",
                )
            )

        return MissingDocumentsSummaryResponse(
            total_deficits=total_deficits,
            pending_count=pending_count,
            rejected_count=rejected_count,
            expired_count=expired_count,
            affected_customers_count=unique_customers,
            items=items,
        )
