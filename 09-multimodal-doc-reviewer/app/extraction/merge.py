"""Merge per-page structured extraction into one document-level result
(Phase 3, step 3).

Pages are merged in order; the first page to report a scalar field wins.
If a later page reports a *different* value for a field that is already
set, the disagreement is recorded as a `FieldConflict` instead of being
silently overwritten — extraction consumers need to see the conflict, not
guess which page is right. List-valued fields (line items, parties)
accumulate unique values across pages instead of conflicting.
"""
from __future__ import annotations

from pydantic import BaseModel

from app.core.models import DocumentType
from app.extraction.extractor import extract_page_fields
from app.extraction.schemas import FIELDS_BY_DOCUMENT_TYPE, SourcedValue


class FieldConflict(BaseModel):
    field: str
    values: list[SourcedValue]


def merge_page_extractions(
    document_type: DocumentType, pages: list[tuple[int, str, str]]
) -> tuple[BaseModel | None, list[FieldConflict]]:
    """`pages` is a list of `(page_number, source, text)` tuples."""
    schema_cls = FIELDS_BY_DOCUMENT_TYPE.get(document_type)
    if schema_cls is None:
        return None, []

    merged: dict[str, SourcedValue] = {}
    list_fields: dict[str, list[str]] = {}
    conflicting: dict[str, list[SourcedValue]] = {}

    for page_number, source, text in pages:
        for name, value in extract_page_fields(document_type, text, page_number, source).items():
            if isinstance(value, list):
                existing = list_fields.setdefault(name, [])
                existing.extend(item for item in value if item not in existing)
                continue

            if name not in merged:
                merged[name] = value
            elif merged[name].value != value.value:
                conflicting.setdefault(name, [merged[name]]).append(value)

    schema = schema_cls.model_validate({**merged, **list_fields})
    conflicts = [FieldConflict(field=name, values=values) for name, values in conflicting.items()]
    return schema, conflicts
