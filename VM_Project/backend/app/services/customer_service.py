"""Customer Directory and 360° Profile Business Service."""

from typing import Any, Dict, List, Optional
from fastapi import HTTPException
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.db.models import Customer, Policy, CustomerAttentionItem
from app.schemas.customer import CustomerSummary


class CustomerService:
    @staticmethod
    async def list_customers(
        db: AsyncSession,
        search: Optional[str] = None,
        tier: Optional[str] = None,
        risk_segment: Optional[str] = None,
        status: Optional[str] = "ACTIVE",
        skip: int = 0,
        limit: int = 50,
    ) -> List[CustomerSummary]:
        """Paginated customer directory with active policies and open attention counts."""
        query = select(
            Customer,
            func.count(func.distinct(Policy.id)).filter(Policy.status == "ACTIVE").label("active_policies_count"),
            func.count(func.distinct(CustomerAttentionItem.id)).filter(CustomerAttentionItem.is_active == True).label("open_attention_count"),
        ).outerjoin(Customer.policies).outerjoin(Customer.attention_items).group_by(Customer.id)

        if status and status != "ALL":
            query = query.where(Customer.status == status.upper())

        if tier:
            query = query.where(Customer.tier == tier.upper())

        if risk_segment:
            query = query.where(Customer.risk_segment == risk_segment.upper())

        if search:
            s = f"%{search.strip()}%"
            query = query.where(
                or_(
                    Customer.first_name.ilike(s),
                    Customer.last_name.ilike(s),
                    Customer.customer_code.ilike(s),
                    Customer.email.ilike(s),
                    Customer.city.ilike(s),
                )
            )

        query = query.order_by(Customer.total_clv.desc()).offset(skip).limit(limit)
        result = await db.execute(query)
        rows = result.all()

        return [
            CustomerSummary(
                id=cust.id,
                customer_code=cust.customer_code,
                full_name=cust.full_name,
                email=cust.email,
                phone=cust.phone,
                tier=cust.tier,
                risk_segment=cust.risk_segment,
                total_clv=cust.total_clv,
                status=cust.status,
                active_policies_count=pol_count,
                open_attention_count=att_count,
            )
            for cust, pol_count, att_count in rows
        ]

    @staticmethod
    async def get_customer_360(db: AsyncSession, customer_id: str) -> Dict[str, Any]:
        """
        Complete 360° customer profile including:
        - Demographics & segmentation
        - All active and historical policies with premium schedules
        - Full compliance document vault
        - Claims history & loss details
        - Customer attention items & recommendation states
        - Activity audit trail
        """
        stmt = (
            select(Customer)
            .options(
                selectinload(Customer.policies).selectinload(Policy.premium_schedules),
                selectinload(Customer.policies).selectinload(Policy.documents),
                selectinload(Customer.documents),
                selectinload(Customer.claims),
                selectinload(Customer.attention_items),
                selectinload(Customer.audit_logs),
            )
            .where(or_(Customer.id == customer_id, Customer.customer_code == customer_id))
        )
        res = await db.execute(stmt)
        customer = res.scalars().first()

        if not customer:
            raise HTTPException(status_code=404, detail="Customer not found.")

        return {
            "id": customer.id,
            "customer_code": customer.customer_code,
            "first_name": customer.first_name,
            "last_name": customer.last_name,
            "full_name": customer.full_name,
            "email": customer.email,
            "phone": customer.phone,
            "date_of_birth": customer.date_of_birth,
            "tier": customer.tier,
            "risk_segment": customer.risk_segment,
            "total_clv": customer.total_clv,
            "assigned_agent": customer.assigned_agent,
            "city": customer.city,
            "state": customer.state,
            "status": customer.status,
            "created_at": customer.created_at,
            "policies": [
                {
                    "id": p.id,
                    "policy_number": p.policy_number,
                    "policy_type": p.policy_type,
                    "plan_name": p.plan_name,
                    "sum_insured": p.sum_insured,
                    "premium_amount": p.premium_amount,
                    "payment_frequency": p.payment_frequency,
                    "start_date": p.start_date,
                    "expiry_date": p.expiry_date,
                    "status": p.status,
                    "auto_renew": p.auto_renew,
                    "renewal_probability": p.renewal_probability,
                    "schedules": [
                        {
                            "id": s.id,
                            "installment_number": s.installment_number,
                            "amount_due": s.amount_due,
                            "due_date": s.due_date,
                            "grace_period_end": s.grace_period_end,
                            "status": s.status,
                            "payment_method": s.payment_method,
                            "paid_at": s.paid_at,
                            "retry_attempts": s.retry_attempts,
                            "failure_reason": s.failure_reason,
                        }
                        for s in p.premium_schedules
                    ],
                }
                for p in customer.policies
            ],
            "documents": [
                {
                    "id": d.id,
                    "policy_id": d.policy_id,
                    "document_type": d.document_type,
                    "document_name": d.document_name,
                    "status": d.status,
                    "is_mandatory": d.is_mandatory,
                    "rejection_reason": d.rejection_reason,
                    "expiry_date": d.expiry_date,
                    "submitted_at": d.submitted_at,
                    "verified_at": d.verified_at,
                }
                for d in customer.documents
            ],
            "claims": [
                {
                    "id": c.id,
                    "policy_id": c.policy_id,
                    "claim_number": c.claim_number,
                    "claim_amount": c.claim_amount,
                    "payout_amount": c.payout_amount,
                    "status": c.status,
                    "incident_date": c.incident_date,
                    "description": c.description,
                    "adjuster_notes": c.adjuster_notes,
                }
                for c in customer.claims
            ],
            "attention_items": [
                {
                    "id": a.id,
                    "policy_id": a.policy_id,
                    "category": a.category,
                    "urgency_level": a.urgency_level,
                    "attention_score": a.attention_score,
                    "title": a.title,
                    "root_cause": a.root_cause,
                    "ai_summary": a.ai_summary,
                    "ai_recommendation": a.ai_recommendation,
                    "suggested_action": a.suggested_action,
                    "status": a.status,
                    "is_active": a.is_active,
                    "assigned_to": a.assigned_to,
                    "detected_at": a.detected_at,
                    "resolved_at": a.resolved_at,
                    "resolution_notes": a.resolution_notes,
                }
                for a in customer.attention_items
            ],
            "audit_logs": [
                {
                    "id": al.id,
                    "action_type": al.action_type,
                    "actor": al.actor,
                    "actor_name": al.actor_name,
                    "description": al.description,
                    "created_at": al.created_at,
                }
                for al in customer.audit_logs
            ],
        }
