"""OpenAI chat-completions adapter.

Requires `OPENAI_API_KEY`. Not exercised by the test suite (offline-by-
default convention) — the gateway routes to `provider: stub` models when
no key is configured. Wire a real key via `.env` to use it.
"""
from __future__ import annotations

import time
from collections.abc import Sequence

import httpx

from app.core.models import ChatMessage

from .base import ProviderAdapter, ProviderResult


class OpenAIAdapter(ProviderAdapter):
    name = "openai"

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key
        self._base_url = base_url
        self._timeout = timeout

    def complete(
        self,
        messages: Sequence[ChatMessage],
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> ProviderResult:
        if not self._api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        start = time.perf_counter()
        response = httpx.post(
            f"{self._base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={
                "model": model,
                "messages": [m.model_dump() for m in messages],
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
            timeout=self._timeout,
        )
        response.raise_for_status()
        data = response.json()
        latency_ms = round((time.perf_counter() - start) * 1000, 4)
        usage = data.get("usage", {})
        return ProviderResult(
            output=data["choices"][0]["message"]["content"],
            input_tokens=usage.get("prompt_tokens", 0),
            output_tokens=usage.get("completion_tokens", 0),
            latency_ms=latency_ms,
            raw_metadata={"provider": "openai", "id": data.get("id")},
        )
