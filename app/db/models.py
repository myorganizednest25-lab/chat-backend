from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any, Dict, Optional

from sqlalchemy import (
    JSON,
    TIMESTAMP,
    Column,
    ForeignKey,
    Index,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import UUID as PG_UUID
from sqlalchemy.orm import declarative_base, relationship


Base = declarative_base()


def uuid_column() -> Column:
    return Column(
        PG_UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
    )


class ChatSession(Base):
    __tablename__ = "chat_sessions"

    id = uuid_column()
    user_id = Column(String, nullable=True)
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=text("now()"),
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=text("now()"),
        onupdate=datetime.utcnow,
    )

    messages = relationship("ChatMessage", back_populates="session", cascade="all,delete")
    state = relationship("SessionState", back_populates="session", uselist=False, cascade="all,delete")


class ChatMessage(Base):
    __tablename__ = "chat_messages"

    id = uuid_column()
    session_id = Column(PG_UUID(as_uuid=True), ForeignKey("chat_sessions.id"), nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=text("now()"),
    )
    meta = Column("metadata", JSON, nullable=False, default=dict, server_default=text("'{}'"))

    session = relationship("ChatSession", back_populates="messages")

    __table_args__ = (Index("ix_chat_messages_session_id", "session_id"),)


class SessionState(Base):
    __tablename__ = "session_state"

    session_id = Column(
        PG_UUID(as_uuid=True), ForeignKey("chat_sessions.id"), primary_key=True
    )
    state = Column(JSON, nullable=False, default=dict, server_default=text("'{}'"))
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=text("now()"),
        onupdate=datetime.utcnow,
    )

    session = relationship("ChatSession", back_populates="state")


class Entity(Base):
    __tablename__ = "entities"

    id = uuid_column()
    name = Column(String, nullable=False)
    entity_type = Column("type", String, key="entity_type", nullable=False)
    city = Column(String, nullable=True)
    state = Column(String, nullable=True)
    url = Column(String, nullable=True)
    meta = Column("metadata", JSON, nullable=False, default=dict, server_default=text("'{}'"))
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=text("now()"),
        onupdate=datetime.utcnow,
    )
    slug = Column(String, nullable=False)


class RawDocument(Base):
    __tablename__ = "raw_documents"

    id = uuid_column()
    entity_id = Column(PG_UUID(as_uuid=True), ForeignKey("entities.id"), nullable=False)
    title = Column(String, nullable=True)
    source_url = Column(String, nullable=True)
    source_type = Column(String, nullable=False)
    clean_text = Column(Text, nullable=False)
    fetched_at = Column(TIMESTAMP(timezone=True), nullable=False, default=datetime.utcnow)
    checksum_sha256 = Column(String, nullable=True)
    meta = Column("metadata", JSON, nullable=False, default=dict, server_default=text("'{}'"))
    created_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=text("now()"),
    )
    updated_at = Column(
        TIMESTAMP(timezone=True),
        nullable=False,
        default=datetime.utcnow,
        server_default=text("now()"),
        onupdate=datetime.utcnow,
    )

    entity = relationship("Entity")

    __table_args__ = (Index("ix_raw_documents_entity_id", "entity_id"),)
