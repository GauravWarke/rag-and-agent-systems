from app.core.models import Chunk, ChunkMetadata, DocType
from app.retrieval.hybrid import HybridRetriever


def _chunk(cid, text):
    return Chunk(chunk_id=cid, text=text,
                 metadata=ChunkMetadata(source_name="t", doc_type=DocType.faq))


def test_hybrid_retrieves_relevant_chunk():
    r = HybridRetriever()
    r.index([
        _chunk("a", "Error 429 means too many requests, wait and retry."),
        _chunk("b", "The uploader accepts PDF and PNG files."),
    ])
    out = r.retrieve("what is error 429", strategy="hybrid")
    assert out
    assert out[0].chunk.chunk_id == "a"
