"""Ingestion + chunking (Phase 2). V1 supports Markdown with heading-based
recursive chunking; strategy is tracked on each chunk for later comparison."""
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
    cid = f"{source_name}::{i}"
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
