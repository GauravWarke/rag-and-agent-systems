"""Heading-based chunking for the Markdown source corpus.

Chunk IDs are derived deterministically from `<doc-stem>::<heading-slug>`
so the same section gets the same ID across scans, which is what lets the
freshness diff (Phase 2) and drift probes (Phase 3) compare "before" and
"after" snapshots of the same section.
"""
from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from app.core.models import ChunkRecord, DocType

_HEADING = re.compile(r"^#{1,6}\s+(.*)$")
_SLUG_STRIP = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    slug = _SLUG_STRIP.sub("-", text.strip().lower()).strip("-")
    return slug or "section"


def hash_text(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def split_sections(markdown: str) -> list[tuple[str, str]]:
    """Split Markdown into `(heading, body)` pairs on top-level headings."""
    sections: list[tuple[str, str]] = []
    heading: str | None = None
    body_lines: list[str] = []
    for line in markdown.splitlines():
        match = _HEADING.match(line)
        if match:
            if heading is not None:
                sections.append((heading, "\n".join(body_lines).strip()))
            heading = match.group(1).strip()
            body_lines = []
        else:
            body_lines.append(line)
    if heading is not None:
        sections.append((heading, "\n".join(body_lines).strip()))
    return sections


def load_docs_meta(docs_meta_path: Path) -> dict[str, dict[str, str]]:
    return json.loads(docs_meta_path.read_text(encoding="utf-8"))


def build_chunks(
    docs_dir: Path,
    docs_meta_path: Path,
    embedding_version: str,
) -> list[ChunkRecord]:
    """Load every Markdown file in `docs_dir`, split into sections, and
    return one `ChunkRecord` per section, using `docs_meta_path` for the
    doc type and last-modified date of each source file."""
    docs_meta = load_docs_meta(docs_meta_path)
    chunks: list[ChunkRecord] = []
    for path in sorted(docs_dir.glob("*.md")):
        meta = docs_meta.get(path.name)
        if meta is None:
            raise ValueError(f"No metadata entry for {path.name} in {docs_meta_path}")
        doc_type: DocType = meta["doc_type"]
        last_modified = meta["last_modified"]
        for heading, body in split_sections(path.read_text(encoding="utf-8")):
            chunk_id = f"{path.stem}::{slugify(heading)}"
            chunks.append(
                ChunkRecord(
                    chunk_id=chunk_id,
                    doc_source=path.name,
                    doc_type=doc_type,
                    section_heading=heading,
                    text=body,
                    chunk_hash=hash_text(body),
                    last_modified=last_modified,
                    embedding_version=embedding_version,
                )
            )
    return chunks
