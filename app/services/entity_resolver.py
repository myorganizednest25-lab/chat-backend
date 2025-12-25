from __future__ import annotations

from typing import Dict, List, Optional

import json
from uuid import UUID

from sqlalchemy import func, select
from sqlalchemy.orm import Session
import structlog

from app.core.config import settings
from app.db.models import Entity
from app.llm.base import LLMClient, LLMMessage
from app.utils.fuzzy import best_fuzzy_match

log = structlog.get_logger()


class EntityResolverResult:
    def __init__(
        self,
        entity: Optional[Entity],
        candidates: List[Dict],
    ):
        self.entity = entity
        self.candidates = candidates


class EntityResolver:
    """Fuzzy resolver using entities.name only."""

    def __init__(self, score_cutoff: int = 70):
        self.score_cutoff = score_cutoff

    def resolve(
        self, session: Session, query: str, city: Optional[str] = None, state: Optional[str] = None
    ) -> EntityResolverResult:
        q = select(Entity)
        if city:
            q = q.where(func.lower(Entity.city) == city.lower())
        if state:
            q = q.where(func.lower(Entity.state) == state.lower())

        entities = session.scalars(q).all()
        names = [e.name for e in entities]
        match = best_fuzzy_match(query, names, score_cutoff=self.score_cutoff)

        matched_entity: Optional[Entity] = None
        candidates: List[Dict] = []

        for entity in entities:
            score = 0.0
            if match and match[0] == entity.name:
                score = match[1]
                matched_entity = entity
            candidates.append(
                {
                    "id": str(entity.id),
                    "name": entity.name,
                    "entity_type": entity.entity_type,
                    "city": entity.city,
                    "state": entity.state,
                    "score": score,
                }
            )

        log.info(
            "entity_resolver.candidates",
            query=query,
            city=city,
            state=state,
            candidate_count=len(candidates),
            candidates=candidates,
            best_match=matched_entity.name if matched_entity else None,
            best_score=match[1] if match else None,
            mode="fuzzy",
        )

        return EntityResolverResult(entity=matched_entity, candidates=candidates)


class LLMEntityResolver:
    """LLM-based resolver: provide candidates, ask model to pick or return none."""

    def __init__(self, llm_client: LLMClient, candidate_limit: int = 50):
        self.llm_client = llm_client
        self.candidate_limit = candidate_limit

    def resolve(
        self, session: Session, query: str, city: Optional[str] = None, state: Optional[str] = None
    ) -> EntityResolverResult:
        q = select(Entity)
        if city:
            q = q.where(func.lower(Entity.city) == city.lower())
        if state:
            q = q.where(func.lower(Entity.state) == state.lower())
        q = q.limit(self.candidate_limit)
        entities = session.scalars(q).all()

        candidates = [
            {
                "id": str(entity.id),
                "name": entity.name,
                "entity_type": entity.entity_type,
            }
            for entity in entities
        ]

        if not candidates:
            log.info(
                "entity_resolver.candidates",
                query=query,
                city=city,
                state=state,
                candidate_count=0,
                candidates=[],
                best_match=None,
                best_score=None,
                mode="llm",
            )
            return EntityResolverResult(entity=None, candidates=[])

        prompt = (
            "You are selecting the best matching entity for a user's question. The entities are schools, camps or programs for children."
            "Choose the single best entity id from the provided list, or respond with null if none match. "
            "Respond strictly as JSON: {\"entity_id\": \"<uuid>\"} or {\"entity_id\": null}."
        )
        user_content = json.dumps(
            {
                "query": query,
                "candidates": candidates,
            }
        )

        response = self.llm_client.generate_chat(
            messages=[
                LLMMessage(role="system", content=prompt),
                LLMMessage(role="user", content=user_content),
            ],
            model=settings.llm_model,
            temperature=0.0,
            max_tokens=200,
        )

        log.info(
            "entity_resolver.llm_response",
            raw_response=response.content,
        )

        selected_id = self._parse_entity_id(response.content, candidates)
        matched_entity = None
        if selected_id:
            matched_entity = next((e for e in entities if str(e.id) == selected_id), None)
            if matched_entity:
                log.info(f"Resolved query entity to ${matched_entity.name}")

        log.debug(
            "entity_resolver.candidates",
            query=query,
            city=city,
            state=state,
            candidate_count=len(candidates),
            candidates=candidates,
            best_match=matched_entity.name if matched_entity else None,
            best_score=None,
            mode="llm",
        )

        return EntityResolverResult(entity=matched_entity, candidates=candidates)

    def _parse_entity_id(self, content: str, candidates: List[Dict]) -> Optional[str]:
        try:
            data = json.loads(content)
            entity_id = data.get("entity_id")
            if not entity_id:
                return None
            # validate uuid and ensure it's in candidates
            _ = UUID(str(entity_id))
            candidate_ids = {c["id"] for c in candidates}
            return str(entity_id) if str(entity_id) in candidate_ids else None
        except Exception:
            return None
