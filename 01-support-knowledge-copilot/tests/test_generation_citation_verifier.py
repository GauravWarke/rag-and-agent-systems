from app.core.models import Chunk, ChunkMetadata, DocType, RetrievedChunk
from app.generation.citation_verifier import verify_citations, verify_claim


def _retrieved(cid, text):
    chunk = Chunk(chunk_id=cid, text=text,
                  metadata=ChunkMetadata(source_name="t", doc_type=DocType.faq))
    return RetrievedChunk(chunk=chunk, fused_score=0.5)


def test_verify_claim_supported_when_words_overlap():
    supported, evidence = verify_claim(
        "Error 429 means too many requests",
        "Error 429 means too many requests, wait and retry.",
    )
    assert supported is True
    assert evidence.startswith("Error 429")


def test_verify_claim_unsupported_when_unrelated():
    supported, _ = verify_claim("The sky is purple today", "Invoices are due on the 1st of the month.")
    assert supported is False


def test_verify_citations_builds_citation_records():
    claims = [("Error 429 means too many requests", _retrieved("c1", "Error 429 means too many requests, retry later."))]
    citations = verify_citations(claims)
    assert len(citations) == 1
    assert citations[0].chunk_id == "c1"
    assert citations[0].supported is True
    assert citations[0].evidence_span
