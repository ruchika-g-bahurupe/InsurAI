"""Centralized Tool Registry for the Unified AI Intelligence Core."""

import inspect
from typing import Any, Callable, Dict, List, Optional
from app.core.logging import logger
from app.agent.tools.database_tools import (
    search_customer_records,
    get_customer_360_profile,
    get_policy_compliance_status,
    get_premium_payment_history,
    get_active_attention_items,
    get_expiring_policies,
    get_missing_documents,
    get_customer_followup_history,
    investigate_customer_case,
    generate_outreach_draft,
    get_portfolio_overview,
    list_customer_records,
    get_customer_policies,
    get_customer_payment_history,
    get_customer_documents,
    get_customer_claim_history,
    get_customer_renewal_history,
    get_customer_previous_attention,
)
from app.agent.tools.rag_tools import search_insurance_documents


class ToolRegistry:
    """Registry managing available tools for both Watchdog and Investigator."""

    def __init__(self):
        self._tools: Dict[str, Callable[..., Any]] = {}
        self._watchdog_tool_names: List[str] = [
            "get_portfolio_overview",
            "list_customer_records",
            "get_customer_360_profile",
            "get_customer_policies",
            "get_customer_payment_history",
            "get_customer_documents",
            "get_customer_claim_history",
            "get_customer_renewal_history",
            "get_customer_previous_attention",
            "investigate_customer_case",
        ]
        self._register_default_tools()

    def register(self, name: str, func: Callable[..., Any]) -> None:
        """Register a tool callable."""
        self._tools[name] = func

    def get_tool(self, name: str) -> Optional[Callable[..., Any]]:
        """Retrieve tool by name."""
        return self._tools.get(name)

    def get_all_callables(self) -> List[Callable[..., Any]]:
        """Returns list of all registered tool functions for Investigator Copilot."""
        return list(self._tools.values())

    def get_watchdog_callables(self) -> List[Callable[..., Any]]:
        """Returns strictly read-only portfolio investigation tools for The Watchdog."""
        return [self._tools[name] for name in self._watchdog_tool_names if name in self._tools]

    def get_watchdog_tool_names(self) -> List[str]:
        """Returns names of read-only Watchdog tools."""
        return list(self._watchdog_tool_names)

    def get_tool_metadata(self) -> List[Dict[str, Any]]:
        """Returns human-readable metadata for all registered tools."""
        meta = []
        for name, func in self._tools.items():
            doc = inspect.getdoc(func) or ""
            sig = str(inspect.signature(func))
            meta.append({
                "name": name,
                "signature": sig,
                "description": doc.split("\n\n")[0] if "\n\n" in doc else doc,
            })
        return meta

    def execute_tool(
        self,
        name: str,
        args: Dict[str, Any],
        allowed_tools: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        """Safely executes a registered tool (optionally scoped to allowed_tools) and returns structured output."""
        if allowed_tools is not None and name not in allowed_tools:
            logger.warning(f"Tool '{name}' blocked by scope restriction.")
            return {"error": f"Tool '{name}' is not permitted in this agent context."}

        func = self._tools.get(name)
        if not func:
            logger.warning(f"Tool '{name}' requested but not found in ToolRegistry.")
            return {"error": f"Tool '{name}' does not exist in registry."}

        try:
            logger.info(f"Executing tool '{name}' with args: {args}")
            result = func(**args)
            return result
        except TypeError as te:
            logger.error(f"Parameter mismatch calling '{name}': {te}")
            return {"error": f"Parameter validation error for tool '{name}': {str(te)}"}
        except Exception as e:
            logger.error(f"Unexpected error executing tool '{name}': {e}")
            return {"error": f"Tool execution failed: {str(e)}"}

    def _register_default_tools(self) -> None:
        """Register core Investigator and Watchdog portfolio investigation tools."""
        self.register("search_customer_records", search_customer_records)
        self.register("get_customer_360_profile", get_customer_360_profile)
        self.register("get_policy_compliance_status", get_policy_compliance_status)
        self.register("get_premium_payment_history", get_premium_payment_history)
        self.register("get_active_attention_items", get_active_attention_items)
        self.register("get_expiring_policies", get_expiring_policies)
        self.register("get_missing_documents", get_missing_documents)
        self.register("get_customer_followup_history", get_customer_followup_history)
        self.register("investigate_customer_case", investigate_customer_case)
        self.register("generate_outreach_draft", generate_outreach_draft)
        # Portfolio investigation tools
        self.register("get_portfolio_overview", get_portfolio_overview)
        self.register("list_customer_records", list_customer_records)
        self.register("get_customer_policies", get_customer_policies)
        self.register("get_customer_payment_history", get_customer_payment_history)
        self.register("get_customer_documents", get_customer_documents)
        self.register("get_customer_claim_history", get_customer_claim_history)
        self.register("get_customer_renewal_history", get_customer_renewal_history)
        self.register("get_customer_previous_attention", get_customer_previous_attention)
        # RAG Knowledge Base tool (Investigator only)
        self.register("search_insurance_documents", search_insurance_documents)


tool_registry = ToolRegistry()
