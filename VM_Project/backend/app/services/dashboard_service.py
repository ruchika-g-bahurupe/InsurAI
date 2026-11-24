"""Executive Dashboard Business Service."""

from datetime import date, datetime, timedelta, timezone
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import (
    Customer,
    Policy,
    PolicyDocument,
    PremiumSchedule,
    CustomerAttentionItem,
)
from app.schemas.dashboard import DashboardMetricsResponse, ExpirationsByWindow


class DashboardService:
    @staticmethod
    async def get_dashboard_metrics(db: AsyncSession) -> DashboardMetricsResponse:
        """Dynamically computes all high-level operational metrics with 0 hardcoded values."""
        today = date.today()

        # 1. Total Customers & Segments
        cust_stmt = select(
            func.count(Customer.id).label("total"),
            func.count(Customer.id).filter(Customer.tier.in_(["VIP", "HIGH_NET_WORTH"])).label("vip_count"),
            func.count(Customer.id).filter(Customer.risk_segment == "HIGH").label("high_risk_count"),
        )
        cust_res = await db.execute(cust_stmt)
        total_cust, vip_count, high_risk_count = cust_res.one()
        total_cust = total_cust or 0
        vip_count = vip_count or 0
        high_risk_count = high_risk_count or 0

        # 2. Total Active Policies
        pol_active_stmt = select(func.count(Policy.id)).where(Policy.status == "ACTIVE")
        pol_active_res = await db.execute(pol_active_stmt)
        total_active_policies = pol_active_res.scalar() or 0

        # 3. Upcoming Policy Expirations (7, 15, 30, 60 days)
        exp_7_res = await db.execute(
            select(func.count(Policy.id)).where(
                Policy.expiry_date >= today,
                Policy.expiry_date <= today + timedelta(days=7),
                Policy.status.in_(["ACTIVE", "RENEWAL_PENDING"]),
            )
        )
        exp_15_res = await db.execute(
            select(func.count(Policy.id)).where(
                Policy.expiry_date >= today,
                Policy.expiry_date <= today + timedelta(days=15),
                Policy.status.in_(["ACTIVE", "RENEWAL_PENDING"]),
            )
        )
        exp_30_res = await db.execute(
            select(func.count(Policy.id)).where(
                Policy.expiry_date >= today,
                Policy.expiry_date <= today + timedelta(days=30),
                Policy.status.in_(["ACTIVE", "RENEWAL_PENDING"]),
            )
        )
        exp_60_res = await db.execute(
            select(func.count(Policy.id)).where(
                Policy.expiry_date >= today,
                Policy.expiry_date <= today + timedelta(days=60),
                Policy.status.in_(["ACTIVE", "RENEWAL_PENDING"]),
            )
        )

        expirations_window = ExpirationsByWindow(
            in_7_days=exp_7_res.scalar() or 0,
            in_15_days=exp_15_res.scalar() or 0,
            in_30_days=exp_30_res.scalar() or 0,
            in_60_days=exp_60_res.scalar() or 0,
        )

        # 4. Missing / Rejected / Expired Mandatory Documents
        missing_docs_res = await db.execute(
            select(func.count(PolicyDocument.id)).where(
                PolicyDocument.is_mandatory == True,
                PolicyDocument.status.in_(["PENDING_SUBMISSION", "REJECTED", "EXPIRED"]),
            )
        )
        missing_docs_count = missing_docs_res.scalar() or 0

        # 5. Premium Issues (Overdue, Grace Period, or Failed) & Total at Risk
        prem_stmt = select(PremiumSchedule).where(
            or_(
                PremiumSchedule.status.in_(["OVERDUE", "FAILED"]),
                (PremiumSchedule.due_date < today) & (PremiumSchedule.status != "PAID"),
                PremiumSchedule.retry_attempts > 0,
            )
        )
        prem_res = await db.execute(prem_stmt)
        prem_issues = prem_res.scalars().all()
        premium_issues_count = len(prem_issues)
        total_premium_at_risk = sum(p.amount_due for p in prem_issues)

        # 6. Customer Attention Items Aggregation
        att_stmt = select(CustomerAttentionItem).where(CustomerAttentionItem.is_active == True)
        att_res = await db.execute(att_stmt)
        active_items = att_res.scalars().all()

        customers_requiring_attention = len(set(i.customer_id for i in active_items))
        high_priority_cases = sum(1 for i in active_items if i.urgency_level in ["CRITICAL", "HIGH"])

        by_cat = {
            "POLICY_EXPIRY": 0,
            "MISSING_DOCS": 0,
            "PREMIUM_OVERDUE": 0,
            "RENEWAL_FOLLOWUP": 0,
            "RISK_ALERT": 0,
        }
        by_urgency = {
            "CRITICAL": 0,
            "HIGH": 0,
            "MEDIUM": 0,
            "LOW": 0,
        }
        by_status = {
            "OPEN": 0,
            "IN_PROGRESS": 0,
            "RESOLVED": 0,
            "DISMISSED": 0,
        }

        # Also get all items (including resolved) for status breakdown
        all_att_stmt = select(CustomerAttentionItem)
        all_att_res = await db.execute(all_att_stmt)
        all_att = all_att_res.scalars().all()

        for item in all_att:
            if item.status in by_status:
                by_status[item.status] += 1

        for item in active_items:
            if item.category in by_cat:
                by_cat[item.category] += 1
            if item.urgency_level in by_urgency:
                by_urgency[item.urgency_level] += 1

        return DashboardMetricsResponse(
            total_customers=total_cust,
            total_active_policies=total_active_policies,
            customers_requiring_attention=customers_requiring_attention,
            high_priority_cases=high_priority_cases,
            upcoming_policy_expirations=expirations_window,
            missing_documents_count=missing_docs_count,
            premium_issues_count=premium_issues_count,
            total_premium_at_risk=round(total_premium_at_risk, 2),
            attention_by_category=by_cat,
            attention_by_urgency=by_urgency,
            attention_by_status=by_status,
            vip_customers_count=vip_count,
            high_risk_customers_count=high_risk_count,
            timestamp=datetime.now(timezone.utc),
        )
