"""Ingestion + chunking (Phase 2). Two strategies are available: recursive
heading-based chunking and fixed-size chunking with overlap. Every chunk
records which strategy produced it (`chunking_strategy`) so retrieval
performance can be compared strategy-by-strategy later."""
from __future__ import annotations

import re
from datetime import date

from app.core.models import Chunk, ChunkMetadata, DocType

_HEADING = re.compile(r"^(#{1,6})\s+(.*)$", re.MULTILINE)


def chunk_markdown(text: str, *, source_name: str, doc_type: DocType,
                   last_updated: date | None = None) -> list[Chunk]:
    matches = list(_HEADING.finditer(text))
    chunks: list[Chunk] = []
    if not matches:
        body = text.strip()
        if body:
            chunks.append(_mk(body, source_name, "", doc_type, last_updated, 0))
        return chunks

    for i, m in enumerate(matches):
        heading = m.group(2).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()
        if body:
            chunks.append(_mk(body, source_name, heading, doc_type, last_updated, i))
    return chunks


def _mk(body, source_name, heading, doc_type, last_updated, i) -> Chunk:
    cid = f"{source_name}::heading::{i}"
    return Chunk(
        chunk_id=cid,
        text=(f"{heading}\n{body}" if heading else body),
        chunking_strategy="heading",
        metadata=ChunkMetadata(
            source_name=source_name,
            section_heading=heading,
            last_updated=last_updated,
            doc_type=doc_type,
        ),
    )


def chunk_fixed_size(text: str, *, source_name: str, doc_type: DocType,
                     last_updated: date | None = None,
                     chunk_size: int = 200, overlap: int = 40) -> list[Chunk]:
    """Fixed-size chunking with overlap, measured in words. Simpler and
    heading-agnostic compared to `chunk_markdown`; useful as a baseline to
    compare retrieval quality against heading-based chunks."""
    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError("overlap must be non-negative and smaller than chunk_size")

    words = text.split()
    chunks: list[Chunk] = []
    if not words:
        return chunks

    step = chunk_size - overlap
    i = 0
    idx = 0
    while True:
        window = words[i:i + chunk_size]
        body = " ".join(window).strip()
        if body:
            chunks.append(_mk_fixed(body, source_name, doc_type, last_updated, idx))
            idx += 1
        if i + chunk_size >= len(words):
            break
        i += step
    return chunks


def _mk_fixed(body, source_name, doc_type, last_updated, i) -> Chunk:
    cid = f"{source_name}::fixed::{i}"
    return Chunk(
        chunk_id=cid,
        text=body,
        chunking_strategy="fixed",
        metadata=ChunkMetadata(
            source_name=source_name,
            section_heading="",
            last_updated=last_updated,
            doc_type=doc_type,
        ),
    )
