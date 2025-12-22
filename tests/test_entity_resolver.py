from __future__ import annotations

from app.db.models import Entity
from app.services.entity_resolver import EntityResolver


def test_entity_resolver_matches_best_candidate(db_session):
    school = Entity(name="Happy Valley School", entity_type="school", city="Austin", state="TX")
    other = Entity(name="Sunrise Academy", entity_type="school", city="Austin", state="TX")
    db_session.add_all([school, other])
    db_session.commit()

    resolver = EntityResolver(score_cutoff=50)
    result = resolver.resolve(db_session, "happy valley school", city="Austin")

    assert result.entity is not None
    assert result.entity.name == "Happy Valley School"
    assert any(c["name"] == "Happy Valley School" for c in result.candidates)
