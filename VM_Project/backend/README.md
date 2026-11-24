# VM_project Backend - Insurance Customer Intelligence Platform

High-performance FastAPI backend with SQLAlchemy 2.0, Pydantic v2, and a centralized Gemini-powered AI Agent Subsystem featuring **The Watchdog** (Proactive Customer Monitoring) and **The Investigator** (Conversational Copilot with Native Tool Calling).

---

## Architectural Highlights (Phases 1, 2 & 3 Implemented)

### 1. Unified AI Agent Subsystem (`app/agent/`)
- **Single Shared Intelligence Core (`intelligence_core.py`)**:
  - Connects **The Watchdog** and **The Investigator** to the shared Python Tool Registry (18 total tools; 10 strictly read-only Watchdog tools).
  - Integrates the modern **Google GenAI SDK** (`google-genai` v3.6.1) supporting structured JSON outputs and native function calling.
  - Automatically operates in **Cognitive Emulation Mode** if `GEMINI_API_KEY` is omitted, and seamlessly activates **Live Gemini API** mode as soon as an API key is provided in `.env`.
- **The Watchdog – Proactive AI Monitoring (`proactive_scanner.py`)**:
  - Automatically queries portfolios for expiry horizons, grace period billing issues, and rejected/pending compliance documents.
  - Batches customer circumstances into structured diagnostic payloads.
  - Synthesizes transparent attention scores (0–100), root causes, and actionable recommendations.
  - Strictly prevents duplicate active recommendations via composite deduplication keys (`dedup_key`).
  - Records execution telemetry and timing in `agent_analysis_runs`.
- **The Investigator – Conversational Copilot (`copilot_agent.py`)**:
  - Genuine tool-using agent using function calling.
  - Dispatches queries to Python tools (`search_customer_records`, `get_customer_360_profile`, `get_expiring_policies`, `get_missing_documents`, `get_premium_payment_history`, `generate_outreach_draft`).
  - Synthesizes answers strictly from real database records (never hallucinates policy details or balances).
  - Maintains multi-turn conversation sessions (`AgentConversation` & `AgentMessage`).
- **Python Tool Registry (`tool_registry.py` & `tools/database_tools.py`)**:
  - 10 reusable tools with strict type hints, input validation, and zero arbitrary SQL execution.

---

## Tool Registry Catalog (10 Database Tools)

| Tool Name | Parameters | Purpose |
| :--- | :--- | :--- |
| `search_customer_records` | `query, tier, risk_segment, limit` | Fuzzy search customers by name, code, or email |
| `get_customer_360_profile` | `customer_id_or_code` | Full dossier (policies, schedules, docs, claims, alerts) |
| `get_policy_compliance_status` | `policy_id_or_number` | Verified vs missing/rejected document checklist |
| `get_premium_payment_history` | `policy_id_or_number` | Invoices, overdue amounts, grace period cutoff, retry attempts |
| `get_active_attention_items` | `category, urgency_level, limit` | Prioritized unresolved Watchdog attention queue |
| `get_expiring_policies` | `within_days, limit` | Upcoming policy expirations with accurate days countdown |
| `get_missing_documents` | `status, limit` | Mandatory document deficits (Pending, Rejected, Expired) |
| `get_customer_followup_history`| `customer_id_or_code` | Audit trail of previous employee & AI actions |
| `investigate_customer_case` | `customer_id_or_code` | Compiles consolidated risk factors into a unified diagnostic |
| `generate_outreach_draft` | `customer_id_or_code, purpose, channel` | Generates email/SMS drafts referencing actual policy data |

---

## API Catalog

| Group | Method | Endpoint | Description |
| :--- | :---: | :--- | :--- |
| **AI Copilot** | `POST` | `/api/v1/copilot/chat` | Conversational turn with The Investigator (tool-calling copilot) |
| | `GET` | `/api/v1/copilot/conversations` | List active investigation sessions |
| | `GET` | `/api/v1/copilot/conversations/{id}`| Full conversation message history with tool executions |
| | `GET` | `/api/v1/copilot/tools` | Catalog of 10 available Python database tools |
| **Watchdog Sweep** | `POST` | `/api/v1/analysis/trigger` | Triggers on-demand autonomous Watchdog portfolio sweep |
| | `GET` | `/api/v1/analysis/runs` | Historical execution telemetry and sweep logs |
| | `GET` | `/api/v1/analysis/runs/latest` | Most recent AI sweep telemetry |
| **Attention Queue**| `GET` | `/api/v1/attention` | Multi-dimensional filtered attention queue |
| | `GET` | `/api/v1/attention/overview` | Categorical & urgency distribution, premium at risk |
| | `GET` | `/api/v1/attention/{id}` | Deep detail with customer, policy, and audit trail |
| | `PATCH`| `/api/v1/attention/{id}/status` | Lifecycle update (`OPEN`, `IN_PROGRESS`, `RESOLVED`, `DISMISSED`) |
| **Policy Expiry** | `GET` | `/api/v1/policies/expiring` | Expiry tracker (7, 15, 30, 60 days) |
| **Documents** | `GET` | `/api/v1/documents/missing` | Mandatory compliance deficits (Pending, Rejected, Expired) |
| **Billing** | `GET` | `/api/v1/billing/issues` | Overdue premiums, grace period tracking, failed debits |
| **Renewals** | `GET` | `/api/v1/renewals/follow-ups` | 60-day renewal pipeline with duplicate alert prevention |
| **Customer 360** | `GET` | `/api/v1/customers` | Directory with real-time active policies & alert counts |
| | `GET` | `/api/v1/customers/{id}` | Complete 360° customer profile |
| **Dashboard** | `GET` | `/api/v1/dashboard/metrics` | Dynamic executive KPIs (Zero hardcoding) |
| **System** | `GET` | `/api/v1/health` | System status, database health, configured Gemini models |

---

## Verification Test Suites

```bash
# Phase 1: Database models, relationships, and seed data verification
python test_verification.py

# Phase 2: Core business logic and query APIs verification
python test_phase2.py

# Phase 3: The Watchdog & The Investigator AI Agent subsystem verification
python test_phase3_agent.py
python test_regression_b1_b9.py
python test_phase5_workflow.py
python test_watchdog_autonomous.py
```

All 3 test suites pass with 100% success.
