from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class ChatRequest(BaseModel):
    content: str = Field(min_length=1, max_length=4000)
    session_id: str | None = None


class AgentMessage(BaseModel):
    type: Literal["trace", "final"]
    agent: str
    content: str
    function: str | None = None


class ChatResponse(BaseModel):
    session_id: str
    messages: list[AgentMessage]


class ChatSessionRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    created_at: datetime
    updated_at: datetime


class ChatMessageRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    session_id: str
    role: str
    content: str
    message_type: str
    agent_name: str | None
    agent_function: str | None
    created_at: datetime
