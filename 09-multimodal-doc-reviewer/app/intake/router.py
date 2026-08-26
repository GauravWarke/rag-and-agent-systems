"""Document upload endpoints (Phase 1): accept a file, load and normalize
its pages, classify the document type, and store the result for the
downstream OCR (Phase 2) and extraction (Phase 3) stages.
"""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from app.core.rate_limit import enforce_rate_limit
from app.intake.classifier import classify_document
from app.intake.loaders import SUPPORTED_CONTENT_TYPES, load_pages
from app.intake.models import Document
from app.intake.store import document_store

router = APIRouter(prefix="/v1/documents", tags=["documents"], dependencies=[Depends(enforce_rate_limit)])

MAX_UPLOAD_BYTES = 20 * 1024 * 1024
_UPLOAD_FILE_PARAM = File(...)


@router.post("", response_model=Document, status_code=201)
async def upload_document(file: UploadFile = _UPLOAD_FILE_PARAM) -> Document:
    if file.content_type not in SUPPORTED_CONTENT_TYPES:
        raise HTTPException(
            status_code=415,
            detail=f"unsupported content type '{file.content_type}'; use one of {sorted(SUPPORTED_CONTENT_TYPES)}",
        )

    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="empty file")
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=413, detail=f"file exceeds the {MAX_UPLOAD_BYTES} byte upload limit")

    try:
        pages = load_pages(data, content_type=file.content_type)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    doc_type, confidence = classify_document(file.filename or "", pages)
    document = Document(
        id=str(uuid4()),
        filename=file.filename or "unknown",
        content_type=file.content_type,
        uploaded_at=datetime.now(timezone.utc).isoformat(),
        document_type=doc_type,
        document_type_confidence=confidence,
        pages=pages,
    )
    return document_store.add(document)


@router.get("", response_model=list[Document])
def list_documents() -> list[Document]:
    return document_store.all()


@router.get("/{document_id}", response_model=Document)
def get_document(document_id: str) -> Document:
    document = document_store.get(document_id)
    if document is None:
        raise HTTPException(status_code=404, detail=f"No document with id '{document_id}'.")
    return document
