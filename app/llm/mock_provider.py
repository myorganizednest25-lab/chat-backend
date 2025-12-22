from __future__ import annotations

from typing import List

from app.llm.base import LLMClient, LLMMessage, LLMResponse


class MockProvider(LLMClient):
    def generate_chat(
        self, messages: List[LLMMessage], model: str, temperature: float, max_tokens: int
    ) -> LLMResponse:
        last_user = next((m for m in reversed(messages) if m.role == "user"), None)
        answer = f"(mock answer) {last_user.content if last_user else ''}".strip()
        return LLMResponse(
            content=answer,
            provider="mock",
            model=model,
            usage={"mock": True, "prompt_tokens": 0, "completion_tokens": len(answer)},
        )
