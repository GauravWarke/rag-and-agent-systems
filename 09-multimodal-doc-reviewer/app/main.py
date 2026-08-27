"""Multimodal Document Intake Reviewer — accepts scanned forms, PDFs, and
images; extracts structured fields; validates them; and routes
low-confidence results to a human review queue.

Endpoints:
  GET  /health                              readiness probe
  POST /v1/documents                        upload a document (PDF/PNG/JPEG/TIFF)
  GET  /v1/documents                        list uploaded documents
  GET  /v1/documents/{id}                   fetch one document (pages, preprocessing metadata)
  POST /v1/documents/{id}/ocr               run OCR + vision fallback over every page
  POST /v1/documents/{id}/extract           extract structured fields (runs OCR first if needed)
  POST /v1/documents/{id}/validate           validate fields and route to auto-approve/review
  GET  /v1/documents/{id}/review             side-by-side review packet (pages + fields + issues)
  GET  /v1/documents/{id}/pages/{n}/image    normalized page image (PNG)
"""
from __future__ import annotations

from fastapi import FastAPI

from app.extraction.router import router as extraction_router
from app.intake.router import router as intake_router
from app.ocr.router import router as ocr_router
from app.review.router import router as review_router
from app.validation.router import router as validation_router

app = FastAPI(title="Multimodal Document Intake Reviewer", version="0.1.0")

app.include_router(intake_router)
app.include_router(ocr_router)
app.include_router(extraction_router)
app.include_router(validation_router)
app.include_router(review_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
