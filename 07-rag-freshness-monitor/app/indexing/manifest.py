"""Build, save, and load the index manifest.

The manifest is the frozen snapshot that freshness scans and drift probes
compare against — it records what was indexed, when, and with which
embedding model and chunking strategy, so later scans can tell exactly
what changed since the index was last built.
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from app.core.models import IndexManifest
from app.indexing.chunker import build_chunks


def build_manifest(
    docs_dir: Path,
    docs_meta_path: Path,
    embedding_model: str,
    embedding_version: str,
    chunking_strategy: str,
) -> IndexManifest:
    if chunking_strategy != "heading":
        raise ValueError(f"Unknown chunking strategy: {chunking_strategy!r}")
    chunks = build_chunks(docs_dir, docs_meta_path, embedding_version)
    return IndexManifest(
        created_at=datetime.now(UTC).isoformat(),
        embedding_model=embedding_model,
        embedding_version=embedding_version,
        chunking_strategy=chunking_strategy,
        chunks=chunks,
    )


def save_manifest(manifest: IndexManifest, manifest_path: Path) -> None:
    manifest_path.parent.mkdir(parents=True, exist_ok=True)
    manifest_path.write_text(manifest.model_dump_json(indent=2), encoding="utf-8")


def load_manifest(manifest_path: Path) -> IndexManifest | None:
    if not manifest_path.exists():
        return None
    return IndexManifest.model_validate_json(manifest_path.read_text(encoding="utf-8"))
