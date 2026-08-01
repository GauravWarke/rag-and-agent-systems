from fastapi.testclient import TestClient

from app.main import app


def _payload(content: str, feature: str = "generic-feature", **overrides) -> dict:
    body = {
        "messages": [{"role": "user", "content": content}],
        "team_id": "team-alpha",
        "feature": feature,
    }
    body.update(overrides)
    return body


def test_simple_extraction_routes_to_tier_1():
    with TestClient(app) as client:
        r = client.post("/v1/chat", json=_payload("Extract the order ID from this text."))
        assert r.status_code == 200
        body = r.json()
        assert body["routing_tier"] == 1
        assert body["model_used"] == "stub-fast"


def test_reasoning_request_routes_to_tier_3():
    with TestClient(app) as client:
        r = client.post("/v1/chat", json=_payload("Please analyze and diagnose this outage."))
        assert r.status_code == 200
        body = r.json()
        assert body["routing_tier"] == 3
        assert body["model_used"] == "stub-strong"


def test_override_feature_forces_tier_3_regardless_of_text():
    with TestClient(app) as client:
        r = client.post("/v1/chat", json=_payload("List the fields.", feature="legal-review"))
        assert r.status_code == 200
        body = r.json()
        assert body["routing_tier"] == 3
        assert body["model_used"] == "stub-strong"


def test_high_risk_tag_forces_tier_3():
    with TestClient(app) as client:
        r = client.post(
            "/v1/chat",
            json=_payload("List the fields.", risk_tags=["medical"]),
        )
        assert r.status_code == 200
        assert r.json()["routing_tier"] == 3
