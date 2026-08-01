"""Feature-level override rules: some features must always use a
stronger model because correctness matters more than cost, regardless
of what the classifier would otherwise pick.
"""
from __future__ import annotations

from pathlib import Path

import yaml


class RoutingOverrides:
    def __init__(self, feature_forced_tier: dict[str, int]) -> None:
        self._forced = feature_forced_tier

    @classmethod
    def load(cls, path: str | Path) -> RoutingOverrides:
        data = yaml.safe_load(Path(path).read_text()) or {}
        return cls(dict(data.get("feature_forced_tier", {})))

    def forced_tier(self, feature: str) -> int | None:
        return self._forced.get(feature)
