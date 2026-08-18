from app.core.config import settings
from app.core.models import AccessLevel, Chunk, ChunkMetadata, DocType
from app.retrieval.hybrid import HybridRetriever


def _chunk(cid, text, access_level=AccessLevel.internal):
    return Chunk(chunk_id=cid, text=text,
                 metadata=ChunkMetadata(source_name="t", doc_type=DocType.faq,
                                        access_level=access_level))


def test_hybrid_retrieves_relevant_chunk():
    r = HybridRetriever()
    r.index([
        _chunk("a", "Error 429 means too many requests, wait and retry."),
        _chunk("b", "The uploader accepts PDF and PNG files."),
    ])
    out = r.retrieve("what is error 429", strategy="hybrid")
    assert out
    assert out[0].chunk.chunk_id == "a"


def test_hybrid_reranks_fused_pool_and_caps_at_rerank_top_k():
    r = HybridRetriever()
    r.index([_chunk(str(i), f"unrelated document number {i}") for i in range(30)])
    out = r.retrieve("unrelated document", strategy="hybrid")
    assert len(out) <= settings.rerank_top_k
    assert all(c.rerank_score is not None for c in out)


def _access_index():
    r = HybridRetriever()
    r.index([
        _chunk("pub", "Error 429 means too many requests, wait and retry.",
               access_level=AccessLevel.public),
        _chunk("int", "Error 429 internal escalation steps for support staff.",
               access_level=AccessLevel.internal),
        _chunk("res", "Error 429 restricted incident response runbook.",
               access_level=AccessLevel.restricted),
    ])
    return r


def test_public_requester_only_sees_public_chunks():
    out = _access_index().retrieve("error 429", access_level=AccessLevel.public)
    ids = {c.chunk.chunk_id for c in out}
    assert ids == {"pub"}


def test_internal_requester_sees_public_and_internal_but_not_restricted():
    out = _access_index().retrieve("error 429", access_level=AccessLevel.internal)
    ids = {c.chunk.chunk_id for c in out}
    assert ids == {"pub", "int"}
    assert "res" not in ids


def test_restricted_requester_sees_everything():
    out = _access_index().retrieve("error 429", access_level=AccessLevel.restricted)
    ids = {c.chunk.chunk_id for c in out}
    assert ids == {"pub", "int", "res"}


def test_access_control_applies_to_dense_and_sparse_strategies():
    r = _access_index()
    for strategy in ("dense", "sparse", "hybrid"):
        out = r.retrieve("error 429", strategy=strategy, access_level=AccessLevel.public)
        assert all(c.chunk.chunk_id == "pub" for c in out)
