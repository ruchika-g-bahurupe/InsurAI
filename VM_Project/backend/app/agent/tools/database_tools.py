"""Reusable Python Database Tools for the Unified AI Intelligence Core.

Each tool executes controlled, structured database retrieval queries via SQLAlchemy
and reuses the core Phase 2 services. No arbitrary SQL execution is allowed.
"""

from datetime import date, datetime, timedelta, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import func, or_, select
from sqlalchemy.orm import selectinload
from app.core.database import SyncSessionLocal
from app.core.logging import logger
from app.db.models import (
    Customer,
    Policy,
    PolicyDocument,
    PremiumSchedule,
    Claim,
    CustomerAttentionItem,
    ActivityAuditLog,
)


def search_customer_records(
    query: str,
    tier: Optional[str] = None,
    risk_segment: Optional[str] = None,
    limit: int = 10,
) -> Dict[str, Any]:
    """Search customers by name, customer code, email, phone, or city.
    
    Args:
        query: Search term for customer name, code (e.g. CUST-1005), or email.
        tier: Optional filter by customer tier (STANDARD, VIP, HIGH_NET_WORTH).
        risk_segment: Optional filter by risk classification (LOW, MEDIUM, HIGH).
        limit: Maximum records to return (default: 10).
    """
    session = SyncSessionLocal()
    try:
        stmt = select(Customer)
        if query:
            s = f"%{query.strip()}%"
            stmt = stmt.where(
                or_(
                    Customer.first_name.ilike(s),
                    Customer.last_name.ilike(s),
                    Customer.customer_code.ilike(s),
                    Customer.email.ilike(s),
                    Customer.city.ilike(s),
                )
            )
        if tier:
            stmt = stmt.where(Customer.tier == tier.upper())
        if risk_segment:
            stmt = stmt.where(Customer.risk_segment == risk_segment.upper())

        stmt = stmt.order_by(Customer.total_clv.desc()).limit(limit)
        customers = session.execute(stmt).scalars().all()

        results = []
        for c in customers:
            results.append({
                "id": c.id,
                "customer_code": c.customer_code,
                "full_name": c.full_name,
                "email": c.email,
                "phone": c.phone,
                "tier": c.tier,
                "risk_segment": c.risk_segment,
                "total_clv": c.total_clv,
                "city": c.city,
                "state": c.state,
                "assigned_agent": c.assigned_agent,
            })
        return {"total_found": len(results), "customers": results}
    except Exception as e:
        logger.error(f"search_customer_records error: {e}")
        return {"error": str(e), "customers": []}
    finally:
        session.close()


def get_customer_360_profile(customer_id_or_code: str) -> Dict[str, Any]:
    """Retrieve full 360-degree customer profile with all policies, schedules, documents, claims, and attention items.
    
    Args:
        customer_id_or_code: The UUID or Customer Code (e.g., CUST-1005).
    """
    session = SyncSessionLocal()
    try:
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
            .where(
                or_(
                    Customer.id == customer_id_or_code,
                    Customer.customer_code == customer_id_or_code.upper(),
                )
            )
        )
        c = session.execute(stmt).scalars().first()
        if not c:
            return {"error": f"Customer not found for identifier '{customer_id_or_code}'"}

        today = date.today()
        policies_data = []
        for p in c.policies:
            policies_data.append({
                "policy_id": p.id,
                "policy_number": p.policy_number,
                "policy_type": p.policy_type,
                "plan_name": p.plan_name,
                "sum_insured": p.sum_insured,
                "premium_amount": p.premium_amount,
                "expiry_date": p.expiry_date.isoformat(),
                "days_to_expiry": (p.expiry_date - today).days,
                "status": p.status,
                "auto_renew": p.auto_renew,
                "renewal_probability": p.renewal_probability,
            })

        documents_data = [
            {
                "document_id": d.id,
                "document_type": d.document_type,
                "document_name": d.document_name,
                "status": d.status,
                "is_mandatory": d.is_mandatory,
                "rejection_reason": d.rejection_reason,
            }
            for d in c.documents
        ]

        claims_data = [
            {
                "claim_id": cl.id,
                "claim_number": cl.claim_number,
                "amount": cl.claim_amount,
                "status": cl.status,
                "incident_date": cl.incident_date.isoformat(),
                "description": cl.description,
            }
            for cl in c.claims
        ]

        attention_data = [
            {
                "item_id": a.id,
                "category": a.category,
                "urgency_level": a.urgency_level,
                "score": a.attention_score,
                "title": a.title,
                "root_cause": a.root_cause,
                "status": a.status,
                "is_active": a.is_active,
            }
            for a in c.attention_items
        ]

        return {
            "customer_id": c.id,
            "customer_code": c.customer_code,
            "full_name": c.full_name,
            "email": c.email,
            "phone": c.phone,
            "tier": c.tier,
            "risk_segment": c.risk_segment,
            "total_clv": c.total_clv,
            "city": c.city,
            "state": c.state,
            "assigned_agent": c.assigned_agent,
            "policies": policies_data,
            "documents": documents_data,
            "claims": claims_data,
            "active_attention_items": [i for i in attention_data if i["is_active"]],
        }
    except Exception as e:
        logger.error(f"get_customer_360_profile error: {e}")
        return {"error": str(e)}
    finally:
        session.close()


