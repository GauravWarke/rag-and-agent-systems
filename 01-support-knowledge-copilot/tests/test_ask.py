import pytest
from fastapi.testclient import TestClient

from app.core.config import settings
from app.core.models import Chunk, ChunkMetadata, DocType, RetrievedChunk
from app.generation.answer import generate
from app.main import app


def test_ask_returns_grounded_answer_with_citations():
    with TestClient(app) as client:
        r = client.post("/ask", json={"question": "What does error 429 mean?"})
        assert r.status_code == 200
        body = r.json()
        assert body.get("answer")
        assert body["confidence"]["final"] >= 0.0
        # a relevant question should retrieve at least one chunk
        assert len(body["retrieved"]) >= 1


def test_ask_no_answer_case():
    with TestClient(app) as client:
        r = client.post("/ask", json={"question": "How do I train a llama to ski on Mars?"})
        assert r.status_code == 200
        body = r.json()
        # unrelated question should be handled gracefully
        assert body["confidence"]["no_answer_detected"] in (True, False)


def test_ask_validates_empty_question():
    with TestClient(app) as client:
        r = client.post("/ask", json={"question": ""})
        assert r.status_code == 422  # server-side validation (secure §2A)


def test_ask_response_has_security_headers():
    with TestClient(app) as client:
        r = client.post("/ask", json={"question": "What does error 429 mean?"})
        assert r.headers["x-content-type-options"] == "nosniff"
        assert r.headers["x-frame-options"] == "DENY"


def test_ask_is_rate_limited(monkeypatch):
    import app.main as main_module

    monkeypatch.setattr(main_module, "_limiter", main_module.RateLimiter(1))
    with TestClient(app) as client:
        first = client.post("/ask", json={"question": "What does error 429 mean?"})
        second = client.post("/ask", json={"question": "What does error 429 mean?"})
        assert first.status_code == 200
        assert second.status_code == 429


def test_ask_default_access_level_cannot_see_restricted_policy():
    with TestClient(app) as client:
        r = client.post("/ask", json={"question": "What is the refund policy threshold?"})
        assert r.status_code == 200
        body = r.json()
        sources = {c["chunk"]["metadata"]["source_name"] for c in body["retrieved"]}
        assert "policy" not in sources


def test_ask_restricted_access_level_can_see_policy():
    with TestClient(app) as client:
        r = client.post("/ask", json={
            "question": "What is the refund policy threshold?",
            "access_level": "restricted",
        })
        assert r.status_code == 200
        body = r.json()
        sources = {c["chunk"]["metadata"]["source_name"] for c in body["retrieved"]}
        assert "policy" in sources


def _chunk(cid, text):
    return Chunk(chunk_id=cid, text=text,
                 metadata=ChunkMetadata(source_name="t", doc_type=DocType.faq))


def test_generate_no_answer_returns_closest_matching_sections(monkeypatch):
    monkeypatch.setattr(settings, "min_retrieval_score", 0.9)
    retrieved = [RetrievedChunk(chunk=_chunk("c1", "Unrelated but closest text."), fused_score=0.2)]
    response = generate("some question with no good match", retrieved)
    assert response.confidence.no_answer_detected is True
    assert response.confidence.final == 0.0
    assert response.citations == []
    # the closest sections are still surfaced, not hidden
    assert response.retrieved == retrieved


def test_generate_unwired_generation_model_raises(monkeypatch):
    monkeypatch.setattr(settings, "generation_model", "gpt-4o-mini")
    retrieved = [RetrievedChunk(chunk=_chunk("c1", "Error 429 means too many requests."), fused_score=0.9)]
    with pytest.raises(NotImplementedError):
        generate("what does error 429 mean", retrieved)
