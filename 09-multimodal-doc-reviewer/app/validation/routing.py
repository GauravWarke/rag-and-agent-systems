"""Route a document by validation confidence (Phase 4, step 3).

No errors at all -> high confidence, auto-approved. Only warnings (e.g. an
unrecognized vendor) -> medium confidence, sent to review. Any error
(missing required field, unparseable date, failed business rule) -> low
confidence, sent to review. Only "high" skips human review.
"""
from __future__ import annotations

from app.core.models import ConfidenceLevel, RoutingDecision
from app.validation.models import ValidationIssue


def route_by_confidence(issues: list[ValidationIssue]) -> tuple[ConfidenceLevel, RoutingDecision]:
    if any(issue.severity == "error" for issue in issues):
        return ConfidenceLevel.LOW, RoutingDecision.NEEDS_REVIEW
    if any(issue.severity == "warning" for issue in issues):
        return ConfidenceLevel.MEDIUM, RoutingDecision.NEEDS_REVIEW
    return ConfidenceLevel.HIGH, RoutingDecision.AUTO_APPROVED
