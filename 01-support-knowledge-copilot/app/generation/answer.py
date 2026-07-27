"""Grounded answer generation (Phase 4).

Orchestrates the three Phase 4 pieces: the answer prompt/contract
(`app.generation.prompts`), citation verification
(`app.generation.citation_verifier`), and confidence scoring
(`app.generation.confidence`).

The default `stub` generator is extractive and offline: it composes an
answer from the top retrieved chunks and cites each sentence by chunk ID,
so the whole system runs and is testable without an LLM key. Swap
`GENERATION_MODEL` to a real provider and implement the call in
`_generate_llm` (using `prompts.SYSTEM_PROMPT` / `build_user_prompt`) when a
provider key is configured.
"""
from __future__ import annotations

from app.core.config import settings
from app.core.models import AskResponse, ConfidenceBreakdown, RetrievedChunk
from app.generation import confidence
from app.generation.citation_verifier import verify_citations


def _generate_llm(question: str, retrieved: list[RetrievedChunk]) -> AskResponse:
    raise NotImplementedError(
        f"Generation model '{settings.generation_model}' not wired yet; "
        "use GENERATION_MODEL=stub or implement the provider adapter using "
        "app.generation.prompts.SYSTEM_PROMPT / build_user_prompt."
    )


def _no_answer_response(question: str, retrieved: list[RetrievedChunk]) -> AskResponse:
    """Handle missing knowledge gracefully (Phase 4, step 4): tell the user
    plainly and surface the closest matching sections instead of guessing."""
    return AskResponse(
        answer="I could not find this in the docs. Here are the closest matching sections I found.",
        citations=[],
        confidence=ConfidenceBreakdown(no_answer_detected=True, final=0.0),
        could_not_verify=[question],
        retrieved=retrieved,
    )


def _generate_stub(question: str, retrieved: list[RetrievedChunk]) -> AskResponse:
    top_k = retrieved[: settings.rerank_top_k]

    # Extractive answer: stitch the most relevant sentence from each top chunk.
    claims = [(r.chunk.text.strip().split(". ")[0], r) for r in top_k]
    citations = verify_citations(claims)
    answer = " ".join(f"{claim} [{r.chunk.chunk_id}]" for claim, r in claims)

    top_score = max((r.fused_score or 0.0) for r in retrieved) if retrieved else 0.0
    breakdown = confidence.score(
        top_score=top_score,
        citations=citations,
        retrieved_count=len(retrieved),
        target_count=settings.rerank_top_k,
    )

    return AskResponse(
        answer=answer,
        citations=citations,
        confidence=breakdown,
        could_not_verify=[c.claim for c in citations if c.supported is False],
        retrieved=retrieved,
    )


def generate(question: str, retrieved: list[RetrievedChunk]) -> AskResponse:
    top_score = max((r.fused_score or 0.0) for r in retrieved) if retrieved else 0.0
    if not retrieved or top_score < settings.min_retrieval_score:
        return _no_answer_response(question, retrieved)

    if settings.generation_model != "stub":
        return _generate_llm(question, retrieved)
    return _generate_stub(question, retrieved)
