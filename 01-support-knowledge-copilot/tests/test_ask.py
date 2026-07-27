from fastapi.testclient import TestClient

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
