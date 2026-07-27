"""Confidence scoring (Phase 4, step 3).

Combines retrieval strength, citation support rate, and answer completeness
into a single confidence number, while keeping the individual signals in the
breakdown so a caller can see why the score landed where it did.
"""
from __future__ import annotations

from app.core.models import Citation, ConfidenceBreakdown

RETRIEVAL_WEIGHT = 0.5
CITATION_WEIGHT = 0.3
COMPLETENESS_WEIGHT = 0.2


def citation_support_rate(citations: list[Citation]) -> float:
    if not citations:
        return 0.0
    return sum(1 for c in citations if c.supported) / len(citations)


def answer_completeness(retrieved_count: int, target_count: int) -> float:
    if target_count <= 0:
        return 0.0
    return min(1.0, retrieved_count / target_count)


def score(
    top_score: float,
    citations: list[Citation],
    retrieved_count: int,
    target_count: int,
) -> ConfidenceBreakdown:
    support_rate = citation_support_rate(citations)
    completeness = answer_completeness(retrieved_count, target_count)
    final = round(
        RETRIEVAL_WEIGHT * top_score
        + CITATION_WEIGHT * support_rate
        + COMPLETENESS_WEIGHT * completeness,
        4,
    )
    return ConfidenceBreakdown(
        retrieval_score=round(top_score, 4),
        citation_support_rate=round(support_rate, 4),
        answer_completeness=round(completeness, 4),
        no_answer_detected=False,
        final=final,
    )
