"""Queryable audit trail of every gateway request.

In-memory for this demo; a production deployment would back this with a
table (e.g. Postgres) so the log survives restarts and scales past one
process, but the query surface (`spend_today`, `spend_month`,
`spend_by_*`) would stay the same.
"""
from __future__ import annotations

import calendar
from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel

from app.registry.models import ModelSpec, estimate_cost


class UsageLogEntry(BaseModel):
    request_id: str
    timestamp: datetime
    team_id: str
    feature: str
    model: str
    provider: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    status: Literal["ok", "error"]
    cost_usd: float
    escalated: bool = False


class UsageStore:
    def __init__(self) -> None:
        self._entries: list[UsageLogEntry] = []

    def log(self, entry: UsageLogEntry) -> None:
        self._entries.append(entry)

    def all(self) -> list[UsageLogEntry]:
        return list(self._entries)

    def _by_scope(self, scope: Literal["team", "feature"], key: str) -> list[UsageLogEntry]:
        attr = "team_id" if scope == "team" else "feature"
        return [e for e in self._entries if getattr(e, attr) == key]

    def spend_today(self, scope: Literal["team", "feature"], key: str, now: datetime | None = None) -> float:
        now = now or datetime.now(timezone.utc)
        return sum(e.cost_usd for e in self._by_scope(scope, key) if e.timestamp.date() == now.date())

    def spend_month(self, scope: Literal["team", "feature"], key: str, now: datetime | None = None) -> float:
        now = now or datetime.now(timezone.utc)
        return sum(
            e.cost_usd
            for e in self._by_scope(scope, key)
            if (e.timestamp.year, e.timestamp.month) == (now.year, now.month)
        )

    def spend_by_team(self) -> dict[str, float]:
        totals: dict[str, float] = {}
        for e in self._entries:
            totals[e.team_id] = totals.get(e.team_id, 0.0) + e.cost_usd
        return totals

    def spend_by_feature(self) -> dict[str, float]:
        totals: dict[str, float] = {}
        for e in self._entries:
            totals[e.feature] = totals.get(e.feature, 0.0) + e.cost_usd
        return totals

    def spend_by_model(self) -> dict[str, float]:
        totals: dict[str, float] = {}
        for e in self._entries:
            totals[e.model] = totals.get(e.model, 0.0) + e.cost_usd
        return totals

    def spend_today_total(self, now: datetime | None = None) -> float:
        now = now or datetime.now(timezone.utc)
        return sum(e.cost_usd for e in self._entries if e.timestamp.date() == now.date())

    def spend_month_total(self, now: datetime | None = None) -> float:
        now = now or datetime.now(timezone.utc)
        return sum(
            e.cost_usd for e in self._entries if (e.timestamp.year, e.timestamp.month) == (now.year, now.month)
        )

    def monthly_projection(self, now: datetime | None = None) -> float:
        """Naive run-rate projection: month-to-date spend scaled by how much
        of the month is left, assuming the daily rate holds steady."""
        now = now or datetime.now(timezone.utc)
        days_in_month = calendar.monthrange(now.year, now.month)[1]
        month_to_date = self.spend_month_total(now)
        return round(month_to_date / now.day * days_in_month, 8)

    def top_expensive(self, limit: int = 10) -> list[dict]:
        ranked = sorted(self._entries, key=lambda e: e.cost_usd, reverse=True)[:limit]
        return [
            {
                "request_id": e.request_id,
                "team_id": e.team_id,
                "feature": e.feature,
                "model": e.model,
                "cost_usd": e.cost_usd,
                "timestamp": e.timestamp.isoformat(),
            }
            for e in ranked
        ]

    def savings_estimate(self, strongest_model: ModelSpec) -> dict:
        """Compare actual routed spend with what the same requests would
        have cost had every one of them been sent to `strongest_model`."""
        ok_entries = [e for e in self._entries if e.status == "ok"]
        actual = sum(e.cost_usd for e in ok_entries)
        hypothetical = sum(estimate_cost(strongest_model, e.input_tokens, e.output_tokens) for e in ok_entries)
        savings = hypothetical - actual
        return {
            "strongest_model": strongest_model.name,
            "request_count": len(ok_entries),
            "actual_cost_usd": round(actual, 8),
            "hypothetical_strongest_model_cost_usd": round(hypothetical, 8),
            "savings_usd": round(savings, 8),
            "savings_pct": round(savings / hypothetical, 6) if hypothetical else 0.0,
        }

    def escalation_rate(self) -> float:
        if not self._entries:
            return 0.0
        return sum(1 for e in self._entries if e.escalated) / len(self._entries)

    def latency_by_model(self) -> dict[str, float]:
        totals: dict[str, list[float]] = {}
        for e in self._entries:
            if e.status != "ok":
                continue
            totals.setdefault(e.model, []).append(e.latency_ms)
        return {model: round(sum(values) / len(values), 4) for model, values in totals.items()}

    def error_rate_by_provider(self) -> dict[str, float]:
        totals: dict[str, list[bool]] = {}
        for e in self._entries:
            totals.setdefault(e.provider, []).append(e.status == "error")
        return {provider: round(sum(flags) / len(flags), 6) for provider, flags in totals.items()}
