import pytest

from app.core.config import settings
from app.core.models import Chunk, ChunkMetadata, DocType, RetrievedChunk
from app.retrieval.reranker import rerank


def _candidate(cid, text, fused_score):
    chunk = Chunk(chunk_id=cid, text=text,
                  metadata=ChunkMetadata(source_name="t", doc_type=DocType.faq))
    return RetrievedChunk(chunk=chunk, fused_score=fused_score)


def test_rerank_scores_and_reorders_by_relevance():
    candidates = [
        _candidate("low", "The uploader accepts PDF and PNG files.", fused_score=0.9),
        _candidate("high", "Error 429 means too many requests, wait and retry.", fused_score=0.1),
    ]
    out = rerank("what does error 429 mean", candidates)
    assert out[0].chunk.chunk_id == "high"
    assert out[0].rerank_score is not None
    assert out[0].rerank_score >= out[1].rerank_score


def test_rerank_keeps_only_top_k(monkeypatch):
    monkeypatch.setattr(settings, "rerank_top_k", 2)
    candidates = [_candidate(str(i), f"chunk number {i} about billing", 0.0) for i in range(5)]
    out = rerank("billing question", candidates)
    assert len(out) == 2


def test_rerank_unknown_model_raises(monkeypatch):
    monkeypatch.setattr(settings, "rerank_model", "cross-encoder/ms-marco-MiniLM-L-6-v2")
    with pytest.raises(NotImplementedError):
        rerank("q", [_candidate("a", "text", 0.0)])
