"""OCR / vision-fallback result models (Phase 2)."""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.core.models import ConfidenceLevel


class OcrLine(BaseModel):
    line_number: int
    text: str


class OcrResult(BaseModel):
    text: str
    lines: list[OcrLine] = Field(default_factory=list)
    engine: str  # "tesseract" | "stub"
    raw_confidence: float | None = None  # 0-100 mean word confidence, when the engine reports one


class ConfidenceAssessment(BaseModel):
    level: ConfidenceLevel
    score: float  # 0-1
    reasons: list[str] = Field(default_factory=list)


class VisionResult(BaseModel):
    text: str
    provider: str  # "stub" | real provider name
    note: str | None = None


class PageTextResult(BaseModel):
    page_number: int
    source: str  # "embedded_text" | "ocr" | "vision_fallback"
    text: str
    ocr: OcrResult | None = None
    confidence: ConfidenceAssessment | None = None
    vision: VisionResult | None = None


class DocumentOcrResult(BaseModel):
    document_id: str
    pages: list[PageTextResult]
