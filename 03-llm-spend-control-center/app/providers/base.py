"""Common interface every provider adapter implements.

The gateway only ever talks to `ProviderAdapter.complete(...)` — it never
knows or cares whether the underlying call hit a real API or the offline
stub. That's what lets model routing (Phase 3) swap providers freely.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from collections.abc import Sequence
from dataclasses import dataclass

from app.core.models import ChatMessage


@dataclass
class ProviderResult:
    output: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    raw_metadata: dict


class ProviderAdapter(ABC):
    name: str

    @abstractmethod
    def complete(
        self,
        messages: Sequence[ChatMessage],
        model: str,
        max_tokens: int,
        temperature: float,
    ) -> ProviderResult:
        """Run a chat completion and return a normalized ProviderResult."""
