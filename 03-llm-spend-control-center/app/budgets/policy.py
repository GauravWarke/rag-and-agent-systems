"""Budget policies: daily/monthly spend limits per team or feature."""
from __future__ import annotations

from pathlib import Path
from typing import Literal

import yaml
from pydantic import BaseModel


class BudgetPolicy(BaseModel):
    scope: Literal["team", "feature"]
    key: str
    daily_limit_usd: float
    monthly_limit_usd: float


class BudgetPolicyStore:
    def __init__(self, policies: list[BudgetPolicy], default: BudgetPolicy) -> None:
        self._team_policies = {p.key: p for p in policies if p.scope == "team"}
        self._feature_policies = {p.key: p for p in policies if p.scope == "feature"}
        self._default = default

    @classmethod
    def load(cls, path: str | Path) -> BudgetPolicyStore:
        data = yaml.safe_load(Path(path).read_text()) or {}
        policies = [BudgetPolicy.model_validate(p) for p in data.get("policies", [])]
        default_data = data.get("default", {"daily_limit_usd": 1.0, "monthly_limit_usd": 20.0})
        default = BudgetPolicy(scope="team", key="__default__", **default_data)
        return cls(policies, default)

    def for_team(self, team_id: str) -> BudgetPolicy:
        return self._team_policies.get(team_id, self._default)

    def for_feature(self, feature: str) -> BudgetPolicy | None:
        return self._feature_policies.get(feature)
