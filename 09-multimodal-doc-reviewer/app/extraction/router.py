"""Structured extraction endpoint (Phase 3): merge each page's text into
one document-level result, validated against the schema for the
document's type. Runs the OCR pipeline first if it hasn't already.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.rate_limit import enforce_rate_limit
from app.extraction.merge import merge_page_extractions
from app.extraction.models import ExtractionResult
from app.extraction.store import extraction_result_store
from app.intake.store import document_store
from app.ocr.pipeline import process_document
from app.ocr.store import ocr_result_store

router = APIRouter(prefix="/v1/documents", tags=["extraction"], dependencies=[Depends(enforce_rate_limit)])


@router.post("/{document_id}/extract", response_model=ExtractionResult)
def extract_document(document_id: str) -> ExtractionResult:
    document = document_store.get(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail=f"No document with id '{document_id}'.")

    ocr_result = ocr_result_store.get(document_id)
    if ocr_result is None:
        ocr_result = ocr_result_store.set(document_id, process_document(document))

    pages = [(p.page_number, p.source, p.text) for p in ocr_result.pages if p.text.strip()]
    schema, conflicts = merge_page_extractions(document.document_type, pages)
    if schema is None:
        raise HTTPException(
            status_code=422,
            detail=f"No extraction schema defined for document type '{document.document_type.value}'.",
        )

    result = ExtractionResult(
        document_id=document_id,
        document_type=document.document_type,
        fields=schema.model_dump(),
        conflicts=conflicts,
    )
    return extraction_result_store.set(document_id, result)
