from __future__ import annotations

import hashlib
from typing import List, Protocol

from openai import OpenAI

from app.core.config import settings


class EmbeddingClient(Protocol):
    def embed(self, text: str) -> List[float]: ...


class OpenAIEmbeddingClient:
    def __init__(self, api_key: str, model: str | None = None):
        self.client = OpenAI(api_key=api_key)
        self.model = model or settings.embedding_model

    def embed(self, text: str) -> List[float]:
        resp = self.client.embeddings.create(model=self.model, input=text)
        return resp.data[0].embedding


class MockEmbeddingClient:
    """Deterministic mock embedding for testing."""

    def __init__(self, dim: int = 16):
        self.dim = dim

    def embed(self, text: str) -> List[float]:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        # Produce a small deterministic vector.
        vals = []
        for i in range(self.dim):
            vals.append(int.from_bytes(digest[i : i + 2], "little") / 65535.0)
        return vals
