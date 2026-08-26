"""Per-page structured field extraction (Phase 3, step 2).

The stub extractor looks for `Label: value` lines using the synonym lists
in `schemas.LABELS_BY_DOCUMENT_TYPE`, plus small dedicated parsers for the
two list-valued fields (invoice line items, contract parties). Swap this
for an LLM structured-output call (e.g. via `instructor`) behind a
provider key later — the schema and source-tracking contract stay the
same either way.
"""
from __future__ import annotations

import re

from app.core.models import DocumentType
from app.extraction.schemas import (
    LABELS_BY_DOCUMENT_TYPE,
    LIST_FIELDS_BY_DOCUMENT_TYPE,
    NUMERIC_FIELDS,
    SourcedValue,
)

_EMAIL_PATTERN = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


def _find_labeled_value(text: str, labels: list[str]) -> str | None:
    for label in labels:
        pattern = re.compile(rf"^\s*{re.escape(label)}\s*[:\-]\s*(.+)$", re.IGNORECASE | re.MULTILINE)
        match = pattern.search(text)
        if match:
            value = match.group(1).strip()
            if value:
                return value
    return None


def _as_number(raw: str) -> float | None:
    cleaned = raw.replace("$", "").replace(",", "").strip()
    try:
        return float(cleaned)
    except ValueError:
        return None


def _extract_line_items(text: str) -> list[str]:
    lines = text.splitlines()
    items: list[str] = []
    in_section = False
    for line in lines:
        stripped = line.strip()
        if re.match(r"^line items?\s*:?\s*$", stripped, re.IGNORECASE):
            in_section = True
            continue
        if in_section:
            if stripped.startswith(("-", "*")):
                items.append(stripped.lstrip("-* ").strip())
                continue
            if not stripped:
                break
            break
    return items


def _extract_parties(text: str) -> list[str]:
    raw = _find_labeled_value(text, ["parties"])
    if not raw:
        return []
    parts = re.split(r",| and ", raw, flags=re.IGNORECASE)
    return [p.strip() for p in parts if p.strip()]


def extract_page_fields(
    document_type: DocumentType, text: str, page_number: int, source: str
) -> dict[str, SourcedValue | list[str]]:
    labels = LABELS_BY_DOCUMENT_TYPE.get(document_type)
    if labels is None:
        return {}

    fields: dict[str, SourcedValue | list[str]] = {}
    for field_name, synonyms in labels.items():
        raw = _find_labeled_value(text, synonyms)
        if raw is None:
            continue
        if field_name in NUMERIC_FIELDS:
            number = _as_number(raw)
            if number is None:
                continue
            fields[field_name] = SourcedValue(value=number, page_number=page_number, source=source)
        else:
            fields[field_name] = SourcedValue(value=raw, page_number=page_number, source=source)

    if document_type == DocumentType.ONBOARDING_FORM and "email" not in fields:
        match = _EMAIL_PATTERN.search(text)
        if match:
            fields["email"] = SourcedValue(value=match.group(0), page_number=page_number, source=source)

    list_field = LIST_FIELDS_BY_DOCUMENT_TYPE.get(document_type)
    if list_field == "line_items":
        fields[list_field] = _extract_line_items(text)
    elif list_field == "parties":
        fields[list_field] = _extract_parties(text)

    return fields
