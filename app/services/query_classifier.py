from __future__ import annotations

import json

from app.core.config import settings
from app.llm.base import LLMClient, LLMMessage


class QueryClassifier:
    """LLM-based classifier for query intent."""

    def __init__(self, llm_client: LLMClient):
        self.llm_client = llm_client

    def classify(self, query: str) -> str:
        prompt = (
            "Classify the user question. Respond ONLY as JSON with a single field query_type set to either "
            "\"general\" or \"school_performance_report\".\n"
            "- Use \"school_performance_report\" when the user is asking about academic performance, scores, grades, ratings, or test results.\n"
            "- Otherwise respond with \"general\"."
        )
        response = self.llm_client.generate_chat(
            messages=[
                LLMMessage(role="system", content=prompt),
                LLMMessage(role="user", content=query),
            ],
            model=settings.llm_model,
            temperature=0.0,
            max_tokens=50,
        )
        try:
            data = json.loads(response.content)
            query_type = data.get("query_type")
            if query_type in {"general", "school_performance_report"}:
                return query_type
        except Exception:
            pass
        return "general"
