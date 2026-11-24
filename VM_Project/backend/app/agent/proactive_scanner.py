"""The Watchdog: Orchestration Component for Autonomous AI Portfolio Investigation."""

import threading
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import func, select
from app.agent.intelligence_core import intelligence_core
from app.core.config import settings
from app.core.database import SyncSessionLocal
from app.core.logging import logger
from app.db.models import (
    Customer,
    CustomerAttentionItem,
    AgentAnalysisRun,
    ActivityAuditLog,
)


class ProactiveWatchdogScanner:
    """Orchestrates autonomous LLM-driven portfolio investigations with safety boundaries and coverage accounting."""

    def __init__(self):
        self.core = intelligence_core
        self._sweep_lock = threading.Lock()

    def run_sweep(
        self,
        trigger_source: str = "DASHBOARD_MANUAL",
        run_type: str = "PROACTIVE_SWEEP",
        max_iterations: int = 12,
        max_tool_calls: int = 40,
        timeout_seconds: float = 90.0,
        investigation_objective: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Orchestrates an autonomous Watchdog investigation with concurrency protection."""
        if not self._sweep_lock.acquire(blocking=False):
            logger.warning("Watchdog investigation already in progress; rejecting concurrent trigger.")
            return {
                "status": "ALREADY_RUNNING",
                "degraded_mode": False,
                "summary": "An autonomous Watchdog investigation is already running. Please wait for completion.",
            }

        try:
            return self._execute_sweep_locked(
                trigger_source=trigger_source,
                run_type=run_type,
                max_iterations=max_iterations,
                max_tool_calls=max_tool_calls,
                timeout_seconds=timeout_seconds,
                investigation_objective=investigation_objective,
            )
        finally:
            self._sweep_lock.release()

    def _execute_sweep_locked(
        self,
        trigger_source: str,
        run_type: str,
        max_iterations: int,
        max_tool_calls: int,
        timeout_seconds: float,
        investigation_objective: Optional[str],
    ) -> Dict[str, Any]:
        start_time = time.perf_counter()
        now_utc = datetime.now(timezone.utc)

        session = SyncSessionLocal()
        total_portfolio_customers = session.execute(select(func.count(Customer.id))).scalar() or 0

        run_record = AgentAnalysisRun(
            run_type=run_type,
            trigger_source=trigger_source,
            status="RUNNING",
            started_at=now_utc,
            records_scanned=0,
            model_used=settings.GEMINI_ANALYSIS_MODEL if self.core.gemini.is_live() else "unavailable",
        )
        session.add(run_record)
        session.commit()
        session.refresh(run_record)

        try:
            logger.info(f"Starting Autonomous Watchdog investigation [Run ID: {run_record.id}]...")

            outcome = self.core.run_autonomous_watchdog_investigation(
                max_iterations=max_iterations,
                max_tool_calls=max_tool_calls,
                timeout_seconds=timeout_seconds,
                investigation_objective=investigation_objective,
            )

            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            tool_calls_log: List[Dict[str, Any]] = outcome.get("tool_calls", [])
            iterations_used: int = outcome.get("iterations_used", 0)

            retrieved_ids = set(outcome.get("customers_retrieved_ids") or [])
            investigated_ids = set(outcome.get("customers_investigated_ids") or [])
            pagination_completed = bool(outcome.get("pagination_completed", False))

            customers_retrieved = len(retrieved_ids)
            customers_deeply_investigated = len(investigated_ids)
            customers_retrieved_not_investigated = len(retrieved_ids - investigated_ids)
            customers_skipped = max(0, total_portfolio_customers - customers_retrieved)
            coverage_complete = (
                pagination_completed
                and total_portfolio_customers > 0
                and customers_retrieved >= total_portfolio_customers
            )

            run_record.records_scanned = customers_retrieved
            run_record.iterations_used = iterations_used
            run_record.tool_calls_count = len(tool_calls_log)
            run_record.tool_calls_log = tool_calls_log
            run_record.execution_time_ms = elapsed_ms
            run_record.completed_at = datetime.now(timezone.utc)

            coverage_payload = {
                "total_portfolio_customers": total_portfolio_customers,
                "pagination_completed": pagination_completed,
                "customers_retrieved": customers_retrieved,
                "customers_deeply_investigated": customers_deeply_investigated,
                "customers_retrieved_not_investigated": customers_retrieved_not_investigated,
                "customers_skipped": customers_skipped,
                "coverage_complete": coverage_complete,
            }

            if outcome.get("status") == "DEGRADED":
                run_record.status = "DEGRADED"
                run_record.degraded_mode = True
                run_record.error_message = outcome.get("error")
                run_record.summary_notes = (
                    "Autonomous AI investigation unavailable (GEMINI_API_KEY not configured). "
                    "Existing attention items preserved. Retry once a live Gemini key is configured."
                )
                session.commit()
                return {
                    "run_id": run_record.id,
                    "status": "DEGRADED",
                    "degraded_mode": True,
                    "error": run_record.error_message,
                    "records_scanned": 0,
                    "issues_detected": 0,
                    "new_recommendations_created": 0,
                    "recommendations_updated": 0,
                    "iterations_used": iterations_used,
                    "tool_calls_count": len(tool_calls_log),
                    "execution_time_ms": elapsed_ms,
                    "model_used": run_record.model_used,
                    "coverage": coverage_payload,
                    "summary": run_record.summary_notes,
                }

            if outcome.get("status") == "FAILED":
                run_record.status = "FAILED"
                run_record.degraded_mode = False
                run_record.error_message = outcome.get("error")
                run_record.summary_notes = f"Autonomous investigation failed: {outcome.get('error')}"
                session.commit()
                return {
                    "run_id": run_record.id,
                    "status": "FAILED",
                    "degraded_mode": False,
                    "error": run_record.error_message,
                    "records_scanned": customers_retrieved,
                    "iterations_used": iterations_used,
                    "tool_calls_count": len(tool_calls_log),
                    "execution_time_ms": elapsed_ms,
                    "coverage": coverage_payload,
                }

            raw_recs: List[Dict[str, Any]] = outcome.get("recommendations", [])
            deduped_map: Dict[str, Dict[str, Any]] = {}
            for rec in raw_recs:
                dk = rec["dedup_key"]
                if dk not in deduped_map or rec["attention_score"] > deduped_map[dk]["attention_score"]:
                    deduped_map[dk] = rec
            all_recommendations = list(deduped_map.values())

            customers_flagged = len({rec["customer_id"] for rec in all_recommendations})
            coverage_payload["customers_flagged"] = customers_flagged

            new_created = 0
            existing_updated = 0
            skipped_closed = 0

            for rec in all_recommendations:
                dedup = rec["dedup_key"]

                active_stmt = select(CustomerAttentionItem).where(
                    CustomerAttentionItem.dedup_key == dedup,
                    CustomerAttentionItem.is_active == True,
                )
                existing_active = session.execute(active_stmt).scalars().first()

                if existing_active:
                    existing_active.attention_score = rec["attention_score"]
                    existing_active.urgency_level = rec["urgency_level"]
                    existing_active.confidence_level = rec["confidence_level"]
                    existing_active.title = rec["title"]
                    existing_active.reasoning_summary = rec["reasoning_summary"]
                    existing_active.root_cause = rec["root_cause"]
                    existing_active.ai_summary = rec["ai_summary"]
                    existing_active.ai_recommendation = rec["ai_recommendation"]
                    existing_active.identified_risk_factors = rec["identified_risk_factors"]
                    existing_active.investigation_steps = rec["investigation_steps"]
                    existing_active.supporting_evidence = rec["supporting_evidence"]
                    existing_active.data_gaps = rec["data_gaps"]
                    existing_active.suggested_action = rec["suggested_action"]
                    existing_updated += 1
                    continue

                closed_stmt = select(CustomerAttentionItem).where(
                    CustomerAttentionItem.dedup_key == dedup,
                    CustomerAttentionItem.is_active == False,
                    CustomerAttentionItem.status.in_(["RESOLVED", "DISMISSED"]),
                )
                if session.execute(closed_stmt).scalars().first():
                    skipped_closed += 1
                    continue

                item = CustomerAttentionItem(
                    customer_id=rec["customer_id"],
                    policy_id=rec.get("policy_id"),
                    category=rec["category"],
                    urgency_level=rec["urgency_level"],
                    attention_score=rec["attention_score"],
                    confidence_level=rec["confidence_level"],
                    dedup_key=dedup,
                    is_active=True,
                    title=rec["title"],
                    reasoning_summary=rec["reasoning_summary"],
                    root_cause=rec["root_cause"],
                    ai_summary=rec["ai_summary"],
                    ai_recommendation=rec["ai_recommendation"],
                    identified_risk_factors=rec["identified_risk_factors"],
                    investigation_steps=rec["investigation_steps"],
                    supporting_evidence=rec["supporting_evidence"],
                    data_gaps=rec["data_gaps"],
                    suggested_action=rec["suggested_action"],
                    status="OPEN",
                    detected_at=now_utc,
                )
                session.add(item)
                new_created += 1

                session.add(
                    ActivityAuditLog(
                        customer_id=rec["customer_id"],
                        action_type="ATTENTION_FLAGGED",
                        actor="SYSTEM_AI",
                        actor_name="The Watchdog Autonomous Agent",
                        description=f"Autonomous Watchdog flagged {rec['urgency_level']} alert: {rec['title']}",
                        metadata_payload={
                            "dedup_key": dedup,
                            "category": rec["category"],
                            "confidence": rec["confidence_level"],
                        },
                    )
                )

            coverage_label = "Full portfolio covered" if coverage_complete else "Partial portfolio coverage"
            run_record.status = "COMPLETED"
            run_record.degraded_mode = False
            run_record.issues_detected = len(all_recommendations)
            run_record.new_recommendations_created = new_created
            run_record.recommendations_updated = existing_updated
            run_record.summary_notes = (
                f"{coverage_label}: retrieved {customers_retrieved}/{total_portfolio_customers} customers "
                f"(deeply investigated {customers_deeply_investigated}, retrieved-only {customers_retrieved_not_investigated}, "
                f"skipped {customers_skipped}), flagged {customers_flagged} "
                f"({iterations_used} iterations, {len(tool_calls_log)} tool calls). "
                f"Results: {new_created} created, {existing_updated} updated, {skipped_closed} closed preserved."
            )

            session.commit()
            logger.info(run_record.summary_notes)

            return {
                "run_id": run_record.id,
                "status": "COMPLETED",
                "degraded_mode": False,
                "records_scanned": customers_retrieved,
                "issues_detected": len(all_recommendations),
                "new_recommendations_created": new_created,
                "recommendations_updated": existing_updated,
                "skipped_closed": skipped_closed,
                "iterations_used": iterations_used,
                "tool_calls_count": len(tool_calls_log),
                "execution_time_ms": elapsed_ms,
                "model_used": run_record.model_used,
                "coverage": coverage_payload,
                "summary": run_record.summary_notes,
            }

        except Exception as e:
            session.rollback()
            logger.error(f"Watchdog orchestration failed: {e}")
            elapsed_ms = round((time.perf_counter() - start_time) * 1000, 2)
            run_record.status = "FAILED"
            run_record.error_message = str(e)
            run_record.execution_time_ms = elapsed_ms
            run_record.completed_at = datetime.now(timezone.utc)
            session.commit()
            return {"run_id": run_record.id, "status": "FAILED", "degraded_mode": False, "error": str(e)}
        finally:
            session.close()


watchdog_scanner = ProactiveWatchdogScanner()
