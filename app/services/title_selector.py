from __future__ import annotations

import json
from typing import List, Sequence

from app.core.config import settings
from app.llm.base import LLMClient, LLMMessage
import structlog


log = structlog.get_logger()


class TitleSelector:
    """Ask the LLM to pick the most relevant document titles."""

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def select_titles(
        self, query: str, query_type: str, documents: Sequence[dict], limit: int = 10
    ) -> List[str]:
        if not documents:
            return []

        prompt = (
            "You are selecting document titles that are most likely to contain information to answer the user's question.\n"
            f"The query_type is \"{query_type}\". Return up to {limit} document_ids in order of relevance.\n"
            "Only pick from the provided documents. Respond strictly as JSON: {\"document_ids\": [\"<uuid>\", ...]}."
        )

        seen_titles = set()
        unique_docs = []
        for doc in documents:
            title = (doc.get("title") or "").strip().lower()
            if title in seen_titles:
                continue
            seen_titles.add(title)
            unique_docs.append(doc)

        doc_payload = [
            {"id": doc["id"], "title": doc.get("title") or "", "source_type": doc.get("source_type")}
            for doc in unique_docs
        ]

        log.info(
            "title_selector.candidates",
            query=query,
            query_type=query_type,
            document_titles=[doc["title"] for doc in doc_payload],
        )
        response = self.llm_client.generate_chat(
            messages=[
                LLMMessage(role="system", content=prompt),
                LLMMessage(
                    role="user",
                    content=json.dumps({"query": query, "documents": doc_payload}),
                ),
            ],
            model=settings.llm_model,
            temperature=0.0,
            max_tokens=200,
        )
        log.info(
            "title_selector.response",
            query=query,
            query_type=query_type,
            raw_response=response.content,
        )
        try:
            data = json.loads(response.content)
            ids = data.get("document_ids") or []
            if not isinstance(ids, list):
                return []
            valid_ids = {doc["id"] for doc in documents}
            filtered: List[str] = []
            for doc_id in ids:
                if not isinstance(doc_id, str):
                    continue
                if doc_id in valid_ids and doc_id not in filtered:
                    filtered.append(doc_id)
                if len(filtered) >= limit:
                    break
            return filtered
        except Exception:
            return []
