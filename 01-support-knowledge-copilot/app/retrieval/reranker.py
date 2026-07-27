"""Reranking pass over fused hybrid candidates (Phase 3, step 4).

RRF fusion is a cheap rank-merge; it does not look at question/chunk semantics
together the way a cross-encoder or LLM-as-reranker would. This stage takes the
top `rerank_candidates` fused chunks and rescores each (question, chunk) pair
directly, then keeps only the top `rerank_top_k` for generation.

The default `stub` reranker is deterministic and offline: it scores question/chunk
token overlap with a bonus for matches that land early in the chunk (titles and
lead sentences tend to state the answer). This approximates what a real
cross-encoder or LLM judge would rank higher, without needing an API key. Swap
`RERANK_MODEL` to a real cross-encoder (e.g. a `ms-marco-MiniLM` model) or an
LLM-as-reranker later.
"""
from __future__ import annotations

from app.core.config import settings
from app.core.models import RetrievedChunk
from app.retrieval.embeddings import _tokenize


def _stub_score(question: str, text: str) -> float:
    q_tokens = _tokenize(question)
    if not q_tokens:
        return 0.0
    t_tokens = _tokenize(text)
    t_set = set(t_tokens)
    overlap = sum(1 for t in q_tokens if t in t_set) / len(q_tokens)
    lead_set = set(t_tokens[: max(1, len(t_tokens) // 4)])
    lead_bonus = sum(1 for t in q_tokens if t in lead_set) / len(q_tokens)
    return round(0.8 * overlap + 0.2 * lead_bonus, 6)


def rerank(question: str, candidates: list[RetrievedChunk]) -> list[RetrievedChunk]:
    """Rescore fused candidates and return the top `settings.rerank_top_k`."""
    if settings.rerank_model != "stub":
        raise NotImplementedError(
            f"Rerank model '{settings.rerank_model}' not wired yet; "
            "use RERANK_MODEL=stub or implement the cross-encoder/LLM-reranker adapter."
        )
    scored = [
        r.model_copy(update={"rerank_score": _stub_score(question, r.chunk.text)})
        for r in candidates
    ]
    scored.sort(key=lambda r: r.rerank_score or 0.0, reverse=True)
    return scored[: settings.rerank_top_k]
