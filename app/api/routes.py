from __future__ import annotations

import time
from typing import Callable, Generator

from fastapi import APIRouter, Depends, HTTPException, Request, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import ChatMessage, ChatSession
from app.db.session import get_session
from app.llm.mock_provider import MockProvider
from app.llm.openai_provider import OpenAIProvider
from app.schemas.chat import (
    ChatRequest,
    ChatResponse,
    MessageSchema,
    SessionCreateResponse,
    SessionSchema,
)
from app.services.entity_resolver import EntityResolver
from app.services.orchestrator import ChatOrchestrator
from app.services.retrieval import RetrievalService


router = APIRouter(prefix="/v1")


class RateLimiter:
    """Simple in-memory rate limiter. TODO: replace with Redis/centralized store."""
    def __init__(self, limit: int = 60):
        self.limit = limit
        self.bucket = {}

    def check(self, key: str) -> None:
        now = time.time()
        window_start = now - 60
        timestamps = [t for t in self.bucket.get(key, []) if t > window_start]
        if len(timestamps) >= self.limit:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Rate limit exceeded")
        timestamps.append(now)
        self.bucket[key] = timestamps


rate_limiter = RateLimiter(limit=settings.rate_limit_per_minute)


def rate_limit_dependency(request: Request):
    client_ip = request.client.host if request.client else "unknown"
    rate_limiter.check(client_ip)


def get_db() -> Generator[Session, None, None]:
    with get_session() as session:
        yield session


def get_llm_client():
    if settings.llm_provider == "openai":
        if not settings.openai_api_key:
            raise HTTPException(status_code=500, detail="OpenAI API key not configured")
        return OpenAIProvider(api_key=settings.openai_api_key)
    return MockProvider()


def get_orchestrator():
    return ChatOrchestrator(
        entity_resolver=EntityResolver(),
        retrieval_service=RetrievalService(),
        llm_client=get_llm_client(),
    )


@router.post("/sessions", response_model=SessionCreateResponse)
def create_session(
    request: Request,
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit_dependency),
):
    session = ChatSession()
    db.add(session)
    db.flush()
    return SessionCreateResponse(session_id=str(session.id))


@router.get("/sessions/{session_id}", response_model=SessionSchema)
def get_session_detail(
    session_id: str,
    db: Session = Depends(get_db),
    _: None = Depends(rate_limit_dependency),
):
    session = db.get(ChatSession, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    stmt = (
        select(ChatMessage)
        .where(ChatMessage.session_id == session_id)
        .order_by(ChatMessage.created_at.desc())
        .limit(settings.history_window)
    )
    messages = list(reversed(db.scalars(stmt).all()))
    session.messages = messages
    return session


@router.post("/chat", response_model=ChatResponse)
def chat(
    payload: ChatRequest,
    db: Session = Depends(get_db),
    orchestrator: ChatOrchestrator = Depends(get_orchestrator),
    _: None = Depends(rate_limit_dependency),
):
    try:
        return orchestrator.handle_chat(db, payload)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc


@router.get("/healthz")
def healthcheck():
    return {"status": "ok"}
