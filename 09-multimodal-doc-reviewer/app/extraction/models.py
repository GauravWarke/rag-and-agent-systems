"""Document-level extraction result (Phase 3)."""
from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field

from app.core.models import DocumentType
from app.extraction.merge import FieldConflict


class ExtractionResult(BaseModel):
    document_id: str
    document_type: DocumentType
    fields: dict[str, Any]
    conflicts: list[FieldConflict] = Field(default_factory=list)
