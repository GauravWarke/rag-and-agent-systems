"""Queryable record of routing quality checks.

Each entry compares a cheap model's response against a stronger reference
model's response for the same prompt. Entries with a low similarity score
are "routing misses" — evidence that the cheaper model produced a
materially different answer than the strong model would have. The miss
rate per feature is what `should_escalate` uses as the system's own
notion of "confidence" in routing a feature to a cheap model.
"""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel


class QualityCheckEntry(BaseModel):
    request_id: str
    timestamp: datetime
    team_id: str
    feature: str
    cheap_model: str
    reference_model: str
    similarity_score: float
    is_routing_miss: bool
    prompt_preview: str
    reason: str | None = None


class QualityStore:
    def __init__(self) -> None:
        self._entries: list[QualityCheckEntry] = []

    def log(self, entry: QualityCheckEntry) -> None:
        self._entries.append(entry)

    def all(self) -> list[QualityCheckEntry]:
        return list(self._entries)

    def misses(self) -> list[QualityCheckEntry]:
        return [e for e in self._entries if e.is_routing_miss]

    def _for_feature(self, feature: str) -> list[QualityCheckEntry]:
        return [e for e in self._entries if e.feature == feature]

    def sample_count_for_feature(self, feature: str) -> int:
        return len(self._for_feature(feature))

    def miss_rate_for_feature(self, feature: str) -> float:
        entries = self._for_feature(feature)
        if not entries:
            return 0.0
        return sum(1 for e in entries if e.is_routing_miss) / len(entries)

    def should_escalate(self, feature: str, min_samples: int, miss_rate_threshold: float) -> bool:
        """True once a feature has enough sampled checks and too many of
        them were routing misses — i.e. the cheap model has recently been
        unreliable for this feature often enough to distrust it again."""
        return (
            self.sample_count_for_feature(feature) >= min_samples
            and self.miss_rate_for_feature(feature) >= miss_rate_threshold
        )

    def pass_rate(self) -> float:
        if not self._entries:
            return 1.0
        return 1 - (len(self.misses()) / len(self._entries))
