"""Evaluates current spend against budget policies and decides
warn/block behavior.

A request is checked against both its team's policy and its feature's
policy (if one is configured) — whichever is closer to its limit wins,
so a well-behaved team can still be blocked by an over-budget feature
and vice versa.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal

from app.budgets.policy import BudgetPolicy, BudgetPolicyStore
from app.usage.store import UsageStore

BudgetStatus = Literal["ok", "warning", "blocked"]

_STATUS_RANK: dict[BudgetStatus, int] = {"ok": 0, "warning": 1, "blocked": 2}


@dataclass
class BudgetCheckResult:
    status: BudgetStatus
    scope: str
    key: str
    pct_used: float
    spent_usd: float
    limit_usd: float


class BudgetTracker:
    def __init__(
        self,
        usage_store: UsageStore,
        policy_store: BudgetPolicyStore,
        warning_threshold_pct: float = 80.0,
    ) -> None:
        self._usage = usage_store
        self._policies = policy_store
        self._warning_threshold = warning_threshold_pct / 100.0

    def check(self, team_id: str, feature: str, now: datetime | None = None) -> BudgetCheckResult:
        results = [self._check_scope("team", team_id, self._policies.for_team(team_id), now)]
        feature_policy = self._policies.for_feature(feature)
        if feature_policy is not None:
            results.append(self._check_scope("feature", feature, feature_policy, now))
        return max(results, key=lambda r: (_STATUS_RANK[r.status], r.pct_used))

    def _check_scope(
        self,
        scope: Literal["team", "feature"],
        key: str,
        policy: BudgetPolicy,
        now: datetime | None,
    ) -> BudgetCheckResult:
        daily_spent = self._usage.spend_today(scope, key, now)
        monthly_spent = self._usage.spend_month(scope, key, now)
        daily_pct = daily_spent / policy.daily_limit_usd if policy.daily_limit_usd > 0 else 0.0
        monthly_pct = monthly_spent / policy.monthly_limit_usd if policy.monthly_limit_usd > 0 else 0.0

        if daily_pct >= monthly_pct:
            pct, spent, limit = daily_pct, daily_spent, policy.daily_limit_usd
        else:
            pct, spent, limit = monthly_pct, monthly_spent, policy.monthly_limit_usd

        if pct >= 1.0:
            status: BudgetStatus = "blocked"
        elif pct >= self._warning_threshold:
            status = "warning"
        else:
            status = "ok"

        return BudgetCheckResult(status=status, scope=scope, key=key, pct_used=pct, spent_usd=spent, limit_usd=limit)
