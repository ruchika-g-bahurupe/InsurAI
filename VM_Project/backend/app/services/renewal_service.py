"""Renewal Pipeline and Follow-up Business Service."""

from datetime import date, timedelta
from typing import List, Optional
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db.models import Policy, Customer, CustomerAttentionItem
from app.schemas.renewal import RenewalFollowUpItem, RenewalFollowUpSummary


class RenewalService:
    @staticmethod
    async def get_renewal_follow_ups(
        db: AsyncSession,
        within_days: int = 60,
        only_unactioned: bool = False,
        skip: int = 0,
        limit: int = 50,
    ) -> RenewalFollowUpSummary:
        """
        Identifies policies in the renewal window:
        - Upcoming expiry within N days (default: 60 days).
        - Excludes already expired policies.
        - Checks existing active attention items to avoid duplicate recommendations.
        - Determines follow-up priority based on customer tier, CLV, and renewal probability.
        """
        today = date.today()
        target_cutoff = today + timedelta(days=within_days)

        # 1. Fetch upcoming expiring policies
        stmt = (
            select(Policy)
            .options(
                selectinload(Policy.customer),
                selectinload(Policy.attention_items),
            )
            .where(
                Policy.expiry_date >= today,
                Policy.expiry_date <= target_cutoff,
                Policy.status.in_(["ACTIVE", "RENEWAL_PENDING"]),
            )
            .order_by(Policy.expiry_date.asc())
        )

        res = await db.execute(stmt)
        all_policies = res.scalars().all()

        items: List[RenewalFollowUpItem] = []
        critical_count = 0
        high_count = 0
        medium_count = 0
        already_actioned = 0
        total_pipeline_prem = 0.0

        for p in all_policies:
            c = p.customer
            total_pipeline_prem += p.premium_amount

            # Check if there is an active renewal attention item for this policy (deduplication check)
            active_renewal_att = next(
                (
                    att
                    for att in p.attention_items
                    if att.is_active and att.category in ["RENEWAL_FOLLOWUP", "POLICY_EXPIRY"]
                ),
                None,
            )

            has_active = active_renewal_att is not None
            att_id = active_renewal_att.id if active_renewal_att else None

            if has_active:
                already_actioned += 1
                if only_unactioned:
                    continue

            days_left = (p.expiry_date - today).days

            # Determine follow-up priority:
            # VIPs or low renewal probability or expiring within 15 days get higher urgency
            if days_left <= 10 or (c and c.tier in ["VIP", "HIGH_NET_WORTH"] and days_left <= 30):
                priority = "CRITICAL"
                critical_count += 1
                rec_action = "Schedule immediate executive call and lock in renewal rate."
            elif days_left <= 30 or p.renewal_probability < 0.60:
                priority = "HIGH"
                high_count += 1
                rec_action = "Send personalized renewal notice with loyalty incentive."
            else:
                priority = "MEDIUM"
                medium_count += 1
                rec_action = "Dispatch automated email renewal reminder."

            items.append(
                RenewalFollowUpItem(
                    policy_id=p.id,
                    policy_number=p.policy_number,
                    policy_type=p.policy_type,
                    plan_name=p.plan_name,
                    premium_amount=p.premium_amount,
                    expiry_date=p.expiry_date,
                    days_to_expiry=days_left,
                    renewal_probability=p.renewal_probability,
                    auto_renew=p.auto_renew,
                    policy_status=p.status,
                    customer_id=c.id if c else "UNKNOWN",
                    customer_name=c.full_name if c else "Unknown Customer",
                    customer_code=c.customer_code if c else "N/A",
                    customer_tier=c.tier if c else "STANDARD",
                    customer_clv=c.total_clv if c else 0.0,
                    assigned_agent=c.assigned_agent if c else "Unassigned",
                    has_active_attention_item=has_active,
                    attention_item_id=att_id,
                    follow_up_priority=priority,
                    recommended_action=rec_action,
                )
            )

        # Apply pagination on processed list
        paginated_items = items[skip : skip + limit]

        return RenewalFollowUpSummary(
            total_in_window=len(items),
            critical_followups=critical_count,
            high_followups=high_count,
            medium_followups=medium_count,
            already_actioned_count=already_actioned,
            total_premium_in_pipeline=round(total_pipeline_prem, 2),
            items=paginated_items,
        )
