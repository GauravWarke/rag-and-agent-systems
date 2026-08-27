"""In-memory validation result store, keyed by document id."""
from __future__ import annotations

from app.validation.models import ValidationResult


class ValidationResultStore:
    def __init__(self) -> None:
        self._results: dict[str, ValidationResult] = {}

    def get(self, document_id: str) -> ValidationResult | None:
        return self._results.get(document_id)

    def set(self, document_id: str, result: ValidationResult) -> ValidationResult:
        self._results[document_id] = result
        return result

    def clear(self) -> None:
        self._results.clear()


validation_result_store = ValidationResultStore()
