"""Grounded-answer prompt design (Phase 4, step 1).

The contract is kept simple and strict on purpose: answer only from the
provided context, cite every claim with the originating chunk ID in square
brackets, and say explicitly when the context does not contain the answer.
This is the prompt a real LLM provider (wired via `GENERATION_MODEL`) would
receive; the offline `stub` generator in `app.generation.answer` follows the
same contract without calling out to a model.
"""
from __future__ import annotations

from app.core.models import RetrievedChunk

SYSTEM_PROMPT = (
    "You are a support knowledge assistant. Answer ONLY using the numbered "
    "context chunks provided below. Every factual claim in your answer must "
    "end with the chunk ID it came from, in square brackets, e.g. [chunk_3]. "
    "If the context does not contain enough information to answer, say so "
    "explicitly instead of guessing. Do not use outside knowledge."
)


def build_context_block(retrieved: list[RetrievedChunk]) -> str:
    """Render retrieved chunks as a numbered, chunk-ID-tagged context block."""
    lines = []
    for r in retrieved:
        lines.append(f"[{r.chunk.chunk_id}] {r.chunk.text.strip()}")
    return "\n\n".join(lines)


def build_user_prompt(question: str, retrieved: list[RetrievedChunk]) -> str:
    context = build_context_block(retrieved)
    return (
        f"Context:\n{context}\n\n"
        f"Question: {question}\n\n"
        "Answer using only the context above, citing chunk IDs for every claim."
    )
