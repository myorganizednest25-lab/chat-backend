from __future__ import annotations

from typing import List

from openai import OpenAI

from app.llm.base import LLMClient, LLMMessage, LLMResponse


class OpenAIProvider(LLMClient):
    def __init__(self, api_key: str):
        self.client = OpenAI(api_key=api_key)

    def generate_chat(
        self, messages: List[LLMMessage], model: str, temperature: float, max_tokens: int
    ) -> LLMResponse:
        payload = [
            {"role": message.role, "content": message.content} for message in messages
        ]
        response = self.client.chat.completions.create(
            model=model,
            messages=payload,
            temperature=temperature,
            max_tokens=max_tokens,
        )
        content = response.choices[0].message.content
        usage = response.usage
        usage_dict = usage.to_dict() if hasattr(usage, "to_dict") else dict(usage or {})

        return LLMResponse(
            content=content or "",
            provider="openai",
            model=model,
            usage=usage_dict,
        )

    def stream_chat(
        self, messages: List[LLMMessage], model: str, temperature: float, max_tokens: int
    ):
        payload = [
            {"role": message.role, "content": message.content} for message in messages
        ]
        stream = self.client.chat.completions.create(
            model=model,
            messages=payload,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=True,
        )
        for chunk in stream:
            if not chunk.choices:
                continue
            delta = chunk.choices[0].delta.content or ""
            if delta:
                yield delta
