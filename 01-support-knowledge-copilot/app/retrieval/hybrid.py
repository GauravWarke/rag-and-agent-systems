"""Hybrid retrieval: dense (cosine over stub embeddings) + sparse (BM25),
fused with Reciprocal Rank Fusion (RRF), then reranked. Phases 2-3 of the
build guide.

Dense and sparse indexes point at the SAME chunk IDs so fusion stays clean —
the key design decision to explain in interviews. RRF is a cheap rank-merge,
so the top `rerank_candidates` fused chunks are rescored by a reranking pass
(see `app.retrieval.reranker`) before the top `rerank_top_k` go to generation.
"""
from __future__ import annotations

from rank_bm25 import BM25Okapi

from app.core.config import settings
from app.core.models import ACCESS_RANK, AccessLevel, Chunk, RetrievedChunk
from app.retrieval.embeddings import _tokenize, cosine, embed
from app.retrieval.reranker import rerank


class HybridRetriever:
    def __init__(self) -> None:
        self._chunks: dict[str, Chunk] = {}
        self._vectors: dict[str, list[float]] = {}
        self._bm25: BM25Okapi | None = None
        self._bm25_ids: list[str] = []

    def index(self, chunks: list[Chunk]) -> None:
        for c in chunks:
            self._chunks[c.chunk_id] = c
            self._vectors[c.chunk_id] = embed(c.text)
        self._bm25_ids = list(self._chunks)
        corpus = [_tokenize(self._chunks[i].text) for i in self._bm25_ids]
        self._bm25 = BM25Okapi(corpus) if corpus else None

    def _allowed_ids(self, access_level: AccessLevel) -> set[str]:
        """Access control (audit finding): a requester may only see chunks at
        their own clearance level or below, so restricted chunks never reach
        unauthorized answers regardless of retrieval strategy."""
        limit = ACCESS_RANK[access_level]
        return {
            cid for cid, chunk in self._chunks.items()
            if ACCESS_RANK[chunk.metadata.access_level] <= limit
        }

    def _dense(self, question: str, k: int, allowed: set[str]) -> list[tuple[str, float]]:
        qv = embed(question)
        scored = [(cid, cosine(qv, v)) for cid, v in self._vectors.items() if cid in allowed]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:k]

    def _sparse(self, question: str, k: int, allowed: set[str]) -> list[tuple[str, float]]:
        if not self._bm25:
            return []
        scores = self._bm25.get_scores(_tokenize(question))
        ranked = sorted(
            ((cid, s) for cid, s in zip(self._bm25_ids, scores) if cid in allowed),
            key=lambda x: x[1], reverse=True,
        )
        return ranked[:k]

    def retrieve(self, question: str, strategy: str = "hybrid",
                 access_level: AccessLevel = AccessLevel.internal) -> list[RetrievedChunk]:
        allowed = self._allowed_ids(access_level)
        dense = self._dense(question, settings.dense_top_k, allowed)
        sparse = self._sparse(question, settings.sparse_top_k, allowed)

        if strategy == "dense":
            return [RetrievedChunk(chunk=self._chunks[c], dense_score=s, fused_score=s)
                    for c, s in dense[: settings.rerank_top_k]]
        if strategy == "sparse":
            return [RetrievedChunk(chunk=self._chunks[c], sparse_rank=i + 1, fused_score=1.0 / (i + 1))
                    for i, (c, _) in enumerate(sparse[: settings.rerank_top_k])]

        # RRF fusion
        rrf_k = settings.rrf_k
        fused: dict[str, float] = {}
        for rank, (cid, _) in enumerate(dense):
            fused[cid] = fused.get(cid, 0.0) + 1.0 / (rrf_k + rank + 1)
        for rank, (cid, _) in enumerate(sparse):
            fused[cid] = fused.get(cid, 0.0) + 1.0 / (rrf_k + rank + 1)

        order = sorted(fused.items(), key=lambda x: x[1], reverse=True)
        dense_map = dict(dense)
        sparse_rank = {cid: i + 1 for i, (cid, _) in enumerate(sparse)}
        pool = []
        for cid, score in order[: settings.rerank_candidates]:
            pool.append(RetrievedChunk(
                chunk=self._chunks[cid],
                dense_score=dense_map.get(cid),
                sparse_rank=sparse_rank.get(cid),
                fused_score=score,
            ))
        return rerank(question, pool)
