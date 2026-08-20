"""Evaluate a scorecard against alert rules and dispatch anything that fires."""
from __future__ import annotations

from datetime import UTC, datetime

from app.alerts.client import AlertClient
from app.alerts.rules import build_alerts
from app.core.models import AlertDispatchResult, FreshnessScorecard


def dispatch_alerts(scorecard: FreshnessScorecard, client: AlertClient) -> AlertDispatchResult:
    triggered = build_alerts(scorecard)
    delivered = all(client.send(message) for message in triggered) if triggered else True
    return AlertDispatchResult(
        checked_at=datetime.now(UTC).isoformat(),
        triggered=triggered,
        channel=client.name,
        delivered=delivered,
    )
