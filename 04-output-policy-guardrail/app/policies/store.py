"""Policy definitions, loaded from YAML so policies are auditable and
changeable without touching code.

Each policy declares its own `detection_strategy` — deterministic checks
are cheap and should catch clear violations before any LLM judge call
runs (see `app/validators/`); `llm_judge` and `both` policies also (or
only) go through `app/judge/`.
"""
from __future__ import annotations

from pathlib import Path

import yaml
from pydantic import BaseModel

from app.core.models import DecisionOutcome, Severity

DetectionStrategy = str  # "deterministic" | "llm_judge" | "both"


class Policy(BaseModel):
    id: str
    name: str
    category: str
    severity: Severity
    description: str
    examples: list[str] = []
    detection_strategy: DetectionStrategy
    recommended_action: DecisionOutcome


class PolicyStore:
    def __init__(self, policies: list[Policy]) -> None:
        self._by_id = {p.id: p for p in policies}

    @classmethod
    def load(cls, path: str | Path) -> PolicyStore:
        data = yaml.safe_load(Path(path).read_text()) or {}
        policies = [Policy.model_validate(p) for p in data.get("policies", [])]
        return cls(policies)

    def all(self) -> list[Policy]:
        return list(self._by_id.values())

    def get(self, policy_id: str) -> Policy | None:
        return self._by_id.get(policy_id)

    def by_strategy(self, strategy: str) -> list[Policy]:
        """Policies whose detection_strategy is `strategy` or "both"."""
        return [p for p in self._by_id.values() if p.detection_strategy in (strategy, "both")]
