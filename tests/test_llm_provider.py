from __future__ import annotations

import pytest

from app.api.routes import get_llm_client
from app.core.config import settings
from app.llm.mock_provider import MockProvider
from app.llm.openai_provider import OpenAIProvider


def test_get_llm_client_returns_mock():
    settings.llm_provider = "mock"
    client = get_llm_client()
    assert isinstance(client, MockProvider)


def test_get_llm_client_returns_openai(monkeypatch):
    settings.llm_provider = "openai"
    settings.openai_api_key = "test-key"
    client = get_llm_client()
    assert isinstance(client, OpenAIProvider)
