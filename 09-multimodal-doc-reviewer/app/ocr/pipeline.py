"""Per-page OCR pipeline (Phase 2): run OCR on raster pages, score
confidence, and fall back to vision extraction when confidence is too low
to trust. Born-digital PDF pages skip both stages since they already have
an embedded text layer. Scanned PDF pages have no normalized image (no
offline rasterizer bundled), so they go straight to vision fallback.
"""
from __future__ import annotations

from app.core.models import ConfidenceLevel, PageSourceFormat
from app.intake.models import Document, Page
from app.ocr.confidence import estimate_confidence
from app.ocr.engine import run_ocr
from app.ocr.models import DocumentOcrResult, PageTextResult
from app.ocr.vision_fallback import run_vision_fallback


def process_page(page: Page) -> PageTextResult:
    if page.source_format == PageSourceFormat.PDF_TEXT:
        return PageTextResult(page_number=page.page_number, source="embedded_text", text=page.embedded_text or "")

    if page.source_format == PageSourceFormat.PDF_IMAGE:
        vision = run_vision_fallback(b"", hint_text="")
        return PageTextResult(page_number=page.page_number, source="vision_fallback", text=vision.text, vision=vision)

    image_png = page.normalized_image_png or b""
    ocr_result = run_ocr(image_png)
    confidence = estimate_confidence(ocr_result, page.width_px, page.height_px)

    if confidence.level == ConfidenceLevel.LOW:
        vision = run_vision_fallback(image_png, hint_text=ocr_result.text)
        return PageTextResult(
            page_number=page.page_number,
            source="vision_fallback",
            text=vision.text,
            ocr=ocr_result,
            confidence=confidence,
            vision=vision,
        )

    return PageTextResult(
        page_number=page.page_number,
        source="ocr",
        text=ocr_result.text,
        ocr=ocr_result,
        confidence=confidence,
    )


def process_document(document: Document) -> DocumentOcrResult:
    return DocumentOcrResult(document_id=document.id, pages=[process_page(p) for p in document.pages])
