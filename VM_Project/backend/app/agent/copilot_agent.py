"""The Investigator: Conversational AI Copilot Engine."""

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from app.agent.intelligence_core import intelligence_core
from app.core.database import SyncSessionLocal
from app.core.logging import logger
from app.db.models import AgentConversation, AgentMessage, Customer


class ConversationalInvestigatorCopilot:
    """The Investigator: Context-aware conversational AI copilot with native tool calling."""

    def __init__(self):
        self.core = intelligence_core

    def handle_message(
        self,
        user_message: str,
        conversation_id: Optional[str] = None,
        customer_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Processes a multi-turn conversation turn:
        1. Retrieves or initializes AgentConversation.
        2. Loads historical messages.
        3. Appends incoming user message.
        4. Calls IntelligenceCore (Gemini tool calling or cognitive tool dispatch).
        5. Persists User & Assistant messages (including tool calls and results).
        6. Returns structured response.
        """
        now_utc = datetime.now(timezone.utc)
        session = SyncSessionLocal()

        try:
            # Step 1: Resolve Conversation Session
            conv: Optional[AgentConversation] = None
            if conversation_id:
                conv = session.execute(
                    select(AgentConversation)
                    .options(selectinload(AgentConversation.messages))
                    .where(AgentConversation.id == conversation_id)
                ).scalars().first()

            if not conv:
                # Create new conversation
                title = "Insurance Portfolio Investigation"
                if customer_id:
                    c = session.execute(
                        select(Customer).where(Customer.id == customer_id)
                    ).scalars().first()
                    if c:
                        title = f"Investigation: {c.full_name} ({c.customer_code})"

                conv = AgentConversation(
                    customer_id=customer_id,
                    title=title,
                    created_at=now_utc,
                    updated_at=now_utc,
                )
                session.add(conv)
                session.commit()
                session.refresh(conv)

            # Step 2: Record User Message
            user_msg_record = AgentMessage(
                conversation_id=conv.id,
                sender="USER",
                content=user_message,
                created_at=now_utc,
            )
            session.add(user_msg_record)
            session.commit()

            # Step 3: Compile Conversation History for Agent
            history_stmt = (
                select(AgentMessage)
                .where(AgentMessage.conversation_id == conv.id)
                .order_by(AgentMessage.created_at.asc())
            )
            history_records = session.execute(history_stmt).scalars().all()

            message_history = [
                {
                    "sender": m.sender,
                    "content": m.content,
                    "tool_calls": m.tool_calls,
                    "tool_results": m.tool_results,
                }
                for m in history_records
            ]

            # Step 4: Execute Agent Turn via Intelligence Core
            investigation_result = self.core.chat_investigate(
                messages=message_history,
                active_customer_id=customer_id or conv.customer_id,
            )

            assistant_reply = investigation_result.get("reply", "I reviewed the records.")
            tool_calls = investigation_result.get("tool_calls", [])
            tool_results = investigation_result.get("tool_results", [])
            execution_mode = investigation_result.get("mode", "COGNITIVE_CORE")

            # Step 5: Persist Assistant Response with Tool Telemetry
            assistant_msg_record = AgentMessage(
                conversation_id=conv.id,
                sender="ASSISTANT",
                content=assistant_reply,
                tool_calls=tool_calls if tool_calls else None,
                tool_results=tool_results if tool_results else None,
                created_at=datetime.now(timezone.utc),
            )
            session.add(assistant_msg_record)

            conv.updated_at = datetime.now(timezone.utc)
            session.commit()
            session.refresh(assistant_msg_record)

            logger.info(
                f"Copilot turn complete [Conv: {conv.id}]: "
                f"{len(tool_calls)} tools executed. Mode: {execution_mode}"
            )

            return {
                "conversation_id": conv.id,
                "message_id": assistant_msg_record.id,
                "title": conv.title,
                "reply": assistant_reply,
                "tool_calls": tool_calls,
                "tool_results": tool_results,
                "mode": execution_mode,
                "customer_id": conv.customer_id,
                "timestamp": assistant_msg_record.created_at.isoformat(),
            }

        except Exception as e:
            session.rollback()
            logger.error(f"Copilot handle_message failed: {e}")
            raise
        finally:
            session.close()


copilot_agent = ConversationalInvestigatorCopilot()
