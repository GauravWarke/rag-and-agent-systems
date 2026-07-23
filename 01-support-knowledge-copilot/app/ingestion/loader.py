"""Load the bundled sample support corpus into chunks.

Documents are first normalized (Phase 2, step 1) via
`app.ingestion.normalizer`, which supports Markdown, HTML, text, and PDF
sources and keeps both raw and cleaned text for debugging. The cleaned text
is then chunked (Phase 2, step 2) using either the heading-based or
fixed-size-with-overlap strategy, so the two can be compared later."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from app.core.models import Chunk, DocType
from app.ingestion.chunker import chunk_fixed_size, chunk_markdown
from app.ingestion.normalizer import SUPPORTED_EXTENSIONS, normalize_document

_DOC_TYPES = {
    "faq": DocType.faq,
    "troubleshooting": DocType.troubleshooting,
    "onboarding": DocType.onboarding,
    "api": DocType.api_docs,
    "release": DocType.release_notes,
    "policy": DocType.policy,
}

_SAMPLE_DIR = Path(__file__).resolve().parents[2] / "data" / "sample_docs"


def load_sample_corpus(chunking_strategy: str = "heading") -> list[Chunk]:
    if chunking_strategy not in {"heading", "fixed"}:
        raise ValueError(f"Unknown chunking strategy: {chunking_strategy!r}")

    chunks: list[Chunk] = []
    paths = sorted(p for p in _SAMPLE_DIR.iterdir() if p.suffix.lower() in SUPPORTED_EXTENSIONS)
    for path in paths:
        stem = path.stem
        doc_type = next((v for k, v in _DOC_TYPES.items() if k in stem), DocType.faq)
        doc = normalize_document(path)
        if chunking_strategy == "fixed":
            chunks.extend(chunk_fixed_size(
                doc.cleaned_text,
                source_name=stem,
                doc_type=doc_type,
                last_updated=date(2025, 1, 1),
            ))
        else:
            chunks.extend(chunk_markdown(
                doc.cleaned_text,
                source_name=stem,
                doc_type=doc_type,
                last_updated=date(2025, 1, 1),
            ))
    return chunks
