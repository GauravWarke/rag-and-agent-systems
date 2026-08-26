"""Estimate whether an OCR result is usable, or whether the page should
fall back to a vision model (Phase 2, step 2).

Blends the engine's own confidence score (when available) with two sanity
checks that raw confidence alone can miss: text density (an engine can be
"confident" about three garbled words on a dense page) and an
alphanumeric-content ratio (catches whitespace/symbol-only noise).
"""
from __future__ import annotations

from app.core.config import settings
from app.core.models import ConfidenceLevel
from app.ocr.models import ConfidenceAssessment, OcrResult

_MIN_ALNUM_RATIO = 0.4
_MIN_TEXT_DENSITY = 0.0005  # chars per pixel


def estimate_confidence(
    ocr: OcrResult, page_width_px: int | None, page_height_px: int | None
) -> ConfidenceAssessment:
    text = ocr.text.strip()
    if not text:
        return ConfidenceAssessment(level=ConfidenceLevel.LOW, score=0.0, reasons=["OCR returned no text"])

    reasons: list[str] = []

    alnum_ratio = sum(c.isalnum() for c in text) / len(text)
    if alnum_ratio < _MIN_ALNUM_RATIO:
        reasons.append(f"low alphanumeric ratio ({alnum_ratio:.2f}); likely noise")

    area = (page_width_px or 0) * (page_height_px or 0)
    if area:
        density = len(text) / area
        if density < _MIN_TEXT_DENSITY:
            reasons.append(f"low text density ({density:.5f} chars/px) for a {page_width_px}x{page_height_px} page")

    engine_score = (ocr.raw_confidence / 100.0) if ocr.raw_confidence is not None else None
    if engine_score is not None and engine_score < 0.5:
        reasons.append(f"low engine confidence ({engine_score:.2f})")

    base = engine_score if engine_score is not None else (0.75 if alnum_ratio >= _MIN_ALNUM_RATIO else 0.3)
    score = max(0.0, min(1.0, base - 0.25 * len(reasons)))

    threshold = settings.ocr_confidence_threshold
    if score >= threshold:
        level = ConfidenceLevel.HIGH if not reasons else ConfidenceLevel.MEDIUM
    else:
        level = ConfidenceLevel.LOW

    if not reasons:
        reasons.append("OCR text passed density and alphanumeric sanity checks")

    return ConfidenceAssessment(level=level, score=round(score, 3), reasons=reasons)
