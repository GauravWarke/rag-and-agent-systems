from app.core.models import ChatMessage, GatewayRequest
from app.routing.overrides import RoutingOverrides
from app.routing.router import select_tier


def _request(content: str, feature: str = "generic-feature", risk_tags=None) -> GatewayRequest:
    return GatewayRequest(
        messages=[ChatMessage(role="user", content=content)],
        team_id="team-alpha",
        feature=feature,
        risk_tags=risk_tags or [],
    )


def test_select_tier_uses_classifier_when_no_override():
    overrides = RoutingOverrides({})
    req = _request("Extract the order ID from this email.")
    assert select_tier(req, overrides) == 1


def test_select_tier_override_wins_over_classifier():
    overrides = RoutingOverrides({"legal-review": 3})
    req = _request("Extract the order ID from this email.", feature="legal-review")
    assert select_tier(req, overrides) == 3
