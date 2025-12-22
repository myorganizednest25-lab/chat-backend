from __future__ import annotations

from typing import Dict, List, Optional, Tuple

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.core.config import settings
from app.db.models import Entity
from app.utils.fuzzy import best_fuzzy_match


class EntityResolverResult:
    def __init__(
        self,
        entity: Optional[Entity],
        candidates: List[Dict],
    ):
        self.entity = entity
        self.candidates = candidates


class EntityResolver:
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

        return EntityResolverResult(entity=matched_entity, candidates=candidates)
