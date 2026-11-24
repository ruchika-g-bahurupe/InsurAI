"""Central Intelligence Core shared by The Watchdog and The Investigator."""

from concurrent.futures import ThreadPoolExecutor, TimeoutError as FuturesTimeoutError
import json
import re
import time
from typing import Any, Dict, List, Optional, Set, Tuple
from google.genai import types
from app.agent.gemini_client import gemini_client
from app.agent.prompts.system_prompts import (
    WATCHDOG_SYSTEM_PROMPT,
    INVESTIGATOR_SYSTEM_PROMPT,
)
from app.agent.tool_registry import tool_registry
from app.core.logging import logger


class IntelligenceCore:
    """Unified AI Engine orchestrating autonomous Gemini investigation, tool dispatch, and validation."""

    def __init__(self):
        self.gemini = gemini_client
        self.registry = tool_registry

    # --------------------------------------------------------------------------
    # 1. Autonomous Watchdog Investigation Agent
    # --------------------------------------------------------------------------
    def run_autonomous_watchdog_investigation(
        self,
        max_iterations: int = 12,
        max_tool_calls: int = 40,
        timeout_seconds: float = 90.0,
        request_timeout_seconds: float = 30.0,
        investigation_objective: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Executes an iterative, LLM-driven autonomous portfolio investigation with:
        - Explicit DEGRADED mode when Gemini is unavailable
        - Request-level timeouts and non-blocking deadline shutdown on timeout
        - Iteration and total tool-call limits
        - Duplicate tool-call protection
        - Detailed portfolio coverage tracking (pagination, retrieved, investigated, uninvestigated)
        - Strict evidence-grounded output validation (no misleading defaults)
        """
        if not self.gemini.is_live() or not self.gemini.client:
            logger.warning("Autonomous Watchdog skipped: GEMINI_API_KEY is not configured (DEGRADED mode).")
            return {
                "status": "DEGRADED",
                "degraded_mode": True,
                "error": (
                    "Autonomous AI investigation is unavailable because GEMINI_API_KEY is not configured. "
                    "Existing attention items have been preserved. Configure GEMINI_API_KEY and retry."
                ),
                "recommendations": [],
                "tool_calls": [],
                "iterations_used": 0,
                "pagination_completed": False,
                "customers_retrieved_ids": [],
                "customers_investigated_ids": [],
            }

        start_time = time.perf_counter()
        deadline = start_time + timeout_seconds
        watchdog_tools = self.registry.get_watchdog_callables()
        allowed_names = self.registry.get_watchdog_tool_names()

        objective = investigation_objective or (
            "Conduct an autonomous investigation of the insurance customer portfolio. "
            "Start with `get_portfolio_overview`, paginate through customers using `list_customer_records(skip=..., limit=15)` "
            "to cover the portfolio in compact batches, and selectively inspect customers who show potential operational, "
            "financial, compliance, claim, or renewal risks. Conclude cleanly with a JSON array of validated attention items "
            "(or `[]` if no customers require attention)."
        )

        contents: List[Any] = [
            types.Content(role="user", parts=[types.Part.from_text(text=objective)])
        ]

        tool_calls_log: List[Dict[str, Any]] = []
        seen_calls: Set[Tuple[str, str]] = set()
        customers_retrieved_ids: Set[str] = set()
        customers_investigated_ids: Set[str] = set()
        pagination_completed = False
        iterations_used = 0
        total_executed_tools = 0

        deep_customer_tools = {
            "get_customer_360_profile",
            "get_customer_policies",
            "get_customer_payment_history",
            "get_customer_documents",
            "get_customer_claim_history",
            "get_customer_renewal_history",
            "get_customer_previous_attention",
            "investigate_customer_case",
        }

        def _remaining() -> float:
            return deadline - time.perf_counter()

        def _coverage_snapshot() -> Dict[str, Any]:
            return {
                "pagination_completed": pagination_completed,
                "customers_retrieved_ids": list(customers_retrieved_ids),
                "customers_investigated_ids": list(customers_investigated_ids),
            }

        executor = ThreadPoolExecutor(max_workers=2)
        timed_out = False
        try:
            for iteration in range(1, max_iterations + 1):
                rem = _remaining()
                if rem <= 0:
                    timed_out = True
                    return {
                        "status": "FAILED",
                        "degraded_mode": False,
                        "error": (
                            f"Execution deadline ({timeout_seconds}s) exceeded after {iterations_used} iterations; "
                            "investigation cancelled without waiting for background worker threads."
                        ),
                        "recommendations": [],
                        "tool_calls": tool_calls_log,
                        "iterations_used": iterations_used,
                        **_coverage_snapshot(),
                    }

                iterations_used = iteration
                req_timeout = min(request_timeout_seconds, max(0.5, rem))

                try:
                    future = executor.submit(
                        self.gemini.generate_with_tools,
                        system_instruction=WATCHDOG_SYSTEM_PROMPT,
                        contents=contents,
                        tools=watchdog_tools,
                        use_analysis_model=True,
                        timeout_seconds=req_timeout,
                    )
                    response = future.result(timeout=rem)
                except FuturesTimeoutError:
                    timed_out = True
                    return {
                        "status": "FAILED",
                        "degraded_mode": False,
                        "error": (
                            f"Gemini API request timed out against execution deadline ({timeout_seconds}s); "
                            "investigation aborted (in-flight worker thread could not be forcibly terminated)."
                        ),
                        "recommendations": [],
                        "tool_calls": tool_calls_log,
                        "iterations_used": iterations_used,
                        **_coverage_snapshot(),
                    }

                if not response:
                    err_detail = getattr(self.gemini, "last_error", None)
                    err_msg = (
                        f"Gemini API call failed during Watchdog investigation: {err_detail}"
                        if err_detail
                        else "Gemini API returned an empty or failed response during Watchdog investigation."
                    )
                    return {
                        "status": "FAILED",
                        "degraded_mode": False,
                        "error": err_msg,
                        "recommendations": [],
                        "tool_calls": tool_calls_log,
                        "iterations_used": iterations_used,
                        **_coverage_snapshot(),
                    }

                function_calls = getattr(response, "function_calls", None)
                if not function_calls and hasattr(response, "candidates") and response.candidates:
                    parts = response.candidates[0].content.parts or []
                    function_calls = [p.function_call for p in parts if getattr(p, "function_call", None)]

                if function_calls:
                    tool_response_parts = []
                    for call in function_calls:
                        if _remaining() <= 0:
                            timed_out = True
                            return {
                                "status": "FAILED",
                                "degraded_mode": False,
                                "error": f"Execution deadline ({timeout_seconds}s) exceeded during tool execution.",
                                "recommendations": [],
                                "tool_calls": tool_calls_log,
                                "iterations_used": iterations_used,
                                **_coverage_snapshot(),
                            }

                        t_name = getattr(call, "name", "")
                        raw_args = getattr(call, "args", None) or {}
                        t_args = dict(raw_args) if not isinstance(raw_args, dict) else raw_args
                        call_sig = (t_name, json.dumps(t_args, sort_keys=True, default=str))

                        if total_executed_tools >= max_tool_calls:
                            t_result: Dict[str, Any] = {
                                "warning": f"Tool execution limit ({max_tool_calls}) reached. Synthesize final JSON findings now."
                            }
                            status_tag = "LIMIT_REACHED"
                        elif call_sig in seen_calls:
                            t_result = {
                                "warning": (
                                    f"Duplicate tool call '{t_name}' with identical arguments skipped. "
                                    "Use previously retrieved results or investigate a different record."
                                )
                            }
                            status_tag = "DUPLICATE_SKIPPED"
                        elif t_name not in allowed_names:
                            t_result = {"error": f"Tool '{t_name}' is not an allowed read-only Watchdog tool."}
                            status_tag = "BLOCKED"
                        else:
                            seen_calls.add(call_sig)
                            total_executed_tools += 1
                            try:
                                tool_future = executor.submit(
                                    self.registry.execute_tool,
                                    t_name,
                                    t_args,
                                    allowed_tools=allowed_names,
                                )
                                t_result = tool_future.result(timeout=max(0.5, _remaining()))
                            except FuturesTimeoutError:
                                timed_out = True
                                return {
                                    "status": "FAILED",
                                    "degraded_mode": False,
                                    "error": (
                                        f"Tool '{t_name}' timed out against execution deadline ({timeout_seconds}s); "
                                        "investigation aborted (in-flight worker thread could not be forcibly terminated)."
                                    ),
                                    "recommendations": [],
                                    "tool_calls": tool_calls_log,
                                    "iterations_used": iterations_used,
                                    **_coverage_snapshot(),
                                }
                            status_tag = "ERROR" if "error" in t_result else "OK"

                            if t_name == "list_customer_records" and status_tag == "OK":
                                page_custs = t_result.get("customers", [])
                                for c in page_custs:
                                    if c.get("customer_id"):
                                        customers_retrieved_ids.add(c["customer_id"])
                                page_limit = t_result.get("limit", 15)
                                if len(page_custs) < page_limit:
                                    pagination_completed = True
                            elif t_name in deep_customer_tools and status_tag == "OK":
                                resolved_cid = t_result.get("customer_id") or (t_result.get("customer") or {}).get("customer_id")
                                if resolved_cid:
                                    customers_investigated_ids.add(resolved_cid)
                                    customers_retrieved_ids.add(resolved_cid)

                        tool_calls_log.append({
                            "iteration": iteration,
                            "name": t_name,
                            "args": t_args,
                            "status": status_tag,
                        })

                        tool_response_parts.append(
                            types.Part.from_function_response(name=t_name, response={"result": t_result})
                        )

                    if getattr(response, "candidates", None) and response.candidates[0].content:
                        contents.append(response.candidates[0].content)
                    contents.append(types.Content(role="user", parts=tool_response_parts))
                    continue

                raw_text = getattr(response, "text", None) or ""
                try:
                    recommendations = self._parse_and_validate_watchdog_output(raw_text)
                    return {
                        "status": "COMPLETED",
                        "degraded_mode": False,
                        "error": None,
                        "recommendations": recommendations,
                        "tool_calls": tool_calls_log,
                        "iterations_used": iterations_used,
                        **_coverage_snapshot(),
                    }
                except ValueError as ve:
                    logger.warning(f"Watchdog final output parse/validation error: {ve}")
                    return {
                        "status": "FAILED",
                        "degraded_mode": False,
                        "error": f"Invalid LLM response structure: {ve}",
                        "recommendations": [],
                        "tool_calls": tool_calls_log,
                        "iterations_used": iterations_used,
                        **_coverage_snapshot(),
                    }

            return {
                "status": "FAILED",
                "degraded_mode": False,
                "error": f"Watchdog reached max_iterations={max_iterations} without producing final recommendations.",
                "recommendations": [],
                "tool_calls": tool_calls_log,
                "iterations_used": iterations_used,
                **_coverage_snapshot(),
            }
        finally:
            executor.shutdown(wait=not timed_out, cancel_futures=timed_out)

    def _collect_verified_record_refs(
        self, profile: Dict[str, Any], payments: Dict[str, Any]
    ) -> Tuple[Set[str], Set[str]]:
        """
        Collects:
        1. Exact database record identifiers (customer_id, customer_code, policy_id, policy_number,
           document_id, document_name, claim_id, claim_number, schedule_id).
        2. Exact verified field values (dates, formatted/raw amounts).
        Excludes generic enum words like 'ACTIVE', 'STANDARD', 'HEALTH', 'VIP'.
        """
        exact_ids: Set[str] = set()
        verified_values: Set[str] = set()

        for key in ("customer_id", "customer_code"):
            if profile.get(key):
                exact_ids.add(str(profile[key]).lower())

        for p in profile.get("policies", []):
            for k in ("policy_id", "policy_number"):
                if p.get(k):
                    exact_ids.add(str(p[k]).lower())
            if p.get("expiry_date"):
                verified_values.add(str(p["expiry_date"]).lower())
            if p.get("premium_amount") is not None:
                amt = float(p["premium_amount"])
                verified_values.add(f"${amt:,.2f}".lower())
                verified_values.add(f"{amt:.2f}".lower())

        for d in profile.get("documents", []):
            for k in ("document_id", "document_name"):
                if d.get(k):
                    exact_ids.add(str(d[k]).lower())

        for cl in profile.get("claims", []):
            for k in ("claim_id", "claim_number"):
                if cl.get(k):
                    exact_ids.add(str(cl[k]).lower())
            if cl.get("amount") is not None:
                amt = float(cl["amount"])
                verified_values.add(f"${amt:,.2f}".lower())

        for sched in payments.get("payment_schedules", []):
            if sched.get("schedule_id"):
                exact_ids.add(str(sched["schedule_id"]).lower())
            if sched.get("due_date"):
                verified_values.add(str(sched["due_date"]).lower())
            if sched.get("amount_due") is not None:
                amt = float(sched["amount_due"])
                verified_values.add(f"${amt:,.2f}".lower())
                verified_values.add(f"{amt:.2f}".lower())

        return exact_ids, verified_values

    def _parse_and_validate_watchdog_output(self, raw_text: str) -> List[Dict[str, Any]]:
        """
        Strictly parses and validates the LLM's JSON array output.
        Rejects any recommendation missing required AI fields or lacking exact DB record references.
        Never supplies misleading defaults for confidence, reasoning, steps, or suggested_action.
        """
        if not raw_text or not raw_text.strip():
            raise ValueError("Empty response text from model.")

        cleaned = re.sub(r"^```(?:json)?\s*", "", raw_text.strip())
        cleaned = re.sub(r"\s*```$", "", cleaned)

        try:
            parsed = json.loads(cleaned)
        except json.JSONDecodeError as je:
            raise ValueError(f"Response is not valid JSON: {je}") from je

        if not isinstance(parsed, list):
            raise ValueError("Top-level JSON output must be a list of attention recommendations.")

        valid_categories = {
            "POLICY_EXPIRY",
            "MISSING_DOCS",
            "PREMIUM_OVERDUE",
            "RENEWAL_FOLLOWUP",
            "RISK_ALERT",
        }
        valid_urgencies = {"CRITICAL", "HIGH", "MEDIUM", "LOW"}
        valid_confidences = {"HIGH", "MEDIUM", "LOW"}

        sanitized: List[Dict[str, Any]] = []
        for idx, item in enumerate(parsed):
            if not isinstance(item, dict):
                logger.warning(f"Watchdog validation rejected item[{idx}]: not an object.")
                continue

            # 1. Customer existence
            cust_ref = item.get("customer_id")
            if not cust_ref or not isinstance(cust_ref, str):
                logger.warning(f"Watchdog validation rejected item[{idx}]: missing customer_id.")
                continue

            profile = self.registry.execute_tool("get_customer_360_profile", {"customer_id_or_code": cust_ref})
            if "error" in profile or not profile.get("customer_id"):
                logger.warning(f"Watchdog validation rejected item[{idx}]: unknown customer '{cust_ref}'.")
                continue

            real_customer_id = profile["customer_id"]
            payments = self.registry.execute_tool("get_customer_payment_history", {"customer_id": real_customer_id})

            # 2. Policy ownership
            raw_policy_id = item.get("policy_id")
            verified_policy_id: Optional[str] = None
            if raw_policy_id is not None and raw_policy_id != "":
                cust_policies = profile.get("policies", [])
                by_id = {p["policy_id"]: p["policy_id"] for p in cust_policies}
                by_num = {p["policy_number"]: p["policy_id"] for p in cust_policies}
                if raw_policy_id in by_id:
                    verified_policy_id = by_id[raw_policy_id]
                elif raw_policy_id in by_num:
                    verified_policy_id = by_num[raw_policy_id]
                else:
                    logger.warning(
                        f"Watchdog validation rejected item[{idx}]: policy '{raw_policy_id}' does not belong to customer '{real_customer_id}'."
                    )
                    continue

            # 3. Required enum fields (no silent defaults)
            category = str(item.get("category") or "").upper()
            if category not in valid_categories:
                logger.warning(f"Watchdog validation rejected item[{idx}]: invalid category '{item.get('category')}'.")
                continue

            urgency = str(item.get("urgency_level") or "").upper()
            if urgency not in valid_urgencies:
                logger.warning(f"Watchdog validation rejected item[{idx}]: invalid urgency_level '{item.get('urgency_level')}'.")
                continue

            confidence = str(item.get("confidence_level") or "").upper()
            if confidence not in valid_confidences:
                logger.warning(f"Watchdog validation rejected item[{idx}]: missing or invalid confidence_level '{item.get('confidence_level')}'.")
                continue

            # 4. Numeric score range
            if item.get("attention_score") is None or isinstance(item.get("attention_score"), bool):
                logger.warning(f"Watchdog validation rejected item[{idx}]: missing attention_score.")
                continue
            try:
                score = float(item["attention_score"])
            except (TypeError, ValueError):
                logger.warning(f"Watchdog validation rejected item[{idx}]: non-numeric attention_score.")
                continue
            if not (0.0 <= score <= 100.0):
                logger.warning(f"Watchdog validation rejected item[{idx}]: attention_score {score} out of [0, 100].")
                continue

            # 5. Required non-empty narrative & decision fields (no silent fallback)
            title = str(item.get("title") or "").strip()
            reasoning_summary = str(item.get("reasoning_summary") or "").strip()
            root_cause = str(item.get("root_cause") or "").strip()
            ai_summary = str(item.get("ai_summary") or "").strip()
            ai_recommendation = str(item.get("ai_recommendation") or "").strip()
            if not all([title, reasoning_summary, root_cause, ai_summary, ai_recommendation]):
                logger.warning(f"Watchdog validation rejected item[{idx}]: missing required narrative/decision fields.")
                continue

            # 6. Required structured lists & suggested_action
            risk_factors = item.get("identified_risk_factors")
            investigation_steps = item.get("investigation_steps")
            suggested_action = item.get("suggested_action")
            if (
                not isinstance(risk_factors, list)
                or not [str(x).strip() for x in risk_factors if str(x).strip()]
                or not isinstance(investigation_steps, list)
                or not [str(x).strip() for x in investigation_steps if str(x).strip()]
                or not isinstance(suggested_action, dict)
                or not str(suggested_action.get("action_type") or "").strip()
            ):
                logger.warning(
                    f"Watchdog validation rejected item[{idx}]: missing identified_risk_factors, investigation_steps, or suggested_action.action_type."
                )
                continue

            # 7. Supporting evidence grounded in exact DB record IDs & verified field values
            evidence = item.get("supporting_evidence")
            if not isinstance(evidence, list) or len(evidence) == 0:
                logger.warning(f"Watchdog validation rejected item[{idx}]: missing supporting_evidence.")
                continue
            evidence_strs = [str(e).strip() for e in evidence if str(e).strip()]
            if not evidence_strs:
                logger.warning(f"Watchdog validation rejected item[{idx}]: empty supporting_evidence.")
                continue

            exact_ids, verified_values = self._collect_verified_record_refs(profile, payments)
            evidence_blob = " ".join(evidence_strs).lower()
            has_exact_id = any(eid in evidence_blob for eid in exact_ids)
            if not has_exact_id:
                logger.warning(
                    f"Watchdog validation rejected item[{idx}]: supporting_evidence lacks any exact DB record ID/code/number for customer '{real_customer_id}'."
                )
                continue

            # If policy_id was specified, verify at least one evidence item or verified value relates to customer records
            if verified_policy_id:
                pol_obj = next((p for p in profile.get("policies", []) if p["policy_id"] == verified_policy_id), None)
                if pol_obj:
                    pol_refs = {pol_obj["policy_id"].lower(), pol_obj["policy_number"].lower()}
                    if not any(pr in evidence_blob for pr in pol_refs):
                        logger.warning(
                            f"Watchdog validation rejected item[{idx}]: policy_id '{verified_policy_id}' specified but not referenced in supporting_evidence."
                        )
                        continue

            # 8. Stable dedup_key
            dedup_key = str(item.get("dedup_key") or "").strip()
            if not dedup_key or re.search(r"_\d+D$", dedup_key):
                logger.warning(f"Watchdog validation rejected item[{idx}]: missing or volatile dedup_key '{dedup_key}'.")
                continue

            raw_gaps = item.get("data_gaps")
            if raw_gaps is None:
                data_gaps: List[str] = []
            elif isinstance(raw_gaps, list):
                data_gaps = [str(g).strip() for g in raw_gaps if str(g).strip()]
            else:
                logger.warning(f"Watchdog validation rejected item[{idx}]: data_gaps must be a list.")
                continue

            sanitized.append({
                "customer_id": real_customer_id,
                "policy_id": verified_policy_id,
                "category": category,
                "urgency_level": urgency,
                "attention_score": round(score, 2),
                "confidence_level": confidence,
                "title": title[:160],
                "reasoning_summary": reasoning_summary,
                "root_cause": root_cause[:255],
                "ai_summary": ai_summary,
                "ai_recommendation": ai_recommendation,
                "identified_risk_factors": [str(x).strip() for x in risk_factors if str(x).strip()],
                "investigation_steps": [str(x).strip() for x in investigation_steps if str(x).strip()],
                "supporting_evidence": evidence_strs,
                "data_gaps": data_gaps,
                "suggested_action": suggested_action,
                "dedup_key": dedup_key[:150],
            })

        return sanitized

    # --------------------------------------------------------------------------
    # 2. Conversational Investigator Copilot Intelligence (Preserved)
    # --------------------------------------------------------------------------
    def chat_investigate(
        self,
        messages: List[Dict[str, Any]],
        active_customer_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Executes a turn of conversational customer investigation."""
        user_message = ""
        for m in reversed(messages):
            if m.get("sender", "").upper() == "USER" or m.get("role") == "user":
                user_message = m.get("content", "")
                break

        if not user_message:
            return {
                "reply": "How can I assist your customer investigation today?",
                "tool_calls": [],
                "tool_results": [],
                "mode": "IDLE",
            }

        if self.gemini.is_live():
            try:
                result = self._gemini_function_calling_turn(messages, active_customer_id)
                if result:
                    return result
            except Exception as e:
                logger.error(f"Live Gemini function calling encountered error: {e}. Falling back to Cognitive Core.")

        return self._cognitive_tool_dispatch(user_message, active_customer_id)

    def _gemini_function_calling_turn(
        self, messages: List[Dict[str, Any]], active_customer_id: Optional[str]
    ) -> Optional[Dict[str, Any]]:
        """Orchestrates native multi-step Gemini function calling with active_customer_id context."""
        all_callables = self.registry.get_all_callables()

        system_prompt = INVESTIGATOR_SYSTEM_PROMPT
        if active_customer_id:
            system_prompt += (
                f"\n\nACTIVE CUSTOMER CONTEXT: The employee is currently inspecting customer "
                f"identifier '{active_customer_id}'. If the employee refers to 'this customer' or omits a name, "
                f"investigate '{active_customer_id}' using the tools."
            )

        formatted_contents: List[Any] = []
        for m in messages:
            role = "user" if m.get("sender", "").upper() == "USER" else "model"
            content = m.get("content", "")
            formatted_contents.append(types.Content(role=role, parts=[types.Part.from_text(text=content)]))

        tool_calls_executed: List[Dict[str, Any]] = []
        tool_results_executed: List[Dict[str, Any]] = []

        current_contents = list(formatted_contents)
        max_rounds = 5

        for _ in range(max_rounds):
            response = self.gemini.generate_with_tools(
                system_instruction=system_prompt,
                contents=current_contents,
                tools=all_callables,
            )
            if not response:
                return None

            function_calls = getattr(response, "function_calls", None)
            if not function_calls and hasattr(response, "candidates") and response.candidates:
                parts = response.candidates[0].content.parts or []
                function_calls = [p.function_call for p in parts if getattr(p, "function_call", None)]

            if not function_calls:
                return {
                    "reply": response.text or "Investigation completed.",
                    "tool_calls": tool_calls_executed,
                    "tool_results": tool_results_executed,
                    "mode": "LIVE_GEMINI",
                }

            tool_response_parts = []
            for call in function_calls:
                t_name = call.name
                raw_args = getattr(call, "args", None) or {}
                t_args = dict(raw_args) if not isinstance(raw_args, dict) else raw_args
                t_result = self.registry.execute_tool(t_name, t_args)

                tool_calls_executed.append({"name": t_name, "args": t_args})
                tool_results_executed.append({"name": t_name, "result": t_result})

                tool_response_parts.append(
                    types.Part.from_function_response(name=t_name, response={"result": t_result})
                )

            if getattr(response, "candidates", None) and response.candidates[0].content:
                current_contents.append(response.candidates[0].content)
            current_contents.append(types.Content(role="user", parts=tool_response_parts))

        return {
            "reply": "Investigation completed based on retrieved database records.",
            "tool_calls": tool_calls_executed,
            "tool_results": tool_results_executed,
            "mode": "LIVE_GEMINI",
        }

    def _extract_customer_candidates(self, query: str, active_customer_id: Optional[str]) -> List[str]:
        """Dynamically extracts customer codes or name terms from natural language queries."""
        candidates: List[str] = []

        for code in re.findall(r"\b(cust-\d+)\b", query, flags=re.IGNORECASE):
            if code.upper() not in candidates:
                candidates.append(code.upper())

        if candidates:
            return candidates

        cmp_match = re.search(
            r"(?:compare|between)\s+([a-zA-Z0-9\s'-]+?)\s+(?:and|vs\.?|with)\s+([a-zA-Z0-9\s'-]+)",
            query,
            flags=re.IGNORECASE,
        )
        if cmp_match:
            for grp in (cmp_match.group(1), cmp_match.group(2)):
                cleaned = re.sub(r"^(?:customer|client)\s+", "", grp.strip(), flags=re.IGNORECASE)
                cleaned = re.sub(r"('s|\s+profile|\s+risk|\s+policies).*", "", cleaned, flags=re.IGNORECASE).strip()
                if cleaned:
                    candidates.append(cleaned)
            if candidates:
                return candidates

        phrase_patterns = [
            r"(?:investigate|profile of|profile for|about|draft.*for|outreach.*for|follow[- ]?up.*for|history.*for|check)\s+(?:customer\s+)?([a-zA-Z0-9\s'-]+)",
            r"why\s+is\s+([a-zA-Z0-9\s'-]+?)\s+(?:high|critical|flagged|at risk|priority)",
        ]
        for pat in phrase_patterns:
            m = re.search(pat, query, flags=re.IGNORECASE)
            if m:
                cand = m.group(1).strip()
                cand = re.sub(r"('s|\s+full|\s+profile|\s+case|\s+why|\s+flagged|\s+and\s+.*).*", "", cand, flags=re.IGNORECASE).strip()
                if cand and cand.lower() not in {"a customer", "the customer", "this customer", "case", "profile", "policies", "me"}:
                    candidates.append(cand)
                    return candidates

        stop_words = {
            "Show", "Tell", "Compare", "Investigate", "Draft", "Check", "List", "What", "Why",
            "Which", "How", "Customer", "Policy", "Policies", "Email", "SMS", "High", "Critical",
            "Overdue", "Missing", "Documents", "Compliance", "Payment", "Renewal", "The", "Me",
        }
        proper_nouns = re.findall(r"\b([A-Z][a-z]{2,}(?:\s+[A-Z][a-z]{2,})?)\b", query)
        for pn in proper_nouns:
            if pn not in stop_words and pn.split()[0] not in stop_words:
                candidates.append(pn)

        if not candidates and active_customer_id:
            candidates.append(active_customer_id)

        return candidates

    def _cognitive_tool_dispatch(
        self, query: str, active_customer_id: Optional[str] = None
    ) -> Dict[str, Any]:
        """Deterministic, natural language intent-to-tool mapper for Investigator Copilot."""
        q = query.lower()
        tool_calls: List[Dict[str, Any]] = []
        tool_results: List[Dict[str, Any]] = []
        reply_parts: List[str] = []

        def run_tool(name: str, args: Dict[str, Any]) -> Dict[str, Any]:
            res = self.registry.execute_tool(name, args)
            tool_calls.append({"name": name, "args": args})
            tool_results.append({"name": name, "result": res})
            return res

        if any(k in q for k in ["draft", "outreach", "email", "sms", "message to"]):
            cands = self._extract_customer_candidates(query, active_customer_id)
            if cands:
                s_res = run_tool("search_customer_records", {"query": cands[0], "limit": 1})
                custs = s_res.get("customers", [])
                if custs:
                    c = custs[0]
                    purpose = "RENEWAL_OFFER"
                    if "doc" in q or "kyc" in q or "compliance" in q:
                        purpose = "MISSING_KYC_REQUEST"
                    elif "pay" in q or "overdue" in q or "grace" in q or "billing" in q:
                        purpose = "PAYMENT_GRACE_REMINDER"
                    channel = "SMS" if "sms" in q else "EMAIL"
                    draft = run_tool(
                        "generate_outreach_draft",
                        {"customer_id_or_code": c["customer_code"], "purpose": purpose, "channel": channel},
                    )
                    reply_parts.append(f"### Draft {draft.get('channel', channel)} Outreach for {c['full_name']} ({c['customer_code']})\n")
                    reply_parts.append(f"**Subject:** {draft.get('subject', 'N/A')}")
                    reply_parts.append(f"**Recipient:** `{draft.get('customer_email', c['email'])}` | `{draft.get('customer_phone', c['phone'])}`\n")
                    reply_parts.append(draft.get("body", ""))
                    reply_parts.append("\n*Requires employee approval before sending.*")
                else:
                    reply_parts.append(f"No customer records found matching '{cands[0]}'.")
            else:
                reply_parts.append("Please specify a customer name or code (e.g. `CUST-1005`) to draft outreach.")

        elif any(k in q for k in ["coverage", "covered", "exclusion", "clause", "guideline", "underwriting", "terms and conditions", "procedure", "accidental damage", "policy wording", "knowledge base"]):
            cands = self._extract_customer_candidates(query, active_customer_id)
            if cands:
                s_res = run_tool("search_customer_records", {"query": cands[0], "limit": 1})
                custs = s_res.get("customers", [])
                if custs:
                    c = custs[0]
                    pol_res = run_tool("get_customer_policies", {"customer_id": c["id"]})
                    reply_parts.append(f"### Customer Policy Context: {c['full_name']} ({c['customer_code']})\n")
                    for p in pol_res.get("policies", []):
                        reply_parts.append(f"- Policy `{p['policy_number']}` ({p['policy_type']} - {p['plan_name']}): **{p['status']}**")
                    reply_parts.append("")
            rag_res = run_tool("search_insurance_documents", {"query": query, "top_k": 5})
            passages = rag_res.get("passages", [])
            if passages:
                reply_parts.append(f"### Insurance Knowledge Base Evidence ({len(passages)} Passages)\n")
                for p in passages:
                    reply_parts.append(
                        f"- **[{p['document_name']}, Page {p['page_number']}]** ({p['category']})\n"
                        f"  > {p['relevant_excerpt'][:350]}"
                    )
                reply_parts.append("\n*Note: Final coverage or claim decisions require authorized employee/adjuster review.*")
            else:
                reply_parts.append(rag_res.get("message") or rag_res.get("error") or "No relevant policy or guideline passages found in the Knowledge Base.")

        elif "follow" in q or "history" in q or "audit" in q:
            cands = self._extract_customer_candidates(query, active_customer_id)
            if cands:
                s_res = run_tool("search_customer_records", {"query": cands[0], "limit": 1})
                custs = s_res.get("customers", [])
                if custs:
                    c = custs[0]
                    hist = run_tool("get_customer_followup_history", {"customer_id_or_code": c["customer_code"]})
                    entries = hist.get("followup_history", [])
                    reply_parts.append(f"### Follow-up & Audit History: {c['full_name']} ({c['customer_code']})\n")
                    if entries:
                        for e in entries[:8]:
                            reply_parts.append(f"- **{e['action_type']}** by {e['actor_name']} ({e['timestamp'][:10]}): {e['description']}")
                    else:
                        reply_parts.append("No historical follow-up actions recorded for this customer.")
                else:
                    reply_parts.append(f"No customer records found matching '{cands[0]}'.")
            else:
                reply_parts.append("Please specify a customer name or code to view follow-up history.")

        elif re.search(r"\bPOL-[A-Z]+-\d+\b", query, flags=re.IGNORECASE):
            pol_num = re.search(r"\b(POL-[A-Z]+-\d+)\b", query, flags=re.IGNORECASE).group(1).upper()
            if "pay" in q or "premium" in q or "billing" in q or "overdue" in q:
                res = run_tool("get_premium_payment_history", {"policy_id_or_number": pol_num})
                if "error" in res:
                    reply_parts.append(res["error"])
                else:
                    reply_parts.append(f"### Premium Payment History: {res['policy_number']} ({res['customer_name']})\n")
                    reply_parts.append(f"- **Annual Premium:** ${res['premium_amount']:,.2f} | **Total Overdue:** ${res['total_overdue_amount']:,.2f}\n")
                    for s in res.get("schedules", []):
                        reply_parts.append(f"- Installment #{s['installment_number']}: **${s['amount_due']:,.2f}** due `{s['due_date']}` [{s['status']}] (Retries: {s['retry_attempts']})")
            else:
                res = run_tool("get_policy_compliance_status", {"policy_id_or_number": pol_num})
                if "error" in res:
                    reply_parts.append(res["error"])
                else:
                    reply_parts.append(f"### Compliance Status: {res['policy_number']} ({res['customer_name']})\n")
                    reply_parts.append(f"- **Fully Compliant:** {'Yes' if res['is_fully_compliant'] else 'No'}\n")
                    for d in res.get("documents", []):
                        reply_parts.append(f"- **{d['document_type']}** (`{d['document_name']}`): [{d['status']}]")

        elif "immediate attention" in q or "urgent" in q or "high priority" in q or "require attention" in q or "critical" in q:
            urgency = "CRITICAL" if ("critical" in q or "immediate" in q) else None
            res = run_tool("get_active_attention_items", {"urgency_level": urgency, "limit": 5})
            alerts = res.get("alerts", [])
            if alerts:
                reply_parts.append(f"### High-Priority Cases Requiring Immediate Attention ({len(alerts)} Found)\n")
                for a in alerts:
                    reply_parts.append(
                        f"- **{a['customer_name']}** ({a['customer_code']}) - **Score: {a['attention_score']}** [{a['urgency_level']}]\n"
                        f"  * **Issue**: {a['title']}\n"
                        f"  * **Root Cause**: {a['root_cause']}\n"
                        f"  * **Recommendation**: {a['ai_recommendation']}\n"
                    )
            else:
                reply_parts.append("No unresolved critical attention items currently found in the queue.")

        elif "expir" in q or "laps" in q:
            days = 15
            match = re.search(r"(\d+)\s*days?", q)
            if match:
                days = int(match.group(1))
            res = run_tool("get_expiring_policies", {"within_days": days, "limit": 6})
            policies = res.get("policies", [])
            reply_parts.append(f"### Policies Expiring within {days} Days ({len(policies)} Found)\n")
            if policies:
                for p in policies:
                    reply_parts.append(
                        f"- **Policy #{p['policy_number']}** ({p['plan_name']})\n"
                        f"  * Policyholder: **{p['customer_name']}** ({p['customer_code']}, {p['customer_tier']})\n"
                        f"  * Expiry Date: `{p['expiry_date']}` (**{p['days_remaining']} days remaining**)\n"
                        f"  * Premium: **${p['premium_amount']:,.2f}** | Renewal Likelihood: {int(p['renewal_probability'] * 100)}%\n"
                    )
            else:
                reply_parts.append(f"No active policies are scheduled to expire within the next {days} days.")

        elif "missing doc" in q or "document" in q or "kyc" in q or "compliance" in q:
            status = "REJECTED" if "rejected" in q else None
            res = run_tool("get_missing_documents", {"status": status, "limit": 6})
            docs = res.get("documents", [])
            reply_parts.append(f"### Mandatory Document Compliance Deficits ({len(docs)} Found)\n")
            if docs:
                for d in docs:
                    reason = f" (Reason: {d['rejection_reason']})" if d.get("rejection_reason") else ""
                    reply_parts.append(
                        f"- **{d['customer_name']}** ({d['customer_code']}) - **{d['document_type']}** [{d['status']}]{reason}\n"
                        f"  * Policy: #{d['policy_number']} | Document File: `{d['document_name']}`\n"
                    )
            else:
                reply_parts.append("All customer policies currently satisfy statutory document compliance requirements.")

        elif "overdue" in q or "premium" in q or "grace period" in q or "unpaid" in q or "billing" in q:
            res = run_tool("get_active_attention_items", {"category": "PREMIUM_OVERDUE", "limit": 5})
            alerts = res.get("alerts", [])
            reply_parts.append(f"### Premium & Grace Period Issues ({len(alerts)} Found)\n")
            if alerts:
                for a in alerts:
                    reply_parts.append(
                        f"- **{a['customer_name']}** ({a['customer_code']}) - Policy #{a['policy_number']}\n"
                        f"  * **Alert**: {a['title']}\n"
                        f"  * **Diagnostic**: {a['root_cause']}\n"
                        f"  * **Recommended Action**: {a['ai_recommendation']}\n"
                    )
            else:
                reply_parts.append("No active overdue premium alerts found in the database.")

        elif any(k in q for k in ["investigate", "profile", "tell me about", "why", "compare", "cust-"]) or active_customer_id:
            cands = self._extract_customer_candidates(query, active_customer_id)
            if not cands:
                reply_parts.append("Please specify the customer name or code (e.g. 'CUST-1005') to investigate.")
            elif len(cands) >= 2 and "compare" in q:
                reply_parts.append("### Comparative Customer Risk Analysis\n")
                for cand in cands[:2]:
                    s_res = run_tool("search_customer_records", {"query": cand, "limit": 1})
                    custs = s_res.get("customers", [])
                    if not custs:
                        reply_parts.append(f"- No customer found matching '{cand}'.")
                        continue
                    c = custs[0]
                    d_res = run_tool("investigate_customer_case", {"customer_id_or_code": c["customer_code"]})
                    reply_parts.append(
                        f"**{c['full_name']} ({c['customer_code']})** — Tier: {c['tier']} | Risk: {c['risk_segment']} | "
                        f"CLV: ${c['total_clv']:,.2f} | Policies: {len(d_res.get('policies', []))} | Active Alerts: {d_res.get('active_attention_count', 0)}"
                    )
                    reply_parts.append("")
            else:
                name_term = cands[0]
                s_res = run_tool("search_customer_records", {"query": name_term, "limit": 1})
                custs = s_res.get("customers", [])
                if custs:
                    c = custs[0]
                    d_res = run_tool("investigate_customer_case", {"customer_id_or_code": c["customer_code"]})
                    reply_parts.append(f"### Intelligence Dossier: {c['full_name']} ({c['customer_code']})\n")
                    reply_parts.append(f"- **Tier**: {c['tier']} | **Risk Segment**: {c['risk_segment']} | **CLV**: ${c['total_clv']:,.2f}")
                    reply_parts.append(f"- **Assigned Agent**: {c['assigned_agent']} | **Location**: {c['city']}, {c['state']}\n")
                    policies = d_res.get("policies", [])
                    if policies:
                        reply_parts.append("**Policies:**")
                        for p in policies:
                            reply_parts.append(f"- Policy `{p['policy_number']}` ({p['policy_type']}): {p['status']}, expires `{p['expiry_date']}` ({p['days_to_expiry']} days)")
                        reply_parts.append("")
                    att = [a for a in d_res.get("attention_history", []) if a.get("is_active")]
                    if att:
                        reply_parts.append("**Active Watchdog Attention Alerts:**")
                        for a in att:
                            reply_parts.append(f"- **[{a['urgency_level']}] {a['title']}** (Score: {a['attention_score']})")
                            reply_parts.append(f"  * Root Cause: {a['root_cause']}")
                        reply_parts.append("")
                    reply_parts.append(
                        f"**Recommended Action**: Initiate outbound follow-up via `{c['email']}` or `{c['phone']}`."
                    )
                else:
                    reply_parts.append(f"No customer records found matching query '{name_term}'.")
        else:
            cands = self._extract_customer_candidates(query, active_customer_id)
            if cands:
                s_res = run_tool("search_customer_records", {"query": cands[0], "limit": 1})
                custs = s_res.get("customers", [])
                if custs:
                    c = custs[0]
                    d_res = run_tool("investigate_customer_case", {"customer_id_or_code": c["customer_code"]})
                    reply_parts.append(f"### Intelligence Dossier: {c['full_name']} ({c['customer_code']})\n")
                    reply_parts.append(f"- **Tier**: {c['tier']} | **Risk Segment**: {c['risk_segment']} | **CLV**: ${c['total_clv']:,.2f}")
                    for a in [x for x in d_res.get("attention_history", []) if x.get("is_active")]:
                        reply_parts.append(f"- **[{a['urgency_level']}] {a['title']}** (Score: {a['attention_score']})")
                    return {
                        "reply": "\n".join(reply_parts),
                        "tool_calls": tool_calls,
                        "tool_results": tool_results,
                        "mode": "COGNITIVE_CORE",
                    }
            res = run_tool("get_active_attention_items", {"limit": 3})
            reply_parts.append("I have retrieved the latest customer attention items from our database:\n")
            for a in res.get("alerts", []):
                reply_parts.append(f"- **{a['customer_name']}** ({a['customer_code']}): {a['title']} [{a['urgency_level']}]")

        return {
            "reply": "\n".join(reply_parts),
            "tool_calls": tool_calls,
            "tool_results": tool_results,
            "mode": "COGNITIVE_CORE",
        }


intelligence_core = IntelligenceCore()
