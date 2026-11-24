"""Central AI Agent Subsystem for VM_project.

Contains:
- The Watchdog: Proactive AI Customer Monitoring (watchdog_scanner)
- The Investigator: Conversational AI Copilot (copilot_agent)
- Tool Registry: 10 Reusable database retrieval & action tools (tool_registry)
- Gemini Client: Modern Google GenAI SDK wrapper (gemini_client)
- Intelligence Core: Unified reasoning engine (intelligence_core)
"""

from app.agent.gemini_client import gemini_client, GeminiClientWrapper
from app.agent.tool_registry import tool_registry, ToolRegistry
from app.agent.intelligence_core import intelligence_core, IntelligenceCore
from app.agent.proactive_scanner import watchdog_scanner, ProactiveWatchdogScanner
from app.agent.copilot_agent import copilot_agent, ConversationalInvestigatorCopilot

__all__ = [
    "gemini_client",
    "GeminiClientWrapper",
    "tool_registry",
    "ToolRegistry",
    "intelligence_core",
    "IntelligenceCore",
    "watchdog_scanner",
    "ProactiveWatchdogScanner",
    "copilot_agent",
    "ConversationalInvestigatorCopilot",
]
