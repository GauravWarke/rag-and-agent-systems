"""Model registry: name, provider, quality tier, pricing, and capabilities.

Loaded once from a YAML file so adding or repricing a model is a config
change, not a code change.
"""
from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel


class ModelSpec(BaseModel):
    name: str
    provider: str
    quality_tier: int
    input_cost_per_million: float
    output_cost_per_million: float
    latency_estimate_ms: float
    max_context_tokens: int
    supports_vision: bool = False
    supports_tools: bool = False


class ModelRegistry:
    def __init__(self, models: list[ModelSpec]) -> None:
        self._by_name = {m.name: m for m in models}

    @classmethod
    def load(cls, path: str | Path) -> ModelRegistry:
        data = yaml.safe_load(Path(path).read_text()) or {}
        return cls([ModelSpec.model_validate(m) for m in data.get("models", [])])

    def get(self, name: str) -> ModelSpec:
        try:
            return self._by_name[name]
        except KeyError:
            raise KeyError(f"Model '{name}' is not in the registry") from None

    def all(self) -> list[ModelSpec]:
        return list(self._by_name.values())

    def models_for_tier(self, tier: int) -> list[ModelSpec]:
        return [m for m in self._by_name.values() if m.quality_tier == tier]

    def default_for_tier(self, tier: int, available_providers: set[str] | None = None) -> ModelSpec:
        candidates = self.models_for_tier(tier)
        if available_providers is not None:
            candidates = [m for m in candidates if m.provider in available_providers]
        candidates = sorted(candidates, key=lambda m: m.input_cost_per_million)
        if not candidates:
            raise KeyError(f"No available models registered for tier {tier}")
        return candidates[0]


def estimate_cost(model: ModelSpec, input_tokens: int, output_tokens: int) -> float:
    cost = (input_tokens * model.input_cost_per_million + output_tokens * model.output_cost_per_million) / 1_000_000
    return round(cost, 8)
