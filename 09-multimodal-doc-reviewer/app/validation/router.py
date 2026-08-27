"""Validation and routing endpoint (Phase 4): run type validation and
business rules over a document's extracted fields, then route it to
auto-approval or human review based on the resulting confidence level.
Runs extraction first if it hasn't already.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.rate_limit import enforce_rate_limit
from app.extraction.router import extract_document
from app.extraction.store import extraction_result_store
from app.intake.store import document_store
from app.validation.models import ValidationResult
from app.validation.routing import route_by_confidence
from app.validation.rules import validate_business_rules, validate_type
from app.validation.store import validation_result_store

router = APIRouter(prefix="/v1/documents", tags=["validation"], dependencies=[Depends(enforce_rate_limit)])


@router.post("/{document_id}/validate", response_model=ValidationResult)
def validate_document(document_id: str) -> ValidationResult:
    document = document_store.get(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail=f"No document with id '{document_id}'.")

    extraction_result = extraction_result_store.get(document_id)
    if extraction_result is None:
        extraction_result = extract_document(document_id)

    issues = validate_type(document.document_type, extraction_result.fields) + validate_business_rules(
        document.document_type, extraction_result.fields
    )
    confidence, routing = route_by_confidence(issues)

    result = ValidationResult(
        document_id=document_id,
        document_type=document.document_type,
        confidence=confidence,
        routing=routing,
        issues=issues,
    )
    return validation_result_store.set(document_id, result)
