"""Vision-model fallback for pages where OCR confidence is too low to
trust (Phase 2, step 3).

Real vision models are expensive, so this only runs for low-confidence
pages — a production design should use them as a fallback, not the
default for every page. The offline default (`VISION_API_KEY` unset)
returns a stub result that flags the page for manual review instead of
guessing; set `VISION_API_KEY` to route to a real provider.
"""
from __future__ import annotations

from app.core.config import settings
from app.ocr.models import VisionResult


def _run_stub(image_png: bytes, hint_text: str) -> VisionResult:
    return VisionResult(
        text=hint_text,
        provider="stub",
        note="VISION_API_KEY not set; offline stub could not extract text from the image. Routed for manual review.",
    )


def _run_provider(image_png: bytes, hint_text: str) -> VisionResult:
    raise NotImplementedError(
        "Vision fallback provider not wired yet; implement the API call here using "
        "settings.vision_api_key, or unset VISION_API_KEY to use the offline stub."
    )


def run_vision_fallback(image_png: bytes, hint_text: str = "") -> VisionResult:
    if settings.vision_api_key:
        return _run_provider(image_png, hint_text)
    return _run_stub(image_png, hint_text)
