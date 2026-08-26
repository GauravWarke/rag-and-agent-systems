"""In-memory document store, shared by the intake, OCR, and extraction
routers so each stage can look up documents the earlier stage produced.
"""
from __future__ import annotations

from app.intake.models import Document


class DocumentStore:
    def __init__(self) -> None:
        self._documents: dict[str, Document] = {}

    def add(self, document: Document) -> Document:
        self._documents[document.id] = document
        return document

    def get(self, document_id: str) -> Document | None:
        return self._documents.get(document_id)

    def all(self) -> list[Document]:
        return list(self._documents.values())

    def clear(self) -> None:
        self._documents.clear()


document_store = DocumentStore()
