"""Policy Inventory and Expiry Business Service."""

from datetime import date, timedelta
from typing import List, Optional, Tuple
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db.models import Policy, Customer
from app.schemas.policy import (
    PolicyDetailResponse,
    PolicyExpiryItem,
    PolicyExpirySummaryResponse,
    PolicyResponse,
)


class PolicyService:
    @staticmethod
    async def get_expiring_policies(
        db: AsyncSession,
        within_days: int = 30,
        policy_type: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> PolicyExpirySummaryResponse:
        """
        Retrieves active policies expiring within `within_days`.
        - Calculates remaining days accurately.
        - Excludes already expired policies (expiry_date < today).
        - Excludes cancelled/lapsed policies.
        - Eager loads customer details.
        """
        today = date.today()
        target_cutoff = today + timedelta(days=within_days)

        # Base query for upcoming active policies only
        stmt = (
            select(Policy)
            .options(selectinload(Policy.customer))
            .where(
                Policy.expiry_date >= today,
                Policy.expiry_date <= target_cutoff,
                Policy.status.in_(["ACTIVE", "RENEWAL_PENDING"]),
            )
        )

        if policy_type:
            stmt = stmt.where(Policy.policy_type == policy_type.upper())

        # Ordered by urgency: closest expiry first
        stmt = stmt.order_by(Policy.expiry_date.asc())

        # Total counts & premium aggregation before pagination
        count_stmt = select(func.count(Policy.id), func.sum(Policy.premium_amount)).where(
            Policy.expiry_date >= today,
            Policy.expiry_date <= target_cutoff,
            Policy.status.in_(["ACTIVE", "RENEWAL_PENDING"]),
        )
        if policy_type:
            count_stmt = count_stmt.where(Policy.policy_type == policy_type.upper())

        count_res = await db.execute(count_stmt)
        total_count, total_premium = count_res.one()
        total_count = total_count or 0
        total_premium = total_premium or 0.0

        # Paginate
        paginated_stmt = stmt.offset(skip).limit(limit)
        res = await db.execute(paginated_stmt)
        policies = res.scalars().all()

        items = []
        for p in policies:
            c = p.customer
            days_left = (p.expiry_date - today).days
            items.append(
                PolicyExpiryItem(
                    policy_id=p.id,
                    policy_number=p.policy_number,
                    policy_type=p.policy_type,
                    plan_name=p.plan_name,
                    premium_amount=p.premium_amount,
                    sum_insured=p.sum_insured,
                    start_date=p.start_date,
                    expiry_date=p.expiry_date,
                    days_remaining=days_left,
                    status=p.status,
                    auto_renew=p.auto_renew,
                    renewal_probability=p.renewal_probability,
                    customer_id=c.id if c else "UNKNOWN",
                    customer_name=c.full_name if c else "Unknown Customer",
                    customer_code=c.customer_code if c else "N/A",
                    customer_email=c.email if c else "N/A",
                    customer_phone=c.phone if c else "N/A",
                    customer_tier=c.tier if c else "STANDARD",
                    assigned_agent=c.assigned_agent if c else "Unassigned",
                )
            )

        return PolicyExpirySummaryResponse(
            filter_window_days=within_days,
            total_expiring=total_count,
            total_premium_at_stake=round(total_premium, 2),
            items=items,
        )

    @staticmethod
    async def get_policies(
        db: AsyncSession,
        customer_id: Optional[str] = None,
        policy_type: Optional[str] = None,
        status: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> List[PolicyResponse]:
        """List general policy inventory with filters."""
        stmt = select(Policy)

        if customer_id:
            stmt = stmt.where(Policy.customer_id == customer_id)
        if policy_type:
            stmt = stmt.where(Policy.policy_type == policy_type.upper())
        if status:
            stmt = stmt.where(Policy.status == status.upper())

        stmt = stmt.order_by(Policy.expiry_date.asc()).offset(skip).limit(limit)
        res = await db.execute(stmt)
        return res.scalars().all()

    @staticmethod
    async def get_policy_detail(db: AsyncSession, policy_id: str) -> PolicyDetailResponse:
        """Fetch policy details with eager-loaded documents, billing schedules, and claims."""
        stmt = (
            select(Policy)
            .options(
                selectinload(Policy.documents),
                selectinload(Policy.premium_schedules),
                selectinload(Policy.claims),
            )
            .where(Policy.id == policy_id)
        )
        res = await db.execute(stmt)
        policy = res.scalars().first()

        if not policy:
            raise HTTPException(status_code=404, detail="Policy not found.")

        return policy
