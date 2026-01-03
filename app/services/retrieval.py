from __future__ import annotations

from typing import List, Optional, Sequence

from sqlalchemy import select, text, func
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import RawDocument
from app.llm.embeddings import EmbeddingClient


class RetrievalService:
    def fetch_document_metadata(
        self,
        session: Session,
        entity_id: Optional[str],
        include_source_types: Optional[Sequence[str]] = None,
        exclude_source_types: Optional[Sequence[str]] = None,
    ) -> List[dict]:
        """Fetch document headers (no content)."""
        if not entity_id:
            return []
        stmt = (
            select(RawDocument)
            .where(RawDocument.entity_id == entity_id)
            .order_by(RawDocument.fetched_at.desc().nullslast())
            .limit(settings.max_documents)
        )
        if include_source_types:
            stmt = stmt.where(RawDocument.source_type.in_(include_source_types))
        elif exclude_source_types:
            stmt = stmt.where(~RawDocument.source_type.in_(exclude_source_types))
        docs = session.scalars(stmt).all()
        return [
            {
                "id": str(doc.id),
                "entity_id": str(doc.entity_id),
                "title": doc.title,
                "source_url": doc.source_url,
                "source_type": doc.source_type,
            }
            for doc in docs
        ]

    def fetch_documents_by_ids(self, session: Session, document_ids: Sequence[str]) -> List[dict]:
        if not document_ids:
            return []
        stmt = select(RawDocument).where(RawDocument.id.in_(document_ids))
        docs = session.scalars(stmt).all()
        ordered = {str(doc.id): doc for doc in docs}
        results = []
        for doc_id in document_ids:
            doc = ordered.get(str(doc_id))
            if not doc:
                continue
            results.append(
                {
                    "id": str(doc.id),
                    "entity_id": str(doc.entity_id),
                    "title": doc.title,
                    "source_url": doc.source_url,
                    "content": doc.clean_text,
                    "source_type": doc.source_type,
                }
            )
        return results

    def fetch_documents_by_similarity(
        self,
        session: Session,
        entity_id: Optional[str],
        query: str,
        embedding_client: EmbeddingClient,
        include_source_types: Optional[Sequence[str]] = None,
        exclude_source_types: Optional[Sequence[str]] = None,
        limit: int = 10,
    ) -> List[dict]:
        if not entity_id:
            return []

        query_embedding = embedding_client.embed(query)

        filters = ["(cd.entity_id = :entity_id OR cd.entity_id IS NULL)"]
        params = {"entity_id": entity_id, "query_embedding": query_embedding, "limit": limit}
        if include_source_types:
            filters.append("COALESCE(rd.source_type, cd.source_type) = ANY(:include_types)")
            params["include_types"] = list(include_source_types)
        elif exclude_source_types:
            filters.append("NOT (COALESCE(rd.source_type, cd.source_type) = ANY(:exclude_types))")
            params["exclude_types"] = list(exclude_source_types)

        where_clause = " AND ".join(filters)
        sql = text(
            f"""
            SELECT
                COALESCE(cd.raw_document_id, rd.id) AS raw_document_id,
                COALESCE(rd.title, cd.section_title) AS chunk_title,
                COALESCE(rd.source_type, cd.source_type) AS chunk_source_type,
                MIN(cd.embedding <=> CAST(:query_embedding AS vector)) AS score
            FROM chunked_documents cd
            LEFT JOIN raw_documents rd ON rd.id = cd.raw_document_id
            WHERE {where_clause}
            GROUP BY COALESCE(cd.raw_document_id, rd.id), COALESCE(rd.title, cd.section_title), COALESCE(rd.source_type, cd.source_type)
            ORDER BY score ASC
            LIMIT :limit
            """
        )
        rows = session.execute(sql, params).all()

        doc_ids: List[str] = []
        fallback_titles: List[str] = []
        for row in rows:
            raw_id = getattr(row, "raw_document_id", None)
            if raw_id:
                doc_ids.append(str(raw_id))
                continue
            chunk_source_type = getattr(row, "chunk_source_type", None)
            chunk_title = getattr(row, "chunk_title", None)
            if chunk_source_type == "csv" and chunk_title:
                fallback_titles.append(chunk_title)

        # Deduplicate while preserving order
        seen = set()
        ordered_ids: List[str] = []
        for doc_id in doc_ids:
            if doc_id in seen:
                continue
            seen.add(doc_id)
            ordered_ids.append(doc_id)

        for title in fallback_titles:
            fallback_id = self._find_raw_document_by_title(session, entity_id, title)
            if fallback_id and fallback_id not in seen:
                seen.add(fallback_id)
                ordered_ids.append(fallback_id)
                if len(ordered_ids) >= limit:
                    break

        return self.fetch_documents_by_ids(session, ordered_ids)

    def _find_raw_document_by_title(
        self, session: Session, entity_id: str, title: str
    ) -> Optional[str]:
        safe_title = (title or "").strip().lower()
        if not safe_title:
            return None
        stmt = (
            select(RawDocument.id)
            .where(
                RawDocument.entity_id == entity_id,
                func.lower(RawDocument.title).contains(safe_title),
            )
            .order_by(RawDocument.fetched_at.desc().nullslast())
            .limit(1)
        )
        doc_id = session.scalars(stmt).first()
        return str(doc_id) if doc_id else None
