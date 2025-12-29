from __future__ import annotations

import uuid
from typing import List, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import RawDocument


class RetrievalService:
    def fetch_documents(self, session: Session, entity_id: Optional[str]) -> List[dict]:
        if not entity_id:
            return []
        stmt = (
            select(RawDocument)
            .where(RawDocument.entity_id == entity_id)
            .order_by(RawDocument.fetched_at.desc().nullslast())
            .limit(settings.max_documents)
        )
        docs = session.scalars(stmt).all()
        return [
            {
                "id": str(doc.id),
                "entity_id": str(doc.entity_id),
                "title": doc.title,
                "source_url": doc.source_url,
                "content": doc.clean_text,
                "source_type": doc.source_type,
            }
            for doc in docs
        ]
