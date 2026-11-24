"""Conversational AI Investigator Copilot API endpoints."""

from typing import Any, Dict, List
from fastapi import APIRouter, Depends, HTTPException
from fastapi.concurrency import run_in_threadpool
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.agent.copilot_agent import copilot_agent
from app.agent.tool_registry import tool_registry
from app.core.database import get_async_db
from app.db.models import AgentConversation
from app.schemas.conversation import (
    ChatQueryRequest,
    AgentConversationResponse,
)

router = APIRouter(prefix="/copilot", tags=["AI Copilot (The Investigator)"])


@router.post("/chat")
async def chat_with_copilot(payload: ChatQueryRequest):
    """
    Conversational turn with The Investigator Copilot.
    - Offloads synchronous agent + DB + Gemini SDK execution to threadpool (non-blocking).
    - Employs native function calling with database tools.
    - Retrieves real database records before answering.
    - Maintains multi-turn conversation session history.
    """
    try:
        response = await run_in_threadpool(
            copilot_agent.handle_message,
            user_message=payload.message,
            conversation_id=payload.conversation_id,
            customer_id=payload.customer_id,
        )
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Copilot investigation failed: {str(e)}")


@router.get("/conversations", response_model=List[Dict[str, Any]])
async def list_conversations(db: AsyncSession = Depends(get_async_db)):
    """List recent copilot conversation sessions."""
    stmt = (
        select(AgentConversation)
        .options(selectinload(AgentConversation.messages))
        .order_by(AgentConversation.updated_at.desc())
        .limit(20)
    )
    res = await db.execute(stmt)
    convs = res.scalars().all()
    return [
        {
            "id": c.id,
            "title": c.title,
            "customer_id": c.customer_id,
            "message_count": len(c.messages),
            "updated_at": c.updated_at,
        }
        for c in convs
    ]


@router.get("/conversations/{conversation_id}", response_model=AgentConversationResponse)
async def get_conversation_session(
    conversation_id: str, db: AsyncSession = Depends(get_async_db)
):
    """Retrieve full message history for a conversation session."""
    stmt = (
        select(AgentConversation)
        .options(selectinload(AgentConversation.messages))
        .where(AgentConversation.id == conversation_id)
    )
    res = await db.execute(stmt)
    conv = res.scalars().first()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversation session not found.")
    return conv


@router.get("/tools")
async def list_available_tools():
    """Returns the catalog of 10 registered Python database retrieval & investigation tools."""
    return {
        "total_tools": len(tool_registry.get_all_callables()),
        "tools": tool_registry.get_tool_metadata(),
    }
