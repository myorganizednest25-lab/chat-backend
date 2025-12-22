from __future__ import annotations

from dataclasses import dataclass
from typing import List, Protocol


@dataclass
class LLMMessage:
    role: str
    content: str


@dataclass
class LLMResponse:
    content: str
    provider: str
    model: str
    usage: dict


class LLMClient(Protocol):
    def generate_chat(
        self, messages: List[LLMMessage], model: str, temperature: float, max_tokens: int
    ) -> LLMResponse: ...
