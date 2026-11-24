"""Premium Billing and Collections Business Service."""

from datetime import date, timedelta
from typing import Optional
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db.models import PremiumSchedule, Policy
from app.schemas.billing import PremiumIssueItem, PremiumIssuesSummaryResponse


class BillingService:
    @staticmethod
    async def get_premium_issues(
        db: AsyncSession,
        issue_type: Optional[str] = None,  # OVERDUE, GRACE_PERIOD, FAILED_DEBIT, UPCOMING
        customer_id: Optional[str] = None,
        skip: int = 0,
        limit: int = 50,
    ) -> PremiumIssuesSummaryResponse:
        """
        Retrieves premium billing issues and upcoming payments.
        - Identifies overdue payments.
        - Identifies payments currently inside grace period window.
        - Identifies failed auto-debits.
        - Calculates days overdue and remaining grace period days.
        - Applies customer_id and issue_type filters consistently to counts and items.
        """
        today = date.today()

        def _apply_issue_filter(query, target_issue_type: Optional[str]):
            if target_issue_type:
                it = target_issue_type.upper()
                if it == "OVERDUE":
                    return query.where(
                        PremiumSchedule.status.in_(["OVERDUE", "FAILED"]),
                        PremiumSchedule.due_date < today,
                    )
                elif it == "GRACE_PERIOD":
                    return query.where(
                        PremiumSchedule.due_date < today,
                        PremiumSchedule.grace_period_end >= today,
                        PremiumSchedule.status != "PAID",
                    )
                elif it == "FAILED_DEBIT":
                    return query.where(
                        or_(
                            PremiumSchedule.status == "FAILED",
                            PremiumSchedule.retry_attempts > 0,
                        ),
                        PremiumSchedule.status != "PAID",
                    )
                elif it == "UPCOMING":
                    in_30d = today + timedelta(days=30)
                    return query.where(
                        PremiumSchedule.due_date >= today,
                        PremiumSchedule.due_date <= in_30d,
                        PremiumSchedule.status == "PENDING",
                    )
            return query.where(
                or_(
                    PremiumSchedule.status.in_(["OVERDUE", "FAILED"]),
                    (PremiumSchedule.due_date < today) & (PremiumSchedule.status != "PAID"),
                    (PremiumSchedule.retry_attempts > 0) & (PremiumSchedule.status != "PAID"),
                )
            )

        stmt = select(PremiumSchedule).options(
            selectinload(PremiumSchedule.policy).selectinload(Policy.customer)
        )
        stmt = _apply_issue_filter(stmt, issue_type)

        summary_query = select(PremiumSchedule)
        summary_query = _apply_issue_filter(summary_query, issue_type)

        if customer_id:
            stmt = stmt.join(PremiumSchedule.policy).where(Policy.customer_id == customer_id)
            summary_query = summary_query.join(PremiumSchedule.policy).where(Policy.customer_id == customer_id)

        all_res = await db.execute(summary_query)
        matching_schedules = all_res.scalars().all()

        total_matching = len(matching_schedules)
        in_grace = 0
        overdue_cnt = 0
        failed_debit = 0
        total_risk_amt = 0.0

        for s in matching_schedules:
            if s.status != "PAID":
                if s.due_date < today <= s.grace_period_end:
                    in_grace += 1
                if s.status in ["OVERDUE", "FAILED"] or s.due_date < today:
                    overdue_cnt += 1
                    total_risk_amt += s.amount_due
                elif issue_type and issue_type.upper() == "UPCOMING":
                    total_risk_amt += s.amount_due
                if s.retry_attempts > 0 or s.status == "FAILED":
                    failed_debit += 1

        # Fetch paginated results
        stmt = stmt.order_by(PremiumSchedule.due_date.asc()).offset(skip).limit(limit)
        res = await db.execute(stmt)
        schedules = res.scalars().all()

        items = []
        for s in schedules:
            p = s.policy
            c = p.customer if p else None

            days_overdue = max(0, (today - s.due_date).days)
            days_grace_remaining = max(0, (s.grace_period_end - today).days)
            is_in_grace = s.due_date < today <= s.grace_period_end

            if s.retry_attempts > 0 or s.status == "FAILED":
                classified_issue = "FAILED_DEBIT"
            elif is_in_grace:
                classified_issue = "GRACE_PERIOD"
            elif s.due_date < today:
                classified_issue = "OVERDUE"
            else:
                classified_issue = "UPCOMING_DUE"

            items.append(
                PremiumIssueItem(
                    schedule_id=s.id,
                    installment_number=s.installment_number,
                    amount_due=s.amount_due,
                    due_date=s.due_date,
                    grace_period_end=s.grace_period_end,
                    status=s.status,
                    payment_method=s.payment_method,
                    retry_attempts=s.retry_attempts,
                    failure_reason=s.failure_reason,
                    issue_type=classified_issue,
                    days_overdue=days_overdue,
                    days_grace_remaining=days_grace_remaining,
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

        return PremiumIssuesSummaryResponse(
            total_issues=total_matching,
            in_grace_period_count=in_grace,
            overdue_count=overdue_cnt,
            failed_auto_debit_count=failed_debit,
            total_amount_at_risk=round(total_risk_amt, 2),
            items=items,
        )
