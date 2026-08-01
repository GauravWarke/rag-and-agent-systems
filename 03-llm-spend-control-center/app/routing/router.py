"""Combines the complexity classifier and override rules into one
tier decision for a gateway request."""
from __future__ import annotations

from app.core.models import GatewayRequest
from app.routing.classifier import classify_complexity
from app.routing.overrides import RoutingOverrides


def select_tier(req: GatewayRequest, overrides: RoutingOverrides) -> int:
    forced = overrides.forced_tier(req.feature)
    if forced is not None:
        return forced
    combined_text = " ".join(m.content for m in req.messages)
    return classify_complexity(combined_text, req.risk_tags)
