"""Detect source-level freshness issues: sections added, removed, or
modified since the manifest was last built, with a semantic-change score
so trivial edits (typo fixes) don't get flagged the same as meaningful
content changes.
"""
from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path

from app.core.models import ChunkRecord, FreshnessDiff, IndexManifest, SectionChange
from app.indexing.chunker import build_chunks
from app.indexing.embeddings import cosine, embed


def semantic_change_score(old_text: str, new_text: str) -> float:
    """0.0 = semantically identical, up to 1.0 = completely different."""
    if not old_text.strip() or not new_text.strip():
        return 1.0
    similarity = cosine(embed(old_text), embed(new_text))
    return max(0.0, min(1.0, 1.0 - similarity))


def diff_against_manifest(
    manifest: IndexManifest,
    docs_dir: Path,
    docs_meta_path: Path,
) -> FreshnessDiff:
    current_chunks: list[ChunkRecord] = build_chunks(docs_dir, docs_meta_path, manifest.embedding_version)
    current_by_id = {c.chunk_id: c for c in current_chunks}
    manifest_by_id = {c.chunk_id: c for c in manifest.chunks}

    added = [
        SectionChange(
            chunk_id=c.chunk_id,
            doc_source=c.doc_source,
            section_heading=c.section_heading,
            change_type="added",
            new_text=c.text,
        )
        for cid, c in current_by_id.items()
        if cid not in manifest_by_id
    ]
    removed = [
        SectionChange(
            chunk_id=c.chunk_id,
            doc_source=c.doc_source,
            section_heading=c.section_heading,
            change_type="removed",
            old_text=c.text,
        )
        for cid, c in manifest_by_id.items()
        if cid not in current_by_id
    ]
    modified = []
    for cid, current in current_by_id.items():
        previous = manifest_by_id.get(cid)
        if previous is not None and previous.chunk_hash != current.chunk_hash:
            modified.append(
                SectionChange(
                    chunk_id=cid,
                    doc_source=current.doc_source,
                    section_heading=current.section_heading,
                    change_type="modified",
                    old_text=previous.text,
                    new_text=current.text,
                    semantic_change_score=semantic_change_score(previous.text, current.text),
                )
            )

    return FreshnessDiff(
        manifest_created_at=manifest.created_at,
        scanned_at=datetime.now(UTC).isoformat(),
        added=added,
        removed=removed,
        modified=modified,
    )
