from __future__ import annotations

from datetime import datetime

from fastapi.testclient import TestClient
from sqlalchemy.orm import sessionmaker

from app import api
from app.core.config import settings
from app.db.models import Base, ChatSession, Entity, EntityDocument
from app.main import app


def test_chat_endpoint_flow(engine):
    settings.llm_provider = "mock"
    SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False, future=True)

    def override_get_db():
        db = SessionLocal()
        try:
            yield db
            db.commit()
        finally:
            db.close()

    app.dependency_overrides[api.routes.get_db] = override_get_db

    with SessionLocal() as db:
        entity = Entity(name="Happy Valley School", entity_type="school", city="Austin", state="TX")
        db.add(entity)
        db.flush()
        doc = EntityDocument(
            entity_id=entity.id,
            title="Handbook",
            source_url="http://example.com/handbook",
            content="Students arrive by 8am.",
            fetched_at=datetime.utcnow(),
        )
        db.add(doc)
        db.commit()

    client = TestClient(app)
    session_resp = client.post("/v1/sessions")
    assert session_resp.status_code == 200
    session_id = session_resp.json()["session_id"]

    chat_resp = client.post(
        "/v1/chat",
        json={"session_id": session_id, "message": "Tell me about Happy Valley School in Austin"},
    )

    assert chat_resp.status_code == 200
    data = chat_resp.json()
    assert data["session_id"] == session_id
    assert data["entity"]["name"] == "Happy Valley School"
    assert len(data["citations"]) == 1
    assert "mock answer" in data["answer"]

    app.dependency_overrides.clear()
