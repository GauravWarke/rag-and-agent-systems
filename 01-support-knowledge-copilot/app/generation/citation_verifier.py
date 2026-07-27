"""Citation verification (Phase 4, step 2).

After an answer is generated, every claim it makes must be checked against
the chunk it cites. V1 uses a rule-based lexical-overlap check (word overlap
between the claim and its cited chunk) rather than an LLM-as-judge, so
verification runs offline and deterministically. Swap `_supported` for an
LLM-as-judge call later without changing the `Citation` contract.
"""
from __future__ import annotations

import re

from app.core.models import Citation, RetrievedChunk

_WORD = re.compile(r"[a-z0-9]+")

# A claim needs at least this fraction of its words present in the cited
# chunk's text to be considered supported.
SUPPORT_THRESHOLD = 0.5

_EVIDENCE_SPAN_LEN = 160


def _overlap(claim: str, chunk_text: str) -> float:
    claim_words, chunk_words = set(_WORD.findall(claim.lower())), set(_WORD.findall(chunk_text.lower()))
    if not claim_words:
        return 0.0
    return len(claim_words & chunk_words) / len(claim_words)


def verify_claim(claim: str, chunk_text: str) -> tuple[bool, str]:
    """Return (supported, evidence_span) for a single claim against its cited chunk."""
    supported = _overlap(claim, chunk_text) >= SUPPORT_THRESHOLD
    return supported, chunk_text[:_EVIDENCE_SPAN_LEN]


def verify_citations(claims: list[tuple[str, RetrievedChunk]]) -> list[Citation]:
    """Verify a list of (claim, cited chunk) pairs and return `Citation` records."""
    citations = []
    for claim, retrieved in claims:
        supported, evidence = verify_claim(claim, retrieved.chunk.text)
        citations.append(Citation(
            chunk_id=retrieved.chunk.chunk_id,
            claim=claim,
            supported=supported,
            evidence_span=evidence,
        ))
    return citations
