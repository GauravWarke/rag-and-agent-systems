"""Validation and routing result models (Phase 4)."""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.core.models import ConfidenceLevel, DocumentType, RoutingDecision


class ValidationIssue(BaseModel):
    field: str | None = None
    severity: Literal["error", "warning"]
    message: str


class ValidationResult(BaseModel):
    document_id: str
    document_type: DocumentType
    confidence: ConfidenceLevel
    routing: RoutingDecision
    issues: list[ValidationIssue] = Field(default_factory=list)
