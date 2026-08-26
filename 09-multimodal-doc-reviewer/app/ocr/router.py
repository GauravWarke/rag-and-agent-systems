"""OCR endpoint (Phase 2): run the OCR + vision-fallback pipeline over
every page of a previously uploaded document.
"""
from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.rate_limit import enforce_rate_limit
from app.intake.store import document_store
from app.ocr.models import DocumentOcrResult
from app.ocr.pipeline import process_document
from app.ocr.store import ocr_result_store

router = APIRouter(prefix="/v1/documents", tags=["ocr"], dependencies=[Depends(enforce_rate_limit)])


@router.post("/{document_id}/ocr", response_model=DocumentOcrResult)
def run_document_ocr(document_id: str) -> DocumentOcrResult:
    document = document_store.get(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail=f"No document with id '{document_id}'.")

    result = process_document(document)
    return ocr_result_store.set(document_id, result)
