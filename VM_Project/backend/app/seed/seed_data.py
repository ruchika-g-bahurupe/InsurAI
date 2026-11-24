"""Enterprise Realistic Mock Dataset Generator for Insurance Customer Intelligence.

Generates 55+ realistic, fictional insurance customer profiles with rich
multi-line policies, document compliance vaults, billing schedules,
claims, attention items, analysis runs, and audit trails.
"""

import os
import sys
import uuid
from datetime import date, datetime, timedelta, timezone

# Ensure backend root is in sys.path
backend_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.core.database import SyncSessionLocal, sync_engine
from app.core.logging import logger
from app.db.base import Base
from app.db.models import (
    Customer,
    Policy,
    PolicyDocument,
    PremiumSchedule,
    Claim,
    CustomerAttentionItem,
    AgentAnalysisRun,
    AgentConversation,
    AgentMessage,
    ActivityAuditLog,
)


def seed_database():
    """Populates the database with 55+ rich, diverse insurance personas."""
    logger.info("Starting enterprise insurance data seeding...")
    
    # Re-create tables cleanly for a deterministic seed
    Base.metadata.drop_all(bind=sync_engine)
    Base.metadata.create_all(bind=sync_engine)

    session = SyncSessionLocal()
    try:
        now_utc = datetime.now(timezone.utc)
        today = date.today()

        # ----------------------------------------------------------------------
        # Agent Personnel
        # ----------------------------------------------------------------------
        agents = [
            "Sarah Jenkins (Senior Underwriter)",
            "David Chen (Retention Specialist)",
            "Elena Rostova (VIP Relationship Manager)",
            "Marcus Vance (Risk & Compliance Officer)",
            "Priya Sharma (Portfolio Analyst)",
        ]

        # ----------------------------------------------------------------------
        # 55 Fictional Customer Personas
        # ----------------------------------------------------------------------
        personas_data = [
            # 1-10: VIP & High Net Worth (High CLV, Multi-policy, high retention value)
            ("Aarav", "Patel", "aarav.patel@fictional-domain.com", "+1-555-0101", "VIP", "LOW", 145000.0, agents[2], "San Francisco", "CA"),
            ("Eleanor", "Vanderbilt", "eleanor.v@fictional-domain.com", "+1-555-0102", "HIGH_NET_WORTH", "LOW", 320000.0, agents[2], "New York", "NY"),
            ("Rajesh", "Singhania", "rajesh.s@fictional-domain.com", "+1-555-0103", "VIP", "LOW", 185000.0, agents[2], "Chicago", "IL"),
            ("Sophia", "Mercer", "sophia.m@fictional-domain.com", "+1-555-0104", "VIP", "MEDIUM", 110000.0, agents[0], "Boston", "MA"),
            ("Vikram", "Mehta", "vikram.mehta@fictional-domain.com", "+1-555-0105", "VIP", "HIGH", 160000.0, agents[1], "Austin", "TX"),
            ("Claire", "DuPont", "claire.dupont@fictional-domain.com", "+1-555-0106", "HIGH_NET_WORTH", "LOW", 290000.0, agents[2], "Seattle", "WA"),
            ("Alexander", "Wright", "alex.wright@fictional-domain.com", "+1-555-0107", "VIP", "MEDIUM", 135000.0, agents[0], "Denver", "CO"),
            ("Ananya", "Deshmukh", "ananya.d@fictional-domain.com", "+1-555-0108", "VIP", "LOW", 125000.0, agents[2], "Atlanta", "GA"),
            ("Harrison", "Sterling", "h.sterling@fictional-domain.com", "+1-555-0109", "HIGH_NET_WORTH", "MEDIUM", 410000.0, agents[2], "Miami", "FL"),
            ("Mira", "Nair", "mira.nair@fictional-domain.com", "+1-555-0110", "VIP", "LOW", 140000.0, agents[0], "Dallas", "TX"),

            # 11-25: Standard Customers with Critical / Immediate Risks (Expiry, Grace Period, Failed Premiums)
            ("Liam", "O'Connor", "liam.oc@fictional-domain.com", "+1-555-0111", "STANDARD", "HIGH", 28000.0, agents[1], "Chicago", "IL"),
            ("Pooja", "Iyer", "pooja.iyer@fictional-domain.com", "+1-555-0112", "STANDARD", "HIGH", 34000.0, agents[3], "Jersey City", "NJ"),
            ("Mateo", "Hernandez", "mateo.h@fictional-domain.com", "+1-555-0113", "STANDARD", "HIGH", 22000.0, agents[1], "Phoenix", "AZ"),
            ("Chloe", "Bennett", "chloe.b@fictional-domain.com", "+1-555-0114", "STANDARD", "HIGH", 42000.0, agents[0], "San Diego", "CA"),
            ("Rohan", "Gupta", "rohan.g@fictional-domain.com", "+1-555-0115", "STANDARD", "HIGH", 31000.0, agents[3], "Charlotte", "NC"),
            ("Emma", "Watson", "emma.w@fictional-domain.com", "+1-555-0116", "STANDARD", "MEDIUM", 19500.0, agents[1], "Portland", "OR"),
            ("Kavita", "Reddy", "kavita.r@fictional-domain.com", "+1-555-0117", "STANDARD", "HIGH", 52000.0, agents[3], "Tampa", "FL"),
            ("Noah", "Sullivan", "noah.s@fictional-domain.com", "+1-555-0118", "STANDARD", "HIGH", 27000.0, agents[1], "Columbus", "OH"),
            ("Zara", "Khan", "zara.khan@fictional-domain.com", "+1-555-0119", "STANDARD", "MEDIUM", 38000.0, agents[0], "Indianapolis", "IN"),
            ("Lucas", "Silva", "lucas.silva@fictional-domain.com", "+1-555-0120", "STANDARD", "HIGH", 16000.0, agents[3], "Salt Lake City", "UT"),
            ("Siddharth", "Verma", "sid.verma@fictional-domain.com", "+1-555-0121", "STANDARD", "HIGH", 44000.0, agents[1], "Philadelphia", "PA"),
            ("Grace", "Kim", "grace.kim@fictional-domain.com", "+1-555-0122", "STANDARD", "HIGH", 29500.0, agents[0], "Minneapolis", "MN"),
            ("Arjun", "Menon", "arjun.m@fictional-domain.com", "+1-555-0123", "STANDARD", "HIGH", 36000.0, agents[3], "Raleigh", "NC"),
            ("Zoe", "Kravitz", "zoe.k@fictional-domain.com", "+1-555-0124", "STANDARD", "MEDIUM", 23000.0, agents[1], "Nashville", "TN"),
            ("Deepak", "Chopra", "deepak.c@fictional-domain.com", "+1-555-0125", "STANDARD", "HIGH", 48000.0, agents[0], "Kansas City", "MO"),

            # 26-40: Missing Document & Compliance Friction Scenarios
            ("Ethan", "Hunt", "ethan.h@fictional-domain.com", "+1-555-0126", "STANDARD", "HIGH", 41000.0, agents[3], "Washington", "DC"),
            ("Neha", "Kapoor", "neha.k@fictional-domain.com", "+1-555-0127", "STANDARD", "MEDIUM", 33000.0, agents[3], "Detroit", "MI"),
            ("Mason", "Clark", "mason.c@fictional-domain.com", "+1-555-0128", "STANDARD", "HIGH", 25000.0, agents[3], "Memphis", "TN"),
            ("Tanya", "Bose", "tanya.b@fictional-domain.com", "+1-555-0129", "STANDARD", "MEDIUM", 29000.0, agents[0], "Baltimore", "MD"),
            ("Oliver", "Queen", "oliver.q@fictional-domain.com", "+1-555-0130", "VIP", "HIGH", 85000.0, agents[2], "Star City", "CA"),
            ("Sanjay", "Dutt", "sanjay.d@fictional-domain.com", "+1-555-0131", "STANDARD", "HIGH", 37000.0, agents[3], "Las Vegas", "NV"),
            ("Isabella", "Rossi", "isabella.r@fictional-domain.com", "+1-555-0132", "STANDARD", "MEDIUM", 31500.0, agents[1], "Albuquerque", "NM"),
            ("Manish", "Malhotra", "manish.m@fictional-domain.com", "+1-555-0133", "VIP", "MEDIUM", 95000.0, agents[2], "Orlando", "FL"),
            ("Ava", "Martinez", "ava.m@fictional-domain.com", "+1-555-0134", "STANDARD", "HIGH", 26000.0, agents[3], "Cleveland", "OH"),
            ("Karan", "Johar", "karan.j@fictional-domain.com", "+1-555-0135", "STANDARD", "LOW", 45000.0, agents[0], "Omaha", "NE"),
            ("Mia", "Wallace", "mia.w@fictional-domain.com", "+1-555-0136", "STANDARD", "HIGH", 21000.0, agents[1], "Tulsa", "OK"),
            ("Aditya", "Roy", "aditya.r@fictional-domain.com", "+1-555-0137", "STANDARD", "MEDIUM", 34000.0, agents[3], "Honolulu", "HI"),
            ("Harper", "Lee", "harper.l@fictional-domain.com", "+1-555-0138", "STANDARD", "LOW", 39000.0, agents[0], "Richmond", "VA"),
            ("Varun", "Dhawan", "varun.d@fictional-domain.com", "+1-555-0139", "STANDARD", "MEDIUM", 28000.0, agents[1], "Boise", "ID"),
            ("Abigail", "Adams", "abigail.a@fictional-domain.com", "+1-555-0140", "STANDARD", "LOW", 51000.0, agents[0], "Providence", "RI"),

            # 41-55: Healthy Baseline, Renewal Pipeline & Low Risk Profiles
            ("Daniel", "Craig", "daniel.c@fictional-domain.com", "+1-555-0141", "VIP", "LOW", 130000.0, agents[2], "San Jose", "CA"),
            ("Shilpa", "Shetty", "shilpa.s@fictional-domain.com", "+1-555-0142", "STANDARD", "LOW", 42000.0, agents[4], "Sacramento", "CA"),
            ("Henry", "Cavill", "henry.c@fictional-domain.com", "+1-555-0143", "STANDARD", "LOW", 38000.0, agents[4], "Fresno", "CA"),
            ("Rani", "Mukerji", "rani.m@fictional-domain.com", "+1-555-0144", "STANDARD", "LOW", 49000.0, agents[4], "Long Beach", "CA"),
            ("James", "Bond", "james.b@fictional-domain.com", "+1-555-0145", "VIP", "LOW", 175000.0, agents[2], "San Francisco", "CA"),
            ("Kareena", "Kapoor", "kareena.k@fictional-domain.com", "+1-555-0146", "STANDARD", "LOW", 54000.0, agents[4], "Oakland", "CA"),
            ("Jack", "Reacher", "jack.r@fictional-domain.com", "+1-555-0147", "STANDARD", "LOW", 29000.0, agents[4], "Bakersfield", "CA"),
            ("Alia", "Bhatt", "alia.b@fictional-domain.com", "+1-555-0148", "VIP", "LOW", 160000.0, agents[2], "Anaheim", "CA"),
            ("Arthur", "Pendelton", "arthur.p@fictional-domain.com", "+1-555-0149", "STANDARD", "LOW", 31000.0, agents[4], "Santa Ana", "CA"),
            ("Shraddha", "Kapoor", "shraddha.k@fictional-domain.com", "+1-555-0150", "STANDARD", "LOW", 47000.0, agents[4], "Riverside", "CA"),
            ("Benjamin", "Franklin", "ben.f@fictional-domain.com", "+1-555-0151", "HIGH_NET_WORTH", "LOW", 260000.0, agents[2], "Philadelphia", "PA"),
            ("Dia", "Mirza", "dia.m@fictional-domain.com", "+1-555-0152", "STANDARD", "LOW", 36000.0, agents[4], "Irvine", "CA"),
            ("Samuel", "Jackson", "samuel.j@fictional-domain.com", "+1-555-0153", "VIP", "LOW", 145000.0, agents[2], "Los Angeles", "CA"),
            ("Preity", "Zinta", "preity.z@fictional-domain.com", "+1-555-0154", "STANDARD", "LOW", 43000.0, agents[4], "San Diego", "CA"),
            ("Thomas", "Shelby", "thomas.s@fictional-domain.com", "+1-555-0155", "HIGH_NET_WORTH", "LOW", 380000.0, agents[2], "Birmingham", "AL"),
        ]

        created_customers = []
        for i, (fn, ln, email, phone, tier, risk, clv, agent, city, state) in enumerate(personas_data, start=1001):
            cust = Customer(
                customer_code=f"CUST-{i}",
                first_name=fn,
                last_name=ln,
                email=email,
                phone=phone,
                date_of_birth=date(1975 + (i % 25), 1 + (i % 12), 1 + (i % 27)),
                tier=tier,
                risk_segment=risk,
                total_clv=clv,
                assigned_agent=agent,
                city=city,
                state=state,
                status="ACTIVE",
                created_at=now_utc - timedelta(days=200 + i % 150),
            )
            session.add(cust)
            created_customers.append(cust)

        session.flush()
        logger.info(f"Seeded {len(created_customers)} customers.")

        # ----------------------------------------------------------------------
        # Policies, Documents, Premium Schedules, Claims, and Attention Items
        # ----------------------------------------------------------------------
        attention_items_to_add = []
        audit_logs_to_add = []

        for idx, customer in enumerate(created_customers):
            # Deterministic scenario steering by customer index
            c_code = customer.customer_code

            # ------------------------------------------------------------------
            # Scenario A: Policy Expiring in 7 Days (CRITICAL ATTENTION)
            # ------------------------------------------------------------------
            if idx in (10, 11):  # Liam O'Connor, Pooja Iyer
                pol = Policy(
                    customer_id=customer.id,
                    policy_number=f"POL-HLT-{2000 + idx}",
                    policy_type="HEALTH",
                    plan_name="Comprehensive Executive Mediclaim",
                    sum_insured=250000.0,
                    premium_amount=2450.0,
                    payment_frequency="ANNUAL",
                    start_date=today - timedelta(days=358),
                    expiry_date=today + timedelta(days=7),
                    status="ACTIVE",
                    auto_renew=False,
                    renewal_probability=0.35,
                )
                session.add(pol)
                session.flush()

                # Document: Verified
                doc = PolicyDocument(
                    policy_id=pol.id,
                    customer_id=customer.id,
                    document_type="KYC_ID",
                    document_name="Government ID & Passport.pdf",
                    status="VERIFIED",
                    is_mandatory=True,
                    verified_at=now_utc - timedelta(days=300),
                )
                session.add(doc)

                # Premium: Last one paid, renewal due
                prem = PremiumSchedule(
                    policy_id=pol.id,
                    installment_number=1,
                    amount_due=2450.0,
                    due_date=today + timedelta(days=7),
                    grace_period_end=today + timedelta(days=37),
                    status="PENDING",
                    payment_method="CREDIT_CARD",
                )
                session.add(prem)

                # Attention Item
                dedup = f"{customer.id}:POLICY_EXPIRY:{pol.id}:EXP_7D"
                att = CustomerAttentionItem(
                    customer_id=customer.id,
                    policy_id=pol.id,
                    category="POLICY_EXPIRY",
                    urgency_level="CRITICAL",
                    attention_score=94.5,
                    dedup_key=dedup,
                    is_active=True,
                    title=f"Health Policy {pol.policy_number} Expiring in 7 Days",
                    root_cause="Upcoming policy lapse without auto-renewal or renewal payment confirmation.",
                    ai_summary=f"Customer {customer.full_name} has an active health policy with $250k coverage expiring in exactly 7 days. Renewal probability is low (35%) and no interaction recorded in 60 days.",
                    ai_recommendation="Initiate urgent outbound outreach. Offer loyalty tier renewal protection with a waived copay rider to secure early renewal.",
                    suggested_action={
                        "action_type": "DRAFT_RENEWAL_OFFER",
                        "policy_id": pol.id,
                        "discount_pct": 5,
                        "channel": "EMAIL_SMS",
                        "urgency_badge": "EXPIRING_7_DAYS"
                    },
                    status="OPEN",
                    assigned_to=customer.assigned_agent,
                )
                attention_items_to_add.append(att)

                audit_logs_to_add.append(
                    ActivityAuditLog(
                        customer_id=customer.id,
                        action_type="ATTENTION_FLAGGED",
                        actor="SYSTEM_AI",
                        actor_name="AI Policy Expiry Watchdog",
                        description=f"Generated Critical Attention Alert: Policy {pol.policy_number} expiring in 7 days.",
                    )
                )

            # ------------------------------------------------------------------
            # Scenario B: Overdue Premium in Grace Period (HIGH ATTENTION)
            # ------------------------------------------------------------------
            elif idx in (12, 13):  # Mateo Hernandez, Chloe Bennett
                pol = Policy(
                    customer_id=customer.id,
                    policy_number=f"POL-AUT-{2000 + idx}",
                    policy_type="MOTOR",
                    plan_name="Zero-Depreciation Private Vehicle Shield",
                    sum_insured=45000.0,
                    premium_amount=1200.0,
                    payment_frequency="QUARTERLY",
                    start_date=today - timedelta(days=90),
                    expiry_date=today + timedelta(days=275),
                    status="GRACE_PERIOD",
                    auto_renew=True,
                    renewal_probability=0.55,
                )
                session.add(pol)
                session.flush()

                # Premium: Overdue, Grace period ending in 4 days
                prem = PremiumSchedule(
                    policy_id=pol.id,
                    installment_number=2,
                    amount_due=300.0,
                    due_date=today - timedelta(days=26),
                    grace_period_end=today + timedelta(days=4),
                    status="OVERDUE",
                    payment_method="AUTO_DEBIT",
                    retry_attempts=3,
                    failure_reason="Insufficient funds on secondary checking account (code: ERR_INSUFFICIENT_FUNDS).",
                )
                session.add(prem)

                dedup = f"{customer.id}:PREMIUM_OVERDUE:{pol.id}:GRACE_EXP_4D"
                att = CustomerAttentionItem(
                    customer_id=customer.id,
                    policy_id=pol.id,
                    category="PREMIUM_OVERDUE",
                    urgency_level="CRITICAL",
                    attention_score=92.0,
                    dedup_key=dedup,
                    is_active=True,
                    title=f"Premium Overdue: Grace Period Expires in 4 Days",
                    root_cause="Auto-debit failed 3 times; grace period cutoff in 4 days before statutory policy cancellation.",
                    ai_summary=f"Quarterly installment #2 of $300.00 failed 3 consecutive bank debits. Policy enters cancellation state on {today + timedelta(days=4)} unless resolved.",
                    ai_recommendation="Contact customer via SMS payment link or offer a 10-day grace extension with alternate payment method setup.",
                    suggested_action={
                        "action_type": "SEND_PAYMENT_LINK",
                        "policy_id": pol.id,
                        "amount_due": 300.0,
                        "payment_channel": "INSTANT_WEB_PORTAL",
                        "extension_available": True
                    },
                    status="OPEN",
                    assigned_to=customer.assigned_agent,
                )
                attention_items_to_add.append(att)

            # ------------------------------------------------------------------
            # Scenario C: Mandatory KYC Document Rejected / Missing (COMPLIANCE ISSUE)
            # ------------------------------------------------------------------
            elif idx in (25, 26, 27):  # Ethan Hunt, Neha Kapoor, Mason Clark
                pol = Policy(
                    customer_id=customer.id,
                    policy_number=f"POL-LIF-{2000 + idx}",
                    policy_type="LIFE",
                    plan_name="Term Assure Max - Family Security",
                    sum_insured=750000.0,
                    premium_amount=3800.0,
                    payment_frequency="ANNUAL",
                    start_date=today - timedelta(days=45),
                    expiry_date=today + timedelta(days=320),
                    status="ACTIVE",
                    auto_renew=True,
                    renewal_probability=0.80,
                )
                session.add(pol)
                session.flush()

                # Document: REJECTED Medical Declaration
                doc1 = PolicyDocument(
                    policy_id=pol.id,
                    customer_id=customer.id,
                    document_type="MEDICAL_DECLARATION",
                    document_name="Attending_Physician_Statement.pdf",
                    status="REJECTED",
                    is_mandatory=True,
                    rejection_reason="Underwriting rejected: Physician signature and stamp missing on Section IV (Cardiology history).",
                    submitted_at=now_utc - timedelta(days=12),
                )
                # Document: PENDING KYC ID
                doc2 = PolicyDocument(
                    policy_id=pol.id,
                    customer_id=customer.id,
                    document_type="PROOF_OF_ADDRESS",
                    document_name="Utility_Bill.pdf",
                    status="PENDING_SUBMISSION",
                    is_mandatory=True,
                )
                session.add_all([doc1, doc2])

                dedup = f"{customer.id}:MISSING_DOCS:{pol.id}:MED_REJECTED"
                att = CustomerAttentionItem(
                    customer_id=customer.id,
                    policy_id=pol.id,
                    category="MISSING_DOCS",
                    urgency_level="HIGH",
                    attention_score=84.0,
                    dedup_key=dedup,
                    is_active=True,
                    title=f"Mandatory Medical Declaration Rejected by Underwriting",
                    root_cause="Physician statement rejected due to missing signature; policy risk of underwriting suspension.",
                    ai_summary=f"Policy {pol.policy_number} for customer {customer.full_name} cannot be confirmed for claims eligibility until a signed Medical Statement is resubmitted.",
                    ai_recommendation="Send a secure document upload request with pre-highlighted signature guidance to the customer's verified phone and email.",
                    suggested_action={
                        "action_type": "REQUEST_DOCUMENT_REUPLOAD",
                        "policy_id": pol.id,
                        "document_type": "MEDICAL_DECLARATION",
                        "secure_upload_token": str(uuid.uuid4())[:8]
                    },
                    status="OPEN",
                    assigned_to=customer.assigned_agent,
                )
                attention_items_to_add.append(att)

            # ------------------------------------------------------------------
            # Scenario D: High CLV VIP Renewal Pipeline (RENEWAL FOLLOW-UP)
            # ------------------------------------------------------------------
            elif idx in (0, 1, 2, 4):  # Aarav Patel, Eleanor Vanderbilt, Rajesh Singhania, Vikram Mehta
                pol1 = Policy(
                    customer_id=customer.id,
                    policy_number=f"POL-PRP-{2000 + idx}",
                    policy_type="PROPERTY",
                    plan_name="Prestige Estate All-Risk Property Shield",
                    sum_insured=2000000.0,
                    premium_amount=8500.0,
                    payment_frequency="ANNUAL",
                    start_date=today - timedelta(days=340),
                    expiry_date=today + timedelta(days=25),
                    status="RENEWAL_PENDING",
                    auto_renew=False,
                    renewal_probability=0.78,
                )
                pol2 = Policy(
                    customer_id=customer.id,
                    policy_number=f"POL-AUT-{3000 + idx}",
                    policy_type="MOTOR",
                    plan_name="Luxury Exotic Vehicle Multi-Car Coverage",
                    sum_insured=180000.0,
                    premium_amount=4200.0,
                    payment_frequency="ANNUAL",
                    start_date=today - timedelta(days=120),
                    expiry_date=today + timedelta(days=245),
                    status="ACTIVE",
                    auto_renew=True,
                    renewal_probability=0.92,
                )
                session.add_all([pol1, pol2])
                session.flush()

                # Verified documents
                session.add(
                    PolicyDocument(
                        policy_id=pol1.id,
                        customer_id=customer.id,
                        document_type="PROPERTY_SURVEY",
                        document_name="Estate_Appraisal_Report.pdf",
                        status="VERIFIED",
                        is_mandatory=True,
                        verified_at=now_utc - timedelta(days=320),
                    )
                )

                # Attention Item: VIP High CLV Renewal
                dedup = f"{customer.id}:RENEWAL_FOLLOWUP:{pol1.id}:VIP_RENEWAL_25D"
                att = CustomerAttentionItem(
                    customer_id=customer.id,
                    policy_id=pol1.id,
                    category="RENEWAL_FOLLOWUP",
                    urgency_level="HIGH",
                    attention_score=88.5,
                    dedup_key=dedup,
                    is_active=True,
                    title=f"VIP Renewal: {customer.full_name} (${pol1.premium_amount:,.2f} Premium at Stake)",
                    root_cause=f"High-Net-Worth VIP customer policy expires in 25 days; total CLV is ${customer.total_clv:,.2f}.",
                    ai_summary=f"Customer is flagged as {customer.tier} with $2M property coverage. Policy requires personal concierge renewal outreach to lock in multi-line policy bundle.",
                    ai_recommendation="Schedule executive relationship manager review. Present bundled multi-policy renewal with upgraded natural disaster endorsement.",
                    suggested_action={
                        "action_type": "SCHEDULE_VIP_CALL",
                        "policy_id": pol1.id,
                        "relationship_manager": customer.assigned_agent,
                        "suggested_bundle_discount": "7.5%"
                    },
                    status="IN_PROGRESS",
                    assigned_to=customer.assigned_agent,
                )
                attention_items_to_add.append(att)

            # ------------------------------------------------------------------
            # Scenario E: Active Claim Under Investigation (RISK SURGE ALERT)
            # ------------------------------------------------------------------
            elif idx in (3, 14):  # Sophia Mercer, Rohan Gupta
                pol = Policy(
                    customer_id=customer.id,
                    policy_number=f"POL-AUT-{2000 + idx}",
                    policy_type="MOTOR",
                    plan_name="Commercial Fleet & Transport Protection",
                    sum_insured=80000.0,
                    premium_amount=2900.0,
                    payment_frequency="ANNUAL",
                    start_date=today - timedelta(days=180),
                    expiry_date=today + timedelta(days=185),
                    status="ACTIVE",
                    auto_renew=True,
                    renewal_probability=0.48,
                )
                session.add(pol)
                session.flush()

                # Large Claim Filed
                claim = Claim(
                    policy_id=pol.id,
                    customer_id=customer.id,
                    claim_number=f"CLM-{today.year}-{9100 + idx}",
                    claim_amount=42500.0,
                    status="UNDER_INVESTIGATION",
                    incident_date=today - timedelta(days=18),
                    description="Multiple vehicle collision on Interstate 90 during heavy storm; total loss on transit vehicle.",
                    adjuster_notes="Police report verified; awaiting commercial cargo inspection validation before payout authorization.",
                )
                session.add(claim)

                dedup = f"{customer.id}:RISK_ALERT:{pol.id}:HIGH_CLAIM_SURGE"
                att = CustomerAttentionItem(
                    customer_id=customer.id,
                    policy_id=pol.id,
                    category="RISK_ALERT",
                    urgency_level="HIGH",
                    attention_score=81.0,
                    dedup_key=dedup,
                    is_active=True,
                    title=f"Significant Claim Under Investigation (${claim.claim_amount:,.2f})",
                    root_cause=f"High-severity claim filed on policy {pol.policy_number} impacting risk underwriting score.",
                    ai_summary=f"Claim #{claim.claim_number} represents 53% of policy sum insured. Risk tier elevated to HIGH. Customer satisfaction during claim settlement will dictate retention.",
                    ai_recommendation="Liaise directly with Senior Claims Adjuster. Ensure proactive status updates are sent to customer to prevent churn during claim processing.",
                    suggested_action={
                        "action_type": "VIEW_CLAIM_DOSSIER",
                        "claim_id": claim.id,
                        "notify_adjuster": True
                    },
                    status="OPEN",
                    assigned_to=customer.assigned_agent,
                )
                attention_items_to_add.append(att)

            # ------------------------------------------------------------------
            # Scenario F: Resolved / Dismissed Historical Recommendations
            # ------------------------------------------------------------------
            elif idx in (15, 16):  # Emma Watson, Kavita Reddy
                pol = Policy(
                    customer_id=customer.id,
                    policy_number=f"POL-HLT-{2000 + idx}",
                    policy_type="HEALTH",
                    plan_name="Family Health Guard - Silver",
                    sum_insured=100000.0,
                    premium_amount=1500.0,
                    payment_frequency="ANNUAL",
                    start_date=today - timedelta(days=200),
                    expiry_date=today + timedelta(days=165),
                    status="ACTIVE",
                    auto_renew=True,
                    renewal_probability=0.88,
                )
                session.add(pol)
                session.flush()

                # Resolved Attention Item
                dedup = f"{customer.id}:MISSING_DOCS:{pol.id}:KYC_RESOLVED"
                att = CustomerAttentionItem(
                    customer_id=customer.id,
                    policy_id=pol.id,
                    category="MISSING_DOCS",
                    urgency_level="MEDIUM",
                    attention_score=60.0,
                    dedup_key=dedup,
                    is_active=False,
                    title=f"KYC Verification Completed for {customer.full_name}",
                    root_cause="KYC was previously flagged as pending; employee completed verification.",
                    ai_summary="All national ID documents and address proofs have been uploaded and verified.",
                    ai_recommendation="No action needed. Compliance verified.",
                    status="RESOLVED",
                    assigned_to=customer.assigned_agent,
                    resolved_at=now_utc - timedelta(days=3),
                    resolved_by=customer.assigned_agent,
                    resolution_notes="Customer uploaded passport and electricity bill via customer self-service portal.",
                )
                attention_items_to_add.append(att)

            # ------------------------------------------------------------------
            # Scenario G: Standard Healthy Policy Baseline (Remaining Customers)
            # ------------------------------------------------------------------
            else:
                p_types = ["HEALTH", "MOTOR", "LIFE", "PROPERTY", "COMMERCIAL"]
                p_type = p_types[idx % len(p_types)]
                plans = {
                    "HEALTH": ("Active Health Shield Pro", 150000.0, 1850.0),
                    "MOTOR": ("DriveSafe Comprehensive Plan", 35000.0, 950.0),
                    "LIFE": ("SecureHorizon Term Life", 500000.0, 2200.0),
                    "PROPERTY": ("HomeCare Standard Insurance", 450000.0, 1600.0),
                    "COMMERCIAL": ("CyberRisk Business Defense", 1000000.0, 5400.0),
                }
                plan_name, sum_ins, prem_amt = plans[p_type]

                pol = Policy(
                    customer_id=customer.id,
                    policy_number=f"POL-{p_type[:3]}-{4000 + idx}",
                    policy_type=p_type,
                    plan_name=plan_name,
                    sum_insured=sum_ins,
                    premium_amount=prem_amt,
                    payment_frequency="ANNUAL",
                    start_date=today - timedelta(days=100 + (idx * 3 % 200)),
                    expiry_date=today + timedelta(days=120 + (idx * 5 % 240)),
                    status="ACTIVE",
                    auto_renew=(idx % 2 == 0),
                    renewal_probability=0.75 + (idx % 20) * 0.01,
                )
                session.add(pol)
                session.flush()

                # Verified Document
                session.add(
                    PolicyDocument(
                        policy_id=pol.id,
                        customer_id=customer.id,
                        document_type="KYC_ID",
                        document_name="National_Identity_Card.pdf",
                        status="VERIFIED",
                        is_mandatory=True,
                        verified_at=now_utc - timedelta(days=90),
                    )
                )

                # Paid Premium
                session.add(
                    PremiumSchedule(
                        policy_id=pol.id,
                        installment_number=1,
                        amount_due=prem_amt,
                        due_date=pol.start_date,
                        grace_period_end=pol.start_date + timedelta(days=30),
                        status="PAID",
                        paid_at=datetime.combine(pol.start_date, datetime.min.time(), tzinfo=timezone.utc),
                        payment_method="AUTO_DEBIT",
                        transaction_reference=f"TXN-{uuid.uuid4().hex[:10].upper()}",
                    )
                )

        # Bulk insert all attention items
        session.add_all(attention_items_to_add)
        session.add_all(audit_logs_to_add)
        session.flush()
        logger.info(f"Seeded {len(attention_items_to_add)} customer attention items.")

        # ----------------------------------------------------------------------
        # Seed Initial Agent Analysis Run (Telemetry History)
        # ----------------------------------------------------------------------
        baseline_run = AgentAnalysisRun(
            run_type="PROACTIVE_SWEEP",
            trigger_source="SCHEDULED_CRON",
            status="COMPLETED",
            records_scanned=len(created_customers),
            issues_detected=len(attention_items_to_add),
            new_recommendations_created=len(attention_items_to_add),
            recommendations_updated=0,
            execution_time_ms=1420.5,
            model_used="gemini-2.5-flash",
            summary_notes="Initial automated customer intelligence scan completed across all portfolios. Flagged critical policy expiries, overdue grace periods, and KYC deficits.",
            started_at=now_utc - timedelta(minutes=15),
            completed_at=now_utc - timedelta(minutes=14, seconds=45),
        )
        session.add(baseline_run)

        # ----------------------------------------------------------------------
        # Seed Sample Agent Conversation (Copilot Investigation History)
        # ----------------------------------------------------------------------
        target_customer = created_customers[4]  # Vikram Mehta
        conv = AgentConversation(
            customer_id=target_customer.id,
            title=f"Retention Investigation: {target_customer.full_name}",
            session_metadata={"priority": "HIGH", "agent": target_customer.assigned_agent},
            created_at=now_utc - timedelta(hours=2),
            updated_at=now_utc - timedelta(hours=1, minutes=50),
        )
        session.add(conv)
        session.flush()

        msg1 = AgentMessage(
            conversation_id=conv.id,
            sender="USER",
            content=f"Can you give me a breakdown of Vikram Mehta's policies and why he was flagged for high attention?",
            created_at=now_utc - timedelta(hours=2),
        )
        msg2 = AgentMessage(
            conversation_id=conv.id,
            sender="TOOL",
            content="Tool executed: get_customer_360_profile(customer_id='...')",
            tool_calls=[{"name": "get_customer_360_profile", "arguments": {"customer_id": target_customer.id}}],
            tool_results=[{"customer_code": target_customer.customer_code, "tier": "VIP", "clv": 160000.0, "active_policies": 2}],
            created_at=now_utc - timedelta(hours=1, minutes=59),
        )
        msg3 = AgentMessage(
            conversation_id=conv.id,
            sender="ASSISTANT",
            content=(
                f"**Investigation Summary for {target_customer.full_name} ({target_customer.customer_code})**\n\n"
                f"- **VIP Status & Value**: Total Lifetime Value is **${target_customer.total_clv:,.2f}** with 2 active high-value policies.\n"
                f"- **Primary Flag**: Prestige Property Policy has upcoming renewal in 25 days with **$8,500.00 annual premium** at stake.\n"
                f"- **Recommended Next Action**: Present a bundled multi-policy renewal offer with a 7.5% loyalty discount before competitor solicitation."
            ),
            created_at=now_utc - timedelta(hours=1, minutes=58),
        )
        session.add_all([msg1, msg2, msg3])

        session.commit()
        logger.info("Successfully committed all enterprise mock data.")

    except Exception as e:
        session.rollback()
        logger.error(f"Seeding failed: {e}")
        raise
    finally:
        session.close()


if __name__ == "__main__":
    seed_database()
