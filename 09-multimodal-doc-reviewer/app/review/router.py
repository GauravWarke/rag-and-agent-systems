"""Review endpoints: Phase 5 step 1 serves the side-by-side packet a
reviewer needs (page images + extracted fields + validation issues) and
the raw page image bytes referenced by it, step 2 lets a reviewer submit
a correction for one field, and step 3 exposes queue-wide accuracy
analytics. Runs validation (which itself runs extraction) first if it
hasn't already.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response

from app.core.rate_limit import enforce_rate_limit
from app.extraction.store import extraction_result_store
from app.intake.store import document_store
from app.review.analytics import compute_review_analytics
from app.review.models import (
    CorrectionRequest,
    FieldCorrection,
    ReviewAnalytics,
    ReviewPacket,
    ReviewPageSummary,
)
from app.review.store import correction_store
from app.validation.router import validate_document
from app.validation.store import validation_result_store

router = APIRouter(prefix="/v1/documents", tags=["review"], dependencies=[Depends(enforce_rate_limit)])
analytics_router = APIRouter(prefix="/v1/review", tags=["review"], dependencies=[Depends(enforce_rate_limit)])


def _get_document_or_404(document_id: str):
    document = document_store.get(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail=f"No document with id '{document_id}'.")
    return document


@router.get("/{document_id}/review", response_model=ReviewPacket)
def get_review_packet(document_id: str) -> ReviewPacket:
    document = _get_document_or_404(document_id)

    validation_result = validation_result_store.get(document_id)
    if validation_result is None:
        validation_result = validate_document(document_id)

    extraction_result = extraction_result_store.get(document_id)
    fields = extraction_result.fields if extraction_result else {}
    conflicts = [c.model_dump() for c in extraction_result.conflicts] if extraction_result else []

    pages = [
        ReviewPageSummary(
            page_number=page.page_number,
            has_image=page.has_normalized_image,
            image_url=f"/v1/documents/{document_id}/pages/{page.page_number}/image"
            if page.has_normalized_image
            else None,
        )
        for page in document.pages
    ]

    return ReviewPacket(
        document_id=document_id,
        filename=document.filename,
        document_type=document.document_type,
        pages=pages,
        fields=fields,
        conflicts=conflicts,
        confidence=validation_result.confidence,
        routing=validation_result.routing,
        issues=validation_result.issues,
    )


@router.get("/{document_id}/pages/{page_number}/image")
def get_page_image(document_id: str, page_number: int) -> Response:
    document = _get_document_or_404(document_id)

    page = next((p for p in document.pages if p.page_number == page_number), None)
    if page is None:
        raise HTTPException(status_code=404, detail=f"Document '{document_id}' has no page {page_number}.")
    if page.normalized_image_png is None:
        raise HTTPException(status_code=404, detail=f"Page {page_number} has no normalized image available.")

    return Response(content=page.normalized_image_png, media_type="image/png")


@router.post("/{document_id}/review/corrections", response_model=FieldCorrection, status_code=201)
def submit_correction(document_id: str, correction: CorrectionRequest) -> FieldCorrection:
    _get_document_or_404(document_id)

    extraction_result = extraction_result_store.get(document_id)
    if extraction_result is None:
        raise HTTPException(
            status_code=409, detail=f"Document '{document_id}' has not been extracted yet; nothing to correct."
        )
    if correction.field not in extraction_result.fields:
        raise HTTPException(
            status_code=400,
            detail=f"'{correction.field}' is not a field of document type '{extraction_result.document_type.value}'.",
        )

    original_value = extraction_result.fields[correction.field]
    if original_value is None or isinstance(original_value, dict):
        page_number = original_value.get("page_number", 0) if isinstance(original_value, dict) else 0
        extraction_result.fields[correction.field] = {
            "value": correction.corrected_value,
            "page_number": page_number,
            "source": "human_correction",
        }
    else:
        extraction_result.fields[correction.field] = correction.corrected_value
    extraction_result_store.set(document_id, extraction_result)

    record = FieldCorrection(
        document_id=document_id,
        field=correction.field,
        original_value=original_value,
        corrected_value=correction.corrected_value,
        reviewer=correction.reviewer,
        reason=correction.reason,
        corrected_at=datetime.now(timezone.utc).isoformat(),
    )
    return correction_store.add(record)


@router.get("/{document_id}/review/corrections", response_model=list[FieldCorrection])
def list_corrections(document_id: str) -> list[FieldCorrection]:
    _get_document_or_404(document_id)
    return correction_store.list_for(document_id)


@analytics_router.get("/analytics", response_model=ReviewAnalytics)
def get_review_analytics() -> ReviewAnalytics:
    return compute_review_analytics()
