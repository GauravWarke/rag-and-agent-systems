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
  POST /v1/documents/{id}/review/corrections submit a reviewer's fix for one field
  GET  /v1/documents/{id}/review/corrections list corrections submitted for a document
  GET  /v1/review/analytics                  field accuracy, review time, and auto-approval rate
"""
from __future__ import annotations

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from app.extraction.router import router as extraction_router
from app.intake.router import router as intake_router
from app.ocr.router import router as ocr_router
from app.review.router import analytics_router as review_analytics_router
from app.review.router import router as review_router
from app.validation.router import router as validation_router

app = FastAPI(
    title='Multimodal Document Reviewer',
    description=(
        'Accepts scanned forms, PDFs and images, extracts structured fields, '
        'validates them, and routes low-confidence results to a human review queue. '
        'OCR runs first; a vision model takes over where confidence drops.'
        '\n\n**Try it:** `POST /v1/documents` to upload, then `/ocr`, `/extract`, '
        '`/validate`.'
    ),
    version="1.0.0",
)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")

app.include_router(intake_router)
app.include_router(ocr_router)
app.include_router(extraction_router)
app.include_router(validation_router)
app.include_router(review_router)
app.include_router(review_analytics_router)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
