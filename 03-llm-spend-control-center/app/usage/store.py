"""Queryable audit trail of every gateway request.

In-memory for this demo; a production deployment would back this with a
table (e.g. Postgres) so the log survives restarts and scales past one
process, but the query surface (`spend_today`, `spend_month`,
`spend_by_*`) would stay the same.
"""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Literal

from pydantic import BaseModel


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
