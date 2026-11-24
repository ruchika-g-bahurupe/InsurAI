"""Customer Attention Items Business Service."""

from datetime import datetime, timezone
from typing import List, Optional
from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db.models import CustomerAttentionItem, Policy, ActivityAuditLog
from app.schemas.attention import (
    CustomerAttentionItemResponse,
    AttentionItemDetailResponse,
    AttentionAuditEntry,
    AttentionOverviewMetrics,
)


def _map_attention_response(item: CustomerAttentionItem) -> CustomerAttentionItemResponse:
    return CustomerAttentionItemResponse(
        id=item.id,
        customer_id=item.customer_id,
        policy_id=item.policy_id,
        category=item.category,
        urgency_level=item.urgency_level,
        attention_score=item.attention_score,
        confidence_level=item.confidence_level,
        dedup_key=item.dedup_key,
        is_active=item.is_active,
        title=item.title,
        reasoning_summary=item.reasoning_summary,
        root_cause=item.root_cause,
        ai_summary=item.ai_summary,
        ai_recommendation=item.ai_recommendation,
        identified_risk_factors=item.identified_risk_factors,
        investigation_steps=item.investigation_steps,
        supporting_evidence=item.supporting_evidence,
        data_gaps=item.data_gaps,
        suggested_action=item.suggested_action,
        status=item.status,
        assigned_to=item.assigned_to,
        detected_at=item.detected_at,
        resolved_at=item.resolved_at,
        resolved_by=item.resolved_by,
        resolution_notes=item.resolution_notes,
        customer_name=item.customer.full_name if item.customer else None,
        customer_code=item.customer.customer_code if item.customer else None,
        customer_tier=item.customer.tier if item.customer else None,
        customer_email=item.customer.email if item.customer else None,
        customer_phone=item.customer.phone if item.customer else None,
        policy_number=item.policy.policy_number if item.policy else None,
        policy_type=item.policy.policy_type if item.policy else None,
    )


