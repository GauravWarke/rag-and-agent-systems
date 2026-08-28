"""In-memory correction store, keyed by document id (Phase 5, step 2).

Also used by the analytics endpoint (Phase 5, step 3) to compute
field-accuracy stats and review turnaround time across all documents.
"""
from __future__ import annotations

from app.review.models import FieldCorrection


class CorrectionStore:
    def __init__(self) -> None:
        self._corrections: dict[str, list[FieldCorrection]] = {}

    def add(self, correction: FieldCorrection) -> FieldCorrection:
        self._corrections.setdefault(correction.document_id, []).append(correction)
        return correction

    def list_for(self, document_id: str) -> list[FieldCorrection]:
        return list(self._corrections.get(document_id, []))

    def all(self) -> list[FieldCorrection]:
        return [c for corrections in self._corrections.values() for c in corrections]

    def clear(self) -> None:
        self._corrections.clear()


correction_store = CorrectionStore()
