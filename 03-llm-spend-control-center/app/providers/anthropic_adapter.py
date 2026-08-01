"""Anthropic messages adapter.

Requires `ANTHROPIC_API_KEY`. Not exercised by the test suite (offline-by-
default convention) — the gateway routes to `provider: stub` models when
no key is configured. Wire a real key via `.env` to use it.
"""
from __future__ import annotations

import time
from collections.abc import Sequence

import httpx

from app.core.models import ChatMessage

from .base import ProviderAdapter, ProviderResult


class AnthropicAdapter(ProviderAdapter):
    name = "anthropic"

    def __init__(
        self,
        api_key: str,
        base_url: str = "https://api.anthropic.com/v1",
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
            raise RuntimeError("ANTHROPIC_API_KEY is not configured")
        start = time.perf_counter()
        system = "\n".join(m.content for m in messages if m.role == "system") or None
        turns = [m.model_dump() for m in messages if m.role != "system"]
        response = httpx.post(
            f"{self._base_url}/messages",
            headers={
                "x-api-key": self._api_key,
                "anthropic-version": "2023-06-01",
            },
            json={
                "model": model,
                "system": system,
                "messages": turns,
                "max_tokens": max_tokens,
                "temperature": temperature,
            },
            timeout=self._timeout,
        )
        response.raise_for_status()
        data = response.json()
        latency_ms = round((time.perf_counter() - start) * 1000, 4)
        usage = data.get("usage", {})
        content = "".join(block.get("text", "") for block in data.get("content", []))
        return ProviderResult(
            output=content,
            input_tokens=usage.get("input_tokens", 0),
            output_tokens=usage.get("output_tokens", 0),
            latency_ms=latency_ms,
            raw_metadata={"provider": "anthropic", "id": data.get("id")},
        )
