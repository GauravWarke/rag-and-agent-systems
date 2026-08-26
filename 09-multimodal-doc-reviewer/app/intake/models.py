"""Document and page records for the intake pipeline (Phase 1).

Normalized page images are kept on the model (so downstream OCR/vision
code can use them directly) but excluded from JSON responses via
`exclude=True` — raw bytes don't belong in an API payload. `has_normalized_image`
is a computed field so clients can still tell whether one is available.
"""
from __future__ import annotations

from pydantic import BaseModel, Field, computed_field

from app.core.models import DocumentType, PageSourceFormat


class PreprocessingStep(BaseModel):
    name: str
    detail: str


class Page(BaseModel):
    page_number: int
    source_format: PageSourceFormat
    width_px: int | None = None
    height_px: int | None = None
    normalized_image_png: bytes | None = Field(default=None, exclude=True, repr=False)
    embedded_text: str | None = None
    preprocessing: list[PreprocessingStep] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)

    @computed_field  # type: ignore[misc]
    @property
    def has_normalized_image(self) -> bool:
        return self.normalized_image_png is not None


class Document(BaseModel):
    id: str
    filename: str
    content_type: str
    uploaded_at: str
    document_type: DocumentType
    document_type_confidence: float
    pages: list[Page]

    @computed_field  # type: ignore[misc]
    @property
    def page_count(self) -> int:
        return len(self.pages)
