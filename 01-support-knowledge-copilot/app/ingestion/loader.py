"""Load the bundled sample support corpus into chunks.

Documents are first normalized (Phase 2, step 1) via
`app.ingestion.normalizer`, which supports Markdown, HTML, text, and PDF
sources and keeps both raw and cleaned text for debugging. The cleaned text
is then chunked (Phase 2, step 2) using either the heading-based or
fixed-size-with-overlap strategy, so the two can be compared later."""
from __future__ import annotations

from datetime import date
from pathlib import Path

from app.core.models import AccessLevel, Chunk, DocType
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

# Access control (audit finding): policy documents (refund rules, internal
# security procedures, etc.) carry sensitive operational detail and are
# restricted by default. Everything else in the sample corpus is internal —
# visible to support staff but not to an unauthenticated/public caller.
_ACCESS_LEVELS: dict[DocType, AccessLevel] = {
    DocType.policy: AccessLevel.restricted,
}
_DEFAULT_ACCESS_LEVEL = AccessLevel.internal

_SAMPLE_DIR = Path(__file__).resolve().parents[2] / "data" / "sample_docs"


def load_corpus_from_dir(source_dir: Path, chunking_strategy: str = "heading") -> list[Chunk]:
    """Load, normalize, and chunk every supported document in `source_dir`.

    Shared by `load_sample_corpus` (bundled demo corpus) and the `ingest.py`
    re-index CLI (arbitrary `--source` directory), so both paths stay in sync.
    """
    if chunking_strategy not in {"heading", "fixed"}:
        raise ValueError(f"Unknown chunking strategy: {chunking_strategy!r}")

    chunks: list[Chunk] = []
    paths = sorted(p for p in source_dir.iterdir() if p.suffix.lower() in SUPPORTED_EXTENSIONS)
    for path in paths:
        stem = path.stem
        doc_type = next((v for k, v in _DOC_TYPES.items() if k in stem), DocType.faq)
        access_level = _ACCESS_LEVELS.get(doc_type, _DEFAULT_ACCESS_LEVEL)
        doc = normalize_document(path)
        if chunking_strategy == "fixed":
            chunks.extend(chunk_fixed_size(
                doc.cleaned_text,
                source_name=stem,
                doc_type=doc_type,
                last_updated=date(2025, 1, 1),
                access_level=access_level,
            ))
        else:
            chunks.extend(chunk_markdown(
                doc.cleaned_text,
                source_name=stem,
                doc_type=doc_type,
                last_updated=date(2025, 1, 1),
                access_level=access_level,
            ))
    return chunks


def load_sample_corpus(chunking_strategy: str = "heading") -> list[Chunk]:
    return load_corpus_from_dir(_SAMPLE_DIR, chunking_strategy=chunking_strategy)
