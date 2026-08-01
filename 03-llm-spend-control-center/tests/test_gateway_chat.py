from fastapi.testclient import TestClient

from app.main import app


def _payload(**overrides):
    body = {
        "messages": [{"role": "user", "content": "How do I reset my password?"}],
        "team_id": "team-alpha",
        "feature": "support-bot",
    }
    body.update(overrides)
    return body


def test_chat_happy_path_routes_to_a_stub_model():
    with TestClient(app) as client:
        r = client.post("/v1/chat", json=_payload())
        assert r.status_code == 200
        body = r.json()
        assert body["provider"] == "stub"
        assert body["routing_tier"] == 2
        assert body["input_tokens"] > 0
        assert body["output_tokens"] > 0
        assert body["cost_usd"] >= 0
        assert body["request_id"]


def test_chat_can_select_explicit_model():
    with TestClient(app) as client:
        r = client.post("/v1/chat", json=_payload(model="stub-strong"))
        assert r.status_code == 200
        body = r.json()
        assert body["model_used"] == "stub-strong"
        assert body["routing_tier"] is None


def test_chat_unknown_model_returns_404():
    with TestClient(app) as client:
        r = client.post("/v1/chat", json=_payload(model="does-not-exist"))
        assert r.status_code == 404


def test_chat_rejects_empty_messages():
    with TestClient(app) as client:
        r = client.post("/v1/chat", json=_payload(messages=[]))
        assert r.status_code == 422


def test_chat_rejects_missing_team_id():
    with TestClient(app) as client:
        body = _payload()
        del body["team_id"]
        r = client.post("/v1/chat", json=body)
        assert r.status_code == 422
