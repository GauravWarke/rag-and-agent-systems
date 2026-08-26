"""In-memory OCR result cache, keyed by document id, so the extraction
stage can reuse a page's OCR output instead of re-running it.
"""
from __future__ import annotations

from app.ocr.models import DocumentOcrResult


class OcrResultStore:
    def __init__(self) -> None:
        self._results: dict[str, DocumentOcrResult] = {}

    def get(self, document_id: str) -> DocumentOcrResult | None:
        return self._results.get(document_id)

    def set(self, document_id: str, result: DocumentOcrResult) -> DocumentOcrResult:
        self._results[document_id] = result
        return result

    def clear(self) -> None:
        self._results.clear()


ocr_result_store = OcrResultStore()
