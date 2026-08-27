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
