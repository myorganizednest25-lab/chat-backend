from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import EntityDocument


class RetrievalService:
    def fetch_documents(self, session: Session, entity_id: Optional[str]) -> List[dict]:
        if not entity_id:
            return []
        try:
            entity_uuid = uuid.UUID(str(entity_id))
        except ValueError:
            return []
        stmt = (
            select(EntityDocument)
            .where(EntityDocument.entity_id == entity_uuid)
            .order_by(EntityDocument.fetched_at.desc().nullslast())
            .limit(settings.max_documents)
        )
        docs = session.scalars(stmt).all()
        return [
            {
                "id": str(doc.id),
                "entity_id": str(doc.entity_id),
                "title": doc.title,
                "source_url": doc.source_url,
                "content": doc.content,
            }
            for doc in docs
        ]
