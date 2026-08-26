"""In-memory extraction result store, keyed by document id."""
from __future__ import annotations

from app.extraction.models import ExtractionResult


class ExtractionResultStore:
    def __init__(self) -> None:
        self._results: dict[str, ExtractionResult] = {}

    def get(self, document_id: str) -> ExtractionResult | None:
        return self._results.get(document_id)

    def set(self, document_id: str, result: ExtractionResult) -> ExtractionResult:
        self._results[document_id] = result
        return result

    def clear(self) -> None:
        self._results.clear()


extraction_result_store = ExtractionResultStore()
