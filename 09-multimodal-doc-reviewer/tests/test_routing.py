from app.core.models import ConfidenceLevel, RoutingDecision
from app.validation.models import ValidationIssue
from app.validation.routing import route_by_confidence


def test_no_issues_routes_high_confidence_auto_approved():
    confidence, routing = route_by_confidence([])
    assert confidence == ConfidenceLevel.HIGH
    assert routing == RoutingDecision.AUTO_APPROVED


def test_warning_only_routes_medium_confidence_needs_review():
    confidence, routing = route_by_confidence(
        [ValidationIssue(field="vendor", severity="warning", message="unknown vendor")]
    )
    assert confidence == ConfidenceLevel.MEDIUM
    assert routing == RoutingDecision.NEEDS_REVIEW


def test_error_routes_low_confidence_needs_review():
    confidence, routing = route_by_confidence(
        [
            ValidationIssue(field="vendor", severity="warning", message="unknown vendor"),
            ValidationIssue(field="total", severity="error", message="missing"),
        ]
    )
    assert confidence == ConfidenceLevel.LOW
    assert routing == RoutingDecision.NEEDS_REVIEW