def get_policy_compliance_status(policy_id_or_number: str) -> Dict[str, Any]:
    """Retrieve compliance document checklist for a policy, identifying verified vs missing/rejected documents.
    
    Args:
        policy_id_or_number: UUID or Policy Number (e.g. POL-LIF-2025).
    """
    session = SyncSessionLocal()
    try:
        stmt = (
            select(Policy)
            .options(
                selectinload(Policy.documents),
                selectinload(Policy.customer),
            )
            .where(
                or_(
                    Policy.id == policy_id_or_number,
                    Policy.policy_number == policy_id_or_number.upper(),
                )
            )
        )
        p = session.execute(stmt).scalars().first()
        if not p:
            return {"error": f"Policy not found for identifier '{policy_id_or_number}'"}

        docs = []
        has_deficit = False
        for d in p.documents:
            is_compliant = d.status == "VERIFIED"
            if not is_compliant and d.is_mandatory:
                has_deficit = True
            docs.append({
                "document_id": d.id,
                "document_type": d.document_type,
                "document_name": d.document_name,
                "status": d.status,
                "is_mandatory": d.is_mandatory,
                "is_compliant": is_compliant,
                "rejection_reason": d.rejection_reason,
            })

        return {
            "policy_number": p.policy_number,
            "policy_type": p.policy_type,
            "customer_name": p.customer.full_name if p.customer else "N/A",
            "is_fully_compliant": not has_deficit,
            "documents": docs,
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        session.close()


def get_premium_payment_history(policy_id_or_number: str) -> Dict[str, Any]:
    """Retrieve premium payment schedules, overdue invoices, and grace period details for a policy.
    
    Args:
        policy_id_or_number: Policy UUID or policy number (e.g., POL-AUT-2012).
    """
    session = SyncSessionLocal()
    try:
        stmt = (
            select(Policy)
            .options(
                selectinload(Policy.premium_schedules),
                selectinload(Policy.customer),
            )
            .where(
                or_(
                    Policy.id == policy_id_or_number,
                    Policy.policy_number == policy_id_or_number.upper(),
                )
            )
        )
        p = session.execute(stmt).scalars().first()
        if not p:
            return {"error": f"Policy not found for identifier '{policy_id_or_number}'"}

        today = date.today()
        schedules = []
        total_overdue = 0.0

        for s in p.premium_schedules:
            is_overdue = s.due_date < today and s.status in ["OVERDUE", "FAILED", "PENDING"]
            if is_overdue:
                total_overdue += s.amount_due
            schedules.append({
                "installment_number": s.installment_number,
                "amount_due": s.amount_due,
                "due_date": s.due_date.isoformat(),
                "grace_period_end": s.grace_period_end.isoformat(),
                "status": s.status,
                "is_overdue": is_overdue,
                "days_overdue": max(0, (today - s.due_date).days),
                "retry_attempts": s.retry_attempts,
                "failure_reason": s.failure_reason,
            })

        return {
            "policy_number": p.policy_number,
            "customer_name": p.customer.full_name if p.customer else "N/A",
            "premium_amount": p.premium_amount,
            "total_overdue_amount": total_overdue,
            "schedules": schedules,
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        session.close()


def get_active_attention_items(
    category: Optional[str] = None,
    urgency_level: Optional[str] = None,
    limit: int = 10,
) -> Dict[str, Any]:
    """List prioritized unresolved attention alerts flagged by the Watchdog.
    
    Args:
        category: POLICY_EXPIRY, MISSING_DOCS, PREMIUM_OVERDUE, RENEWAL_FOLLOWUP, RISK_ALERT.
        urgency_level: CRITICAL, HIGH, MEDIUM, LOW.
        limit: Max items to return.
    """
    session = SyncSessionLocal()
    try:
        stmt = (
            select(CustomerAttentionItem)
            .options(
                selectinload(CustomerAttentionItem.customer),
                selectinload(CustomerAttentionItem.policy),
            )
            .where(CustomerAttentionItem.is_active == True)
        )
        if category:
            stmt = stmt.where(CustomerAttentionItem.category == category.upper())
        if urgency_level:
            stmt = stmt.where(CustomerAttentionItem.urgency_level == urgency_level.upper())

        stmt = stmt.order_by(CustomerAttentionItem.attention_score.desc()).limit(limit)
        items = session.execute(stmt).scalars().all()

        results = []
        for i in items:
            results.append({
                "attention_id": i.id,
                "customer_name": i.customer.full_name if i.customer else "N/A",
                "customer_code": i.customer.customer_code if i.customer else "N/A",
                "customer_tier": i.customer.tier if i.customer else "STANDARD",
                "policy_number": i.policy.policy_number if i.policy else "N/A",
                "category": i.category,
                "urgency_level": i.urgency_level,
                "attention_score": i.attention_score,
                "title": i.title,
                "root_cause": i.root_cause,
                "ai_recommendation": i.ai_recommendation,
                "status": i.status,
            })

        return {"total_alerts": len(results), "alerts": results}
    except Exception as e:
        return {"error": str(e), "alerts": []}
    finally:
        session.close()


def get_expiring_policies(within_days: int = 15, limit: int = 10) -> Dict[str, Any]:
    """Retrieve policies expiring within a given window of days (e.g. 7, 15, 30 days).
    
    Args:
        within_days: Horizon window in days (default: 15).
        limit: Max policies to return.
    """
    session = SyncSessionLocal()
    try:
        today = date.today()
        target = today + timedelta(days=within_days)
        stmt = (
            select(Policy)
            .options(selectinload(Policy.customer))
            .where(
                Policy.expiry_date >= today,
                Policy.expiry_date <= target,
                Policy.status.in_(["ACTIVE", "RENEWAL_PENDING"]),
            )
            .order_by(Policy.expiry_date.asc())
            .limit(limit)
        )
        policies = session.execute(stmt).scalars().all()

        results = []
        for p in policies:
            c = p.customer
            results.append({
                "policy_number": p.policy_number,
                "policy_type": p.policy_type,
                "plan_name": p.plan_name,
                "premium_amount": p.premium_amount,
                "expiry_date": p.expiry_date.isoformat(),
                "days_remaining": (p.expiry_date - today).days,
                "customer_name": c.full_name if c else "N/A",
                "customer_code": c.customer_code if c else "N/A",
                "customer_tier": c.tier if c else "STANDARD",
                "renewal_probability": p.renewal_probability,
            })
        return {"window_days": within_days, "total": len(results), "policies": results}
    except Exception as e:
        return {"error": str(e), "policies": []}
    finally:
        session.close()


def get_missing_documents(status: Optional[str] = None, limit: int = 10) -> Dict[str, Any]:
    """Retrieve customers with missing, pending, or rejected mandatory compliance documents.
    
    Args:
        status: PENDING_SUBMISSION, REJECTED, EXPIRED (optional filter).
        limit: Max records to return.
    """
    session = SyncSessionLocal()
    try:
        deficit_statuses = ["PENDING_SUBMISSION", "REJECTED", "EXPIRED"]
        stmt = (
            select(PolicyDocument)
            .options(
                selectinload(PolicyDocument.policy),
                selectinload(PolicyDocument.customer),
            )
            .where(
                PolicyDocument.is_mandatory == True,
                PolicyDocument.status.in_([status.upper()] if status else deficit_statuses),
            )
            .order_by(PolicyDocument.created_at.desc())
            .limit(limit)
        )
        docs = session.execute(stmt).scalars().all()

        results = []
        for d in docs:
            results.append({
                "document_type": d.document_type,
                "document_name": d.document_name,
                "status": d.status,
                "rejection_reason": d.rejection_reason,
                "policy_number": d.policy.policy_number if d.policy else "N/A",
                "customer_name": d.customer.full_name if d.customer else "N/A",
                "customer_code": d.customer.customer_code if d.customer else "N/A",
            })
        return {"total_deficits": len(results), "documents": results}
    except Exception as e:
        return {"error": str(e), "documents": []}
    finally:
        session.close()


def get_customer_followup_history(customer_id_or_code: str) -> Dict[str, Any]:
    """Retrieve historical follow-up touches, outreach logs, and employee actions for a customer.
    
    Args:
        customer_id_or_code: Customer UUID or code (e.g. CUST-1005).
    """
    session = SyncSessionLocal()
    try:
        cust_stmt = select(Customer).where(
            or_(
                Customer.id == customer_id_or_code,
                Customer.customer_code == customer_id_or_code.upper(),
            )
        )
        c = session.execute(cust_stmt).scalars().first()
        if not c:
            return {"error": f"Customer not found for '{customer_id_or_code}'"}

        audit_stmt = (
            select(ActivityAuditLog)
            .where(ActivityAuditLog.customer_id == c.id)
            .order_by(ActivityAuditLog.created_at.desc())
            .limit(15)
        )
        logs = session.execute(audit_stmt).scalars().all()

        history = []
        for log in logs:
            history.append({
                "action_type": log.action_type,
                "actor": log.actor,
                "actor_name": log.actor_name,
                "description": log.description,
                "timestamp": log.created_at.isoformat(),
            })

        return {
            "customer_code": c.customer_code,
            "customer_name": c.full_name,
            "total_actions": len(history),
            "followup_history": history,
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        session.close()


def investigate_customer_case(customer_id_or_code: str) -> Dict[str, Any]:
    """Read-only customer investigation aggregator: compiles raw policies, payment schedules, documents, claims, and attention history for LLM interpretation.
    
    Args:
        customer_id_or_code: Customer UUID or customer code (e.g. CUST-1005).
    """
    profile = get_customer_360_profile(customer_id_or_code)
    if "error" in profile:
        return profile

    payments = get_customer_payment_history(profile["customer_id"])
    prev_att = get_customer_previous_attention(profile["customer_id"])

    return {
        "customer": {
            "customer_id": profile["customer_id"],
            "code": profile["customer_code"],
            "name": profile["full_name"],
            "tier": profile["tier"],
            "risk_segment": profile["risk_segment"],
            "total_clv": profile["total_clv"],
            "assigned_agent": profile["assigned_agent"],
        },
        "policies": profile.get("policies", []),
        "payment_schedules": payments.get("payment_schedules", []),
        "documents": profile.get("documents", []),
        "claims": profile.get("claims", []),
        "active_attention_count": len(profile.get("active_attention_items", [])),
        "attention_history": prev_att.get("attention_items", []),
    }


def generate_outreach_draft(
    customer_id_or_code: str,
    purpose: str,
    channel: str = "EMAIL",
) -> Dict[str, Any]:
    """Generates a professional, personalized customer outreach draft (Email or SMS) referencing actual policy and due dates.
    
    Args:
        customer_id_or_code: Customer UUID or customer code.
        purpose: Outreach goal, e.g. RENEWAL_OFFER, MISSING_KYC_REQUEST, PAYMENT_GRACE_REMINDER.
        channel: EMAIL or SMS (default: EMAIL).
    """
    profile = get_customer_360_profile(customer_id_or_code)
    if "error" in profile:
        return profile

    c_name = profile["full_name"]
    tier = profile["tier"]
    agent = profile["assigned_agent"]

    policies = profile.get("policies", [])
    primary_policy = policies[0] if policies else None
    pol_num = primary_policy["policy_number"] if primary_policy else "Your Policy"
    plan_name = primary_policy["plan_name"] if primary_policy else "Coverage Plan"

    purpose_upper = purpose.upper()

    if "RENEWAL" in purpose_upper:
        subject = f"Priority Renewal Notice: Secure your {plan_name} ({pol_num})"
        body = (
            f"Dear {c_name},\n\n"
            f"We value your loyalty as a {tier} policyholder with us. Your {plan_name} (Policy #{pol_num}) "
            f"is approaching its scheduled renewal date.\n\n"
            f"To ensure uninterrupted protection, our underwriting desk has authorized a tailored renewal plan. "
            f"Please review your renewal terms at your earliest convenience or reply directly to this message.\n\n"
            f"Warm regards,\n{agent}\nInsureDesk Customer Retention Desk"
        )
    elif "DOCUMENT" in purpose_upper or "KYC" in purpose_upper:
        subject = f"Action Required: Compliance Document Verification for Policy {pol_num}"
        body = (
            f"Dear {c_name},\n\n"
            f"During our underwriting compliance review, we noted that mandatory verification documentation for "
            f"Policy #{pol_num} requires your attention.\n\n"
            f"Please upload the required document via our secure policyholder portal to ensure complete claims eligibility.\n\n"
            f"Sincerely,\n{agent}\nInsureDesk Compliance Operations"
        )
    else:  # PAYMENT / OVERDUE
        subject = f"Urgent: Payment Status Reminder for Policy {pol_num}"
        body = (
            f"Dear {c_name},\n\n"
            f"This is an urgent courtesy reminder regarding your premium installment for Policy #{pol_num}. "
            f"To prevent grace period expiration and maintain active coverage, please authorize payment online or "
            f"contact us immediately to update your billing details.\n\n"
            f"Best regards,\n{agent}\nInsureDesk Billing Services"
        )

    return {
        "channel": channel.upper(),
        "customer_name": c_name,
        "customer_email": profile["email"],
        "customer_phone": profile["phone"],
        "subject": subject,
        "body": body,
        "is_draft": True,
        "requires_employee_approval": True,
    }


# ------------------------------------------------------------------------------
# Autonomous Watchdog Portfolio Investigation Tools (Strictly Read-Only)
# ------------------------------------------------------------------------------

def get_portfolio_overview() -> Dict[str, Any]:
    """Retrieve compact aggregate counts across the entire insurance portfolio (customers, policies, billing, documents, claims, attention items).
    Use this first to understand portfolio size before paginating customers.
    """
    session = SyncSessionLocal()
    try:
        total_customers = session.execute(select(func.count(Customer.id))).scalar() or 0
        total_policies = session.execute(select(func.count(Policy.id))).scalar() or 0
        active_policies = session.execute(
            select(func.count(Policy.id)).where(Policy.status == "ACTIVE")
        ).scalar() or 0
        renewal_pending = session.execute(
            select(func.count(Policy.id)).where(Policy.status == "RENEWAL_PENDING")
        ).scalar() or 0
        grace_policies = session.execute(
            select(func.count(Policy.id)).where(Policy.status == "GRACE_PERIOD")
        ).scalar() or 0
        unpaid_schedules = session.execute(
            select(func.count(PremiumSchedule.id)).where(PremiumSchedule.status != "PAID")
        ).scalar() or 0
        non_verified_docs = session.execute(
            select(func.count(PolicyDocument.id)).where(
                PolicyDocument.is_mandatory == True,
                PolicyDocument.status != "VERIFIED",
            )
        ).scalar() or 0
        open_claims = session.execute(
            select(func.count(Claim.id)).where(Claim.status.in_(["SUBMITTED", "UNDER_REVIEW"]))
        ).scalar() or 0
        active_attention = session.execute(
            select(func.count(CustomerAttentionItem.id)).where(CustomerAttentionItem.is_active == True)
        ).scalar() or 0

        return {
            "total_customers": total_customers,
            "total_policies": total_policies,
            "active_policies": active_policies,
            "renewal_pending_policies": renewal_pending,
            "grace_period_policies": grace_policies,
            "unpaid_premium_schedules": unpaid_schedules,
            "non_verified_mandatory_documents": non_verified_docs,
            "open_claims": open_claims,
            "active_attention_items": active_attention,
            "as_of_date": date.today().isoformat(),
        }
    except Exception as e:
        logger.error(f"get_portfolio_overview error: {e}")
        return {"error": str(e)}
    finally:
        session.close()


def list_customer_records(
    skip: int = 0,
    limit: int = 15,
    tier: Optional[str] = None,
    risk_segment: Optional[str] = None,
) -> Dict[str, Any]:
    """List paginated customer portfolio summaries with policy and alert counts for investigation triage.

    Args:
        skip: Pagination offset (default: 0).
        limit: Maximum customers per page (default: 15, max: 25).
        tier: Optional filter (STANDARD, VIP, HIGH_NET_WORTH).
        risk_segment: Optional filter (LOW, MEDIUM, HIGH).
    """
    session = SyncSessionLocal()
    try:
        safe_limit = max(1, min(limit, 25))
        stmt = (
            select(
                Customer,
                func.count(func.distinct(Policy.id)).label("policy_count"),
                func.count(func.distinct(CustomerAttentionItem.id))
                .filter(CustomerAttentionItem.is_active == True)
                .label("active_alerts"),
            )
            .outerjoin(Customer.policies)
            .outerjoin(Customer.attention_items)
            .group_by(Customer.id)
        )
        if tier:
            stmt = stmt.where(Customer.tier == tier.upper())
        if risk_segment:
            stmt = stmt.where(Customer.risk_segment == risk_segment.upper())

        stmt = stmt.order_by(Customer.customer_code.asc()).offset(max(0, skip)).limit(safe_limit)
        rows = session.execute(stmt).all()

        customers = []
        for c, pol_count, active_alerts in rows:
            customers.append({
                "customer_id": c.id,
                "customer_code": c.customer_code,
                "full_name": c.full_name,
                "tier": c.tier,
                "risk_segment": c.risk_segment,
                "total_clv": c.total_clv,
                "status": c.status,
                "policy_count": pol_count,
                "active_attention_count": active_alerts,
            })

        return {
            "skip": max(0, skip),
            "limit": safe_limit,
            "returned": len(customers),
            "customers": customers,
        }
    except Exception as e:
        logger.error(f"list_customer_records error: {e}")
        return {"error": str(e), "customers": []}
    finally:
        session.close()


def _resolve_customer(session, customer_id_or_code: str) -> Optional[Customer]:
    stmt = select(Customer).where(
        or_(
            Customer.id == customer_id_or_code,
            Customer.customer_code == customer_id_or_code.upper(),
        )
    )
    return session.execute(stmt).scalars().first()


def get_customer_policies(customer_id: str) -> Dict[str, Any]:
    """Retrieve all policies for a specific customer (by UUID or customer_code).

    Args:
        customer_id: Customer UUID or customer_code (e.g. CUST-1005).
    """
    session = SyncSessionLocal()
    try:
        c = _resolve_customer(session, customer_id)
        if not c:
            return {"error": f"Customer not found for '{customer_id}'"}

        today = date.today()
        policies = session.execute(
            select(Policy).where(Policy.customer_id == c.id).order_by(Policy.expiry_date.asc())
        ).scalars().all()

        return {
            "customer_id": c.id,
            "customer_code": c.customer_code,
            "full_name": c.full_name,
            "as_of_date": today.isoformat(),
            "policies": [
                {
                    "policy_id": p.id,
                    "policy_number": p.policy_number,
                    "policy_type": p.policy_type,
                    "plan_name": p.plan_name,
                    "status": p.status,
                    "premium_amount": p.premium_amount,
                    "sum_insured": p.sum_insured,
                    "payment_frequency": p.payment_frequency,
                    "start_date": p.start_date.isoformat(),
                    "expiry_date": p.expiry_date.isoformat(),
                    "days_to_expiry": (p.expiry_date - today).days,
                    "auto_renew": p.auto_renew,
                    "renewal_probability": p.renewal_probability,
                }
                for p in policies
            ],
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        session.close()


def get_customer_payment_history(customer_id: str) -> Dict[str, Any]:
    """Retrieve all premium payment schedules and billing history across a customer's policies.

    Args:
        customer_id: Customer UUID or customer_code (e.g. CUST-1005).
    """
    session = SyncSessionLocal()
    try:
        c = _resolve_customer(session, customer_id)
        if not c:
            return {"error": f"Customer not found for '{customer_id}'"}

        today = date.today()
        stmt = (
            select(PremiumSchedule)
            .join(PremiumSchedule.policy)
            .options(selectinload(PremiumSchedule.policy))
            .where(Policy.customer_id == c.id)
            .order_by(PremiumSchedule.due_date.desc())
        )
        schedules = session.execute(stmt).scalars().all()

        return {
            "customer_id": c.id,
            "customer_code": c.customer_code,
            "as_of_date": today.isoformat(),
            "payment_schedules": [
                {
                    "schedule_id": s.id,
                    "policy_id": s.policy_id,
                    "policy_number": s.policy.policy_number if s.policy else "N/A",
                    "installment_number": s.installment_number,
                    "amount_due": s.amount_due,
                    "due_date": s.due_date.isoformat(),
                    "grace_period_end": s.grace_period_end.isoformat(),
                    "days_past_due": max(0, (today - s.due_date).days),
                    "grace_days_remaining": (s.grace_period_end - today).days,
                    "status": s.status,
                    "payment_method": s.payment_method,
                    "retry_attempts": s.retry_attempts,
                    "failure_reason": s.failure_reason,
                    "paid_at": s.paid_at.isoformat() if s.paid_at else None,
                }
                for s in schedules
            ],
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        session.close()


def get_customer_documents(customer_id: str) -> Dict[str, Any]:
    """Retrieve all compliance and underwriting documents for a customer.

    Args:
        customer_id: Customer UUID or customer_code (e.g. CUST-1005).
    """
    session = SyncSessionLocal()
    try:
        c = _resolve_customer(session, customer_id)
        if not c:
            return {"error": f"Customer not found for '{customer_id}'"}

        docs = session.execute(
            select(PolicyDocument)
            .options(selectinload(PolicyDocument.policy))
            .where(PolicyDocument.customer_id == c.id)
        ).scalars().all()

        return {
            "customer_id": c.id,
            "customer_code": c.customer_code,
            "documents": [
                {
                    "document_id": d.id,
                    "policy_id": d.policy_id,
                    "policy_number": d.policy.policy_number if d.policy else "N/A",
                    "document_type": d.document_type,
                    "document_name": d.document_name,
                    "status": d.status,
                    "is_mandatory": d.is_mandatory,
                    "rejection_reason": d.rejection_reason,
                    "expiry_date": d.expiry_date.isoformat() if d.expiry_date else None,
                    "submitted_at": d.submitted_at.isoformat() if d.submitted_at else None,
                    "verified_at": d.verified_at.isoformat() if d.verified_at else None,
                }
                for d in docs
            ],
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        session.close()


def get_customer_claim_history(customer_id: str) -> Dict[str, Any]:
    """Retrieve claims history and settlement statuses for a customer.

    Args:
        customer_id: Customer UUID or customer_code (e.g. CUST-1005).
    """
    session = SyncSessionLocal()
    try:
        c = _resolve_customer(session, customer_id)
        if not c:
            return {"error": f"Customer not found for '{customer_id}'"}

        claims = session.execute(
            select(Claim)
            .options(selectinload(Claim.policy))
            .where(Claim.customer_id == c.id)
            .order_by(Claim.incident_date.desc())
        ).scalars().all()

        return {
            "customer_id": c.id,
            "customer_code": c.customer_code,
            "claims": [
                {
                    "claim_id": cl.id,
                    "claim_number": cl.claim_number,
                    "policy_id": cl.policy_id,
                    "policy_number": cl.policy.policy_number if cl.policy else "N/A",
                    "policy_sum_insured": cl.policy.sum_insured if cl.policy else None,
                    "claim_amount": cl.claim_amount,
                    "payout_amount": cl.payout_amount,
                    "status": cl.status,
                    "incident_date": cl.incident_date.isoformat(),
                    "description": cl.description,
                    "adjuster_notes": cl.adjuster_notes,
                }
                for cl in claims
            ],
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        session.close()


def get_customer_renewal_history(customer_id: str) -> Dict[str, Any]:
    """Retrieve policy renewal posture, auto-renew settings, and recent renewal/outreach audit events for a customer.

    Args:
        customer_id: Customer UUID or customer_code (e.g. CUST-1005).
    """
    session = SyncSessionLocal()
    try:
        c = _resolve_customer(session, customer_id)
        if not c:
            return {"error": f"Customer not found for '{customer_id}'"}

        today = date.today()
        policies = session.execute(
            select(Policy).where(Policy.customer_id == c.id).order_by(Policy.expiry_date.asc())
        ).scalars().all()

        audit_logs = session.execute(
            select(ActivityAuditLog)
            .where(ActivityAuditLog.customer_id == c.id)
            .order_by(ActivityAuditLog.created_at.desc())
            .limit(10)
        ).scalars().all()

        return {
            "customer_id": c.id,
            "customer_code": c.customer_code,
            "as_of_date": today.isoformat(),
            "policy_renewal_posture": [
                {
                    "policy_id": p.id,
                    "policy_number": p.policy_number,
                    "status": p.status,
                    "start_date": p.start_date.isoformat(),
                    "expiry_date": p.expiry_date.isoformat(),
                    "days_to_expiry": (p.expiry_date - today).days,
                    "auto_renew": p.auto_renew,
                    "renewal_probability": p.renewal_probability,
                    "premium_amount": p.premium_amount,
                }
                for p in policies
            ],
            "recent_activity_logs": [
                {
                    "action_type": a.action_type,
                    "actor_name": a.actor_name,
                    "description": a.description,
                    "created_at": a.created_at.isoformat(),
                }
                for a in audit_logs
            ],
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        session.close()


def get_customer_previous_attention(customer_id: str) -> Dict[str, Any]:
    """Retrieve both active and previously resolved/dismissed Watchdog attention items for a customer.

    Args:
        customer_id: Customer UUID or customer_code (e.g. CUST-1005).
    """
    session = SyncSessionLocal()
    try:
        c = _resolve_customer(session, customer_id)
        if not c:
            return {"error": f"Customer not found for '{customer_id}'"}

        items = session.execute(
            select(CustomerAttentionItem)
            .where(CustomerAttentionItem.customer_id == c.id)
            .order_by(CustomerAttentionItem.detected_at.desc())
        ).scalars().all()

        return {
            "customer_id": c.id,
            "customer_code": c.customer_code,
            "attention_items": [
                {
                    "attention_id": i.id,
                    "policy_id": i.policy_id,
                    "category": i.category,
                    "urgency_level": i.urgency_level,
                    "attention_score": i.attention_score,
                    "status": i.status,
                    "is_active": i.is_active,
                    "dedup_key": i.dedup_key,
                    "title": i.title,
                    "root_cause": i.root_cause,
                    "detected_at": i.detected_at.isoformat(),
                    "resolved_at": i.resolved_at.isoformat() if i.resolved_at else None,
                    "resolution_notes": i.resolution_notes,
                }
                for i in items
            ],
        }
    except Exception as e:
        return {"error": str(e)}
    finally:
        session.close()
