"""Sampled routing verification.

For a share of requests answered by a cheaper model, replay the same
prompt against the strongest available model and compare the two
outputs. This runs as a FastAPI background task so it never adds latency
to the user-facing response — the whole point of routing to a cheap model
in the first place.
"""
from __future__ import annotations

from collections.abc import Callable, Sequence
from datetime import datetime, timezone

from app.core.models import ChatMessage
from app.providers.base import ProviderAdapter
from app.quality.judge import score_similarity
from app.quality.store import QualityCheckEntry, QualityStore
from app.registry.models import ModelRegistry


class QualityVerifier:
    def __init__(
        self,
        model_registry: ModelRegistry,
        quality_store: QualityStore,
        get_adapter: Callable[[str], ProviderAdapter],
        available_providers: Callable[[], set[str]],
        similarity_threshold: float,
    ) -> None:
        self._model_registry = model_registry
        self._quality_store = quality_store
        self._get_adapter = get_adapter
        self._available_providers = available_providers
        self._similarity_threshold = similarity_threshold

    def verify(
        self,
        *,
        request_id: str,
        team_id: str,
        feature: str,
        messages: Sequence[ChatMessage],
        cheap_model_name: str,
        cheap_output: str,
        max_tokens: int,
        temperature: float,
    ) -> None:
        try:
            reference_model = self._model_registry.default_for_tier(3, self._available_providers())
        except KeyError:
            return  # no stronger model available to verify against
        if reference_model.name == cheap_model_name:
            return

        adapter = self._get_adapter(reference_model.provider)
        try:
            reference = adapter.complete(messages, reference_model.name, max_tokens, temperature)
        except (RuntimeError, ValueError):
            return  # reference call failed; don't let that look like a routing miss

        score = score_similarity(cheap_output, reference.output)
        is_miss = score < self._similarity_threshold
        last_user = next((m.content for m in reversed(messages) if m.role == "user"), "")

        self._quality_store.log(
            QualityCheckEntry(
                request_id=request_id,
                timestamp=datetime.now(timezone.utc),
                team_id=team_id,
                feature=feature,
                cheap_model=cheap_model_name,
                reference_model=reference_model.name,
                similarity_score=score,
                is_routing_miss=is_miss,
                prompt_preview=last_user.strip()[:200],
                reason=(
                    f"similarity {score:.2f} below threshold {self._similarity_threshold:.2f}"
                    if is_miss
                    else None
                ),
            )
        )
