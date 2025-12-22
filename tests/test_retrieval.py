from __future__ import annotations

from datetime import datetime

from app.db.models import Entity, EntityDocument
from app.services.retrieval import RetrievalService


def test_retrieval_returns_documents_for_entity(db_session):
    entity = Entity(name="Happy Valley School", entity_type="school", city="Austin", state="TX")
    db_session.add(entity)
    db_session.flush()

    doc = EntityDocument(
        entity_id=entity.id,
        title="Handbook",
        source_url="http://example.com/handbook",
        content="All students must arrive by 8am.",
        fetched_at=datetime.utcnow(),
    )
    db_session.add(doc)
    db_session.commit()

    service = RetrievalService()
    docs = service.fetch_documents(db_session, str(entity.id))

    assert len(docs) == 1
    assert docs[0]["title"] == "Handbook"
