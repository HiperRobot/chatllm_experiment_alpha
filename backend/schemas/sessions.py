from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class ChatSessionCreate(BaseModel):
    title: str | None = None


class ChatSessionUpdate(BaseModel):
    title: str | None = None


class ChatSessionResponse(BaseModel):
    id: int
    title: str
    user_id: int | None = None
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionListResponse(BaseModel):
    sessions: list[ChatSessionResponse]


class ChatSessionMessageResponse(BaseModel):
    id: int
    role: str
    content: str
    model: str
    created_at: datetime

    model_config = {"from_attributes": True}


class ChatSessionDetailResponse(BaseModel):
    session: ChatSessionResponse
    messages: list[ChatSessionMessageResponse]