class AttentionService:
    @staticmethod
    async def get_attention_items(
        db: AsyncSession,
        category: Optional[str] = None,
        urgency_level: Optional[str] = None,
        status: Optional[str] = None,
        customer_id: Optional[str] = None,
        sort_by: str = "attention_score",
        order: str = "desc",
        skip: int = 0,
        limit: int = 50,
    ) -> List[CustomerAttentionItemResponse]:
        """Query attention items with filtering, sorting, and customer/policy context."""
        stmt = (
            select(CustomerAttentionItem)
            .options(
                selectinload(CustomerAttentionItem.customer),
                selectinload(CustomerAttentionItem.policy),
            )
        )

        if customer_id:
            stmt = stmt.where(CustomerAttentionItem.customer_id == customer_id)

        if category:
            stmt = stmt.where(CustomerAttentionItem.category == category.upper())

        if urgency_level:
            stmt = stmt.where(CustomerAttentionItem.urgency_level == urgency_level.upper())

        if status:
            if status.upper() == "ACTIVE":
                stmt = stmt.where(CustomerAttentionItem.is_active == True)
            else:
                stmt = stmt.where(CustomerAttentionItem.status == status.upper())
        else:
            stmt = stmt.where(CustomerAttentionItem.is_active == True)

        sort_column = getattr(CustomerAttentionItem, sort_by, CustomerAttentionItem.attention_score)
        if order.lower() == "asc":
            stmt = stmt.order_by(sort_column.asc())
        else:
            stmt = stmt.order_by(sort_column.desc())

        stmt = stmt.offset(skip).limit(limit)
        res = await db.execute(stmt)
        items = res.scalars().all()

        return [_map_attention_response(item) for item in items]

    @staticmethod
    async def get_attention_item_detail(
        db: AsyncSession, attention_id: str
    ) -> AttentionItemDetailResponse:
        """Fetch complete deep detail of an attention item with customer, policy, and audit trail."""
        stmt = (
            select(CustomerAttentionItem)
            .options(
                selectinload(CustomerAttentionItem.customer),
                selectinload(CustomerAttentionItem.policy),
            )
            .where(CustomerAttentionItem.id == attention_id)
        )
        res = await db.execute(stmt)
        item = res.scalars().first()

        if not item:
            raise HTTPException(status_code=404, detail="Attention item not found.")

        audit_stmt = (
            select(ActivityAuditLog)
            .where(ActivityAuditLog.customer_id == item.customer_id)
            .order_by(ActivityAuditLog.created_at.desc())
            .limit(10)
        )
        audit_res = await db.execute(audit_stmt)
        audit_records = audit_res.scalars().all()

        customer_details = None
        if item.customer:
            c = item.customer
            customer_details = {
                "id": c.id,
                "customer_code": c.customer_code,
                "full_name": c.full_name,
                "email": c.email,
                "phone": c.phone,
                "tier": c.tier,
                "risk_segment": c.risk_segment,
                "total_clv": c.total_clv,
                "assigned_agent": c.assigned_agent,
                "city": c.city,
                "state": c.state,
                "status": c.status,
            }

        policy_details = None
        if item.policy:
            p = item.policy
            policy_details = {
                "id": p.id,
                "policy_number": p.policy_number,
                "policy_type": p.policy_type,
                "plan_name": p.plan_name,
                "sum_insured": p.sum_insured,
                "premium_amount": p.premium_amount,
                "start_date": p.start_date.isoformat(),
                "expiry_date": p.expiry_date.isoformat(),
                "status": p.status,
                "auto_renew": p.auto_renew,
                "renewal_probability": p.renewal_probability,
            }

        audit_history = [
            AttentionAuditEntry(
                id=a.id,
                action_type=a.action_type,
                actor=a.actor,
                actor_name=a.actor_name,
                description=a.description,
                created_at=a.created_at,
            )
            for a in audit_records
        ]

        base_resp = _map_attention_response(item)
        return AttentionItemDetailResponse(
            **base_resp.model_dump(),
            customer_details=customer_details,
            policy_details=policy_details,
            audit_history=audit_history,
        )

    @staticmethod
    async def update_attention_status(
        db: AsyncSession,
        attention_id: str,
        status: str,
        assigned_to: Optional[str] = None,
        resolved_by: Optional[str] = None,
        resolution_notes: Optional[str] = None,
    ) -> CustomerAttentionItemResponse:
        """Update lifecycle status and write an employee action audit entry."""
        stmt = (
            select(CustomerAttentionItem)
            .options(
                selectinload(CustomerAttentionItem.customer),
                selectinload(CustomerAttentionItem.policy),
            )
            .where(CustomerAttentionItem.id == attention_id)
        )
        res = await db.execute(stmt)
        item = res.scalars().first()

        if not item:
            raise HTTPException(status_code=404, detail="Attention item not found.")

        valid_statuses = {"OPEN", "IN_PROGRESS", "RESOLVED", "DISMISSED"}
        new_status = status.upper()
        if new_status not in valid_statuses:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}. Must be one of {valid_statuses}")

        old_status = item.status
        item.status = new_status
        if assigned_to is not None:
            item.assigned_to = assigned_to

        now_utc = datetime.now(timezone.utc)
        actor_name = resolved_by or assigned_to or "Assigned Employee"

        if new_status in {"RESOLVED", "DISMISSED"}:
            item.is_active = False
            item.resolved_at = now_utc
            item.resolved_by = actor_name
            item.resolution_notes = resolution_notes or f"Marked as {new_status}."
        else:
            item.is_active = True
            item.resolved_at = None

        audit = ActivityAuditLog(
            customer_id=item.customer_id,
            action_type=f"RECOMMENDATION_{new_status}",
            actor="EMPLOYEE",
            actor_name=actor_name,
            description=(
                f"Attention Item '{item.title}' transition: {old_status} -> {new_status}. "
                f"Notes: {resolution_notes or 'Status updated by user.'}"
            ),
            metadata_payload={
                "attention_id": item.id,
                "previous_status": old_status,
                "new_status": new_status,
                "category": item.category,
                "dedup_key": item.dedup_key,
            },
        )
        db.add(audit)

        await db.commit()
        await db.refresh(item)

        return _map_attention_response(item)

    @staticmethod
    async def get_attention_overview(db: AsyncSession) -> AttentionOverviewMetrics:
        """Calculate active attention distribution and total premium at risk."""
        active_items_stmt = select(CustomerAttentionItem).where(CustomerAttentionItem.is_active == True)
        res = await db.execute(active_items_stmt)
        active_items = res.scalars().all()

        total_active = len(active_items)
        critical_count = sum(1 for i in active_items if i.urgency_level == "CRITICAL")
        high_count = sum(1 for i in active_items if i.urgency_level == "HIGH")
        medium_count = sum(1 for i in active_items if i.urgency_level == "MEDIUM")
        low_count = sum(1 for i in active_items if i.urgency_level == "LOW")

        cat_counts = {
            "POLICY_EXPIRY": 0,
            "MISSING_DOCS": 0,
            "PREMIUM_OVERDUE": 0,
            "RENEWAL_FOLLOWUP": 0,
            "RISK_ALERT": 0,
        }
        for item in active_items:
            if item.category in cat_counts:
                cat_counts[item.category] += 1

        policy_ids = [i.policy_id for i in active_items if i.policy_id]
        total_prem_at_risk = 0.0
        if policy_ids:
            prem_stmt = select(func.sum(Policy.premium_amount)).where(Policy.id.in_(policy_ids))
            prem_res = await db.execute(prem_stmt)
            total_prem_at_risk = prem_res.scalar() or 0.0

        return AttentionOverviewMetrics(
            total_active_alerts=total_active,
            critical_alerts=critical_count,
            high_alerts=high_count,
            medium_alerts=medium_count,
            low_alerts=low_count,
            policy_expiry_count=cat_counts["POLICY_EXPIRY"],
            missing_docs_count=cat_counts["MISSING_DOCS"],
            premium_issues_count=cat_counts["PREMIUM_OVERDUE"],
            renewal_followup_count=cat_counts["RENEWAL_FOLLOWUP"],
            risk_alert_count=cat_counts["RISK_ALERT"],
            total_premium_at_risk=round(total_prem_at_risk, 2),
        )
