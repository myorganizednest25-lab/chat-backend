from __future__ import annotations

from typing import List, Optional

import structlog
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import ChatMessage, ChatSession, SessionState
from app.llm.base import LLMClient, LLMMessage
from app.schemas.chat import ChatRequest, ChatResponse, EntitySchema
from app.services.entity_resolver import EntityResolver, EntityResolverResult
from app.services.retrieval import RetrievalService
from app.utils.citations import build_citation_map, format_citations


log = structlog.get_logger()


SYSTEM_PROMPT = (
    "You are a helpful assistant that answers questions in natural language that is easy to read. "
    "Be honest about what you know and do not know. "
    "Use the provided documents when answering. Cite sources using [doc#] after statements when applicable."
)


class ChatOrchestrator:
    def __init__(
        self,
        entity_resolver: EntityResolver,
        retrieval_service: RetrievalService,
        llm_client: LLMClient,
    ):
        self.entity_resolver = entity_resolver
        self.retrieval_service = retrieval_service
        self.llm_client = llm_client

    # def _load_session(self, db: Session, session_id: str) -> ChatSession:
    #     session = db.get(ChatSession, session_id)
    #     if not session:
    #         raise ValueError("Session not found")
    #     return session

    # def _history_messages(self, db: Session, session_id: str) -> List[ChatMessage]:
    #     stmt = (
    #         select(ChatMessage)
    #         .where(ChatMessage.session_id == session_id)
    #         .order_by(ChatMessage.created_at.desc())
    #         .limit(settings.history_window)
    #     )
    #     records = list(reversed(db.scalars(stmt).all()))
    #     return records

    def _build_llm_messages(
        self,
        history: List[ChatMessage],
        documents: List[dict],
        user_message: ChatMessage,
    ) -> List[LLMMessage]:
        llm_messages: List[LLMMessage] = [LLMMessage(role="system", content=SYSTEM_PROMPT)]

        if documents:
            citation_map, order = build_citation_map(documents)
            context_blocks = []
            for key in order:
                doc = citation_map[key]
                context_blocks.append(f"[{key}] {doc['title']}: {doc['content']}")
            doc_context = "\n\n".join(context_blocks)
            llm_messages.append(
                LLMMessage(
                    role="system",
                    content=f"Use these documents as citations:\n{doc_context}",
                )
            )

        for msg in history:
            llm_messages.append(LLMMessage(role=msg.role, content=msg.content))

        llm_messages.append(LLMMessage(role=user_message.role, content=user_message.content))
        return llm_messages

    def handle_chat(self, db: Session, payload: ChatRequest) -> ChatResponse:
        # Persistence and history are temporarily disabled.
        # chat_session = self._load_session(db, payload.session_id)
        # if payload.user_id and not chat_session.user_id:
        #     chat_session.user_id = payload.user_id
        # user_message = ChatMessage(
        #     session_id=chat_session.id,
        #     role="user",
        #     content=payload.message,
        #     meta={},
        # )
        # db.add(user_message)
        # db.flush()
        user_message = ChatMessage(
            session_id=None,
            role="user",
            content=payload.message,
            meta={},
        )

        log.info("<<<Fetching entity for user query>>>")
        resolver_result: EntityResolverResult = self.entity_resolver.resolve(
            db, payload.message, city=payload.city, state=payload.state
        )
        entity = resolver_result.entity

        log.info("<<<Fetching documents for the entity>>>")
        documents = self.retrieval_service.fetch_documents(
            db, str(entity.id) if entity else None
        )
        log.info(
            "retrieval.results",
            # session_id=str(chat_session.id),
            entity_id=str(entity.id) if entity else None,
            doc_count=len(documents),
            doc_titles=[doc.get("title") for doc in documents],
        )

        history: List[ChatMessage] = []
        llm_messages = self._build_llm_messages(history, documents, user_message)

        log.info("<<<Sending message to llm for QA>>>")

        response = self.llm_client.generate_chat(
            messages=llm_messages,
            model=settings.llm_model,
            temperature=settings.llm_temperature,
            max_tokens=settings.llm_max_tokens,
        )

        # assistant_message = ChatMessage(
        #     session_id=chat_session.id,
        #     role="assistant",
        #     content=response.content,
        #     meta={
        #         "provider": response.provider,
        #         "model": response.model,
        #         "usage": response.usage,
        #         "entity_id": str(entity.id) if entity else None,
        #         "doc_ids": [doc["id"] for doc in documents],
        #     },
        # )
        # db.add(assistant_message)

        # state = db.get(SessionState, chat_session.id)
        # if not state:
        #     state = SessionState(session_id=chat_session.id, state={})
        #     db.add(state)
        # state.state.update(
        #     {
        #         "entity_id": str(entity.id) if entity else None,
        #         "last_message_id": str(assistant_message.id),
        #     }
        # )

        citation_map, order = build_citation_map(documents)
        citations = format_citations(order, citation_map)

        debug_payload = {
            "entity_candidates": resolver_result.candidates,
            "retrieval_count": len(documents),
            "provider": response.provider,
            "model": response.model,
        }

        log.info(
            "chat.completed",
            # session_id=str(chat_session.id),
            entity_id=str(entity.id) if entity else None,
            docs=len(documents),
        )

        entity_schema = (
            EntitySchema(
                id=str(entity.id),
                name=entity.name,
                type=entity.entity_type,
                city=entity.city,
                state=entity.state,
            )
            if entity
            else None
        )

        return ChatResponse(
            session_id=payload.session_id,
            answer=response.content,
            entity=entity_schema,
            citations=citations,
            debug=debug_payload if settings.debug else None,
        )
