"""Agent Conversation and Message Pydantic v2 schemas."""

from datetime import datetime
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, ConfigDict, Field


class AgentMessageBase(BaseModel):
    sender: str = Field(..., description="USER, ASSISTANT, SYSTEM, TOOL")
    content: str
    tool_calls: Optional[List[Dict[str, Any]]] = None
    tool_results: Optional[List[Dict[str, Any]]] = None


class AgentMessageResponse(AgentMessageBase):
    id: str
    conversation_id: str
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class AgentConversationBase(BaseModel):
    customer_id: Optional[str] = None
    title: str = "Customer Intelligence Investigation"
    session_metadata: Optional[Dict[str, Any]] = None


class AgentConversationResponse(BaseModel):
    id: str
    customer_id: Optional[str] = None
    title: str
    session_metadata: Optional[Dict[str, Any]] = None
    created_at: datetime
    updated_at: datetime
    messages: List[AgentMessageResponse] = []

    model_config = ConfigDict(from_attributes=True)


class ChatQueryRequest(BaseModel):
    conversation_id: Optional[str] = None
    customer_id: Optional[str] = None
    message: str = Field(..., min_length=1)
    context_filters: Optional[Dict[str, Any]] = None
