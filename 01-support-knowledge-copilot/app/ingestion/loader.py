"""Load the bundled sample support corpus into chunks."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from app.core.models import Chunk, DocType
from app.ingestion.chunker import chunk_markdown

_DOC_TYPES = {
    "faq": DocType.faq,
    "troubleshooting": DocType.troubleshooting,
    "onboarding": DocType.onboarding,
    "api": DocType.api_docs,
    "release": DocType.release_notes,
    "policy": DocType.policy,
}

_SAMPLE_DIR = Path(__file__).resolve().parents[2] / "data" / "sample_docs"


def load_sample_corpus() -> list[Chunk]:
    chunks: list[Chunk] = []
    for md in sorted(_SAMPLE_DIR.glob("*.md")):
        stem = md.stem
        doc_type = next((v for k, v in _DOC_TYPES.items() if k in stem), DocType.faq)
        chunks.extend(chunk_markdown(
            md.read_text(encoding="utf-8"),
            source_name=stem,
            doc_type=doc_type,
            last_updated=date(2025, 1, 1),
        ))
    return chunks
