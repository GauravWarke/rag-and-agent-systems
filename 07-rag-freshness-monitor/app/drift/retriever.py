"""Minimal dense retriever used to run probe questions against a chunk set.

This is intentionally a single-signal (cosine over the stub embedder)
top-1 retriever, not the full hybrid pipeline — the point of the drift
probes is to notice *when retrieval results change* across index
snapshots, not to maximize retrieval quality.
"""
from __future__ import annotations

from app.core.models import ChunkRecord
from app.indexing.embeddings import cosine, embed


def top_match(question: str, chunks: list[ChunkRecord]) -> tuple[str | None, float]:
    """Return `(chunk_id, score)` of the closest chunk to `question`, or
    `(None, 0.0)` if `chunks` is empty."""
    if not chunks:
        return None, 0.0
    query_vec = embed(question)
    best_id: str | None = None
    best_score = -1.0
    for chunk in chunks:
        score = cosine(query_vec, embed(chunk.text))
        if score > best_score:
            best_score = score
            best_id = chunk.chunk_id
    return best_id, max(0.0, best_score)
