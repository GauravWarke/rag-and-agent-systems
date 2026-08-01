"""Offline, keyless provider used by default so the whole gateway — routing,
budgets, cost tracking — is testable without any provider API key.

Deterministic and dependency-free: given the same messages and model it
always returns the same output, which keeps tests stable.
"""
from __future__ import annotations

import time
from collections.abc import Sequence

from app.core.models import ChatMessage

from .base import ProviderAdapter, ProviderResult


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


class StubAdapter(ProviderAdapter):
    name = "stub"

    def complete(
        self,
        messages: Sequence[ChatMessage],
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> ProviderResult:
        start = time.perf_counter()
        prompt_text = "\n".join(f"{m.role}: {m.content}" for m in messages)
        last_user = next((m.content for m in reversed(messages) if m.role == "user"), "")
        output = f"[{model}] Acknowledged: {last_user.strip()[:200]}"
        output = output[: max(1, max_tokens) * 4]
        latency_ms = round((time.perf_counter() - start) * 1000, 4)
        return ProviderResult(
            output=output,
            input_tokens=_estimate_tokens(prompt_text),
            output_tokens=_estimate_tokens(output),
            latency_ms=latency_ms,
            raw_metadata={"provider": "stub"},
        )
