"""Grounded answer generation and confidence scoring (Phase 4).

V1 uses an extractive, rule-based generator so the whole system runs without an
LLM key: it composes an answer from the top retrieved chunks, attaches citations
by chunk ID, verifies each citation by lexical overlap, and produces a confidence
breakdown. Replace `generate()` with an LLM call (strict "answer only from
context, cite chunk IDs") when a provider key is configured.
"""
from __future__ import annotations

import re

from app.core.config import settings
from app.core.models import (
    AskResponse,
    Citation,
    ConfidenceBreakdown,
    RetrievedChunk,
)

_WORD = re.compile(r"[a-z0-9]+")


def _overlap(a: str, b: str) -> float:
    wa, wb = set(_WORD.findall(a.lower())), set(_WORD.findall(b.lower()))
    if not wa:
        return 0.0
    return len(wa & wb) / len(wa)


def generate(question: str, retrieved: list[RetrievedChunk]) -> AskResponse:
    top_score = max((r.fused_score or 0.0) for r in retrieved) if retrieved else 0.0

    # Handle missing knowledge gracefully (Phase 4, step 4)
    if not retrieved or top_score < settings.min_retrieval_score:
        return AskResponse(
            answer="I could not find this in the docs.",
            citations=[],
            confidence=ConfidenceBreakdown(no_answer_detected=True, final=0.0),
            could_not_verify=[question],
            retrieved=retrieved,
        )

    # Extractive answer: stitch the most relevant sentences from top chunks.
    parts, citations = [], []
    for r in retrieved[: settings.rerank_top_k]:
        sentence = r.chunk.text.strip().split(". ")[0]
        parts.append(f"{sentence} [{r.chunk.chunk_id}]")
        supported = _overlap(sentence, r.chunk.text) > 0.5
        citations.append(Citation(
            chunk_id=r.chunk.chunk_id,
            claim=sentence,
            supported=supported,
            evidence_span=r.chunk.text[:160],
        ))

    answer = " ".join(parts)
    support_rate = (sum(1 for c in citations if c.supported) / len(citations)) if citations else 0.0
    completeness = min(1.0, len(retrieved) / settings.rerank_top_k)
    final = round(0.5 * top_score + 0.3 * support_rate + 0.2 * completeness, 4)

    return AskResponse(
        answer=answer,
        citations=citations,
        confidence=ConfidenceBreakdown(
            retrieval_score=round(top_score, 4),
            citation_support_rate=round(support_rate, 4),
            answer_completeness=round(completeness, 4),
            no_answer_detected=False,
            final=final,
        ),
        could_not_verify=[c.claim for c in citations if c.supported is False],
        retrieved=retrieved,
    )
