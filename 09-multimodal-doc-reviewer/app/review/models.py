"""Side-by-side review packet (Phase 5, step 1).

Bundles everything a human reviewer needs to judge one document in a
single response: the page thumbnails to look at, the extracted fields to
check, and the validation issues that explain why the document landed in
the queue. Every field value already carries the page number it came from
(`SourcedValue.page_number`, set during extraction) — a review UI uses
that to jump to / highlight the right page image, so no separate
click-to-source mapping needs to be built here.
"""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.core.models import ConfidenceLevel, DocumentType, RoutingDecision
from app.validation.models import ValidationIssue


class ReviewPageSummary(BaseModel):
    page_number: int
    has_image: bool
    image_url: str | None = None


class ReviewPacket(BaseModel):
    document_id: str
    filename: str
    document_type: DocumentType
    pages: list[ReviewPageSummary]
    fields: dict[str, Any]
    conflicts: list[dict[str, Any]] = Field(default_factory=list)
    confidence: ConfidenceLevel
    routing: RoutingDecision
    issues: list[ValidationIssue] = Field(default_factory=list)


class CorrectionRequest(BaseModel):
    """Body for submitting a reviewer's fix to one extracted field."""

    field: str
    corrected_value: Any
    reviewer: str
    reason: str | None = None


class FieldCorrection(BaseModel):
    """A stored reviewer correction (Phase 5, step 2): what the extractor
    produced, what the reviewer changed it to, and who/why — the audit
    trail that field-accuracy analytics (step 3) is computed from.
    """

    document_id: str
    field: str
    original_value: Any = None
    corrected_value: Any
    reviewer: str
    reason: str | None = None
    corrected_at: str


class FieldAccuracyStat(BaseModel):
    field: str
    correction_count: int


class ReviewAnalytics(BaseModel):
    """Aggregate review-queue health across every ingested document
    (Phase 5, step 3): auto-approval rate, how long human review takes,
    and which fields the extractor gets wrong most often.
    """

    total_documents: int
    auto_approved: int
    needs_review: int
    auto_approval_rate: float
    total_corrections: int
    average_review_time_seconds: float | None = None
    field_accuracy: list[FieldAccuracyStat] = Field(default_factory=list)
