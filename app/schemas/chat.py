from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class SessionCreateResponse(BaseModel):
    session_id: str


class MessageSchema(BaseModel):
    id: str
    role: str
    content: str
    created_at: datetime
    metadata: Dict[str, Any] = Field(default_factory=dict, alias="meta")

    model_config = {"from_attributes": True, "populate_by_name": True}


class SessionSchema(BaseModel):
    id: str
    user_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    messages: List[MessageSchema]

    model_config = {"from_attributes": True}


class EntitySchema(BaseModel):
    id: Optional[str] = None
    name: Optional[str] = None
    type: Optional[str] = Field(default=None, serialization_alias="entity_type")
    city: Optional[str] = None
    state: Optional[str] = None


class ChatRequest(BaseModel):
    session_id: str
    user_id: Optional[str] = None
    message: str
    city: Optional[str] = None
    state: Optional[str] = None
    stream: bool = False


class DebugInfo(BaseModel):
    entity_candidates: Optional[List[dict]] = None
    retrieval_count: Optional[int] = None
    provider: Optional[str] = None
    model: Optional[str] = None


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    entity: Optional[EntitySchema] = None
    citations: List[dict] = Field(default_factory=list)
    debug: Optional[DebugInfo] = None
