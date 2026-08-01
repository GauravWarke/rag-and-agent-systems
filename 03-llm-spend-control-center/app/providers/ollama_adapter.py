"""Ollama local-server adapter, for self-hosted models.

Talks to a local Ollama server (`OLLAMA_BASE_URL`). Not exercised by the
test suite (offline-by-default convention) — requires a running server.
"""
from __future__ import annotations

import time
from collections.abc import Sequence

import httpx

from app.core.models import ChatMessage

from .base import ProviderAdapter, ProviderResult


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


class OllamaAdapter(ProviderAdapter):
    name = "ollama"

    def __init__(self, base_url: str = "http://localhost:11434", timeout: float = 60.0) -> None:
        self._base_url = base_url
        self._timeout = timeout

    def complete(
        self,
        messages: Sequence[ChatMessage],
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> ProviderResult:
        start = time.perf_counter()
        try:
            response = httpx.post(
                f"{self._base_url}/api/chat",
                json={
                    "model": model,
                    "messages": [m.model_dump() for m in messages],
                    "stream": False,
                    "options": {"temperature": temperature, "num_predict": max_tokens},
                },
                timeout=self._timeout,
            )
            response.raise_for_status()
        except httpx.HTTPError as exc:
            raise RuntimeError(f"Ollama server unreachable at {self._base_url}: {exc}") from exc
        data = response.json()
        latency_ms = round((time.perf_counter() - start) * 1000, 4)
        content = data.get("message", {}).get("content", "")
        return ProviderResult(
            output=content,
            input_tokens=data.get("prompt_eval_count", _estimate_tokens(content)),
            output_tokens=data.get("eval_count", _estimate_tokens(content)),
            latency_ms=latency_ms,
            raw_metadata={"provider": "ollama"},
        )
