from fastapi.testclient import TestClient

import app.main as main_module
from app.main import app


def test_review_approve():
    with TestClient(app) as client:
        r = client.post(
            "/v1/review",
            json={"prompt": "What's the weather?", "output": "It's sunny today.", "feature": "weather-bot"},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["decision"] == "approve"
        assert body["findings"] == []


def test_review_pii_is_rewrite():
    with TestClient(app) as client:
        r = client.post(
            "/v1/review",
            json={
                "prompt": "Who do I contact?",
                "output": "Reach out to jane.doe@example.com for help.",
                "feature": "support-bot",
            },
        )
        assert r.status_code == 200
        body = r.json()
        assert body["decision"] == "rewrite"
        assert body["findings"][0]["policy_id"] == "pii_leakage"


def test_review_validates_request_body():
    with TestClient(app) as client:
        r = client.post("/v1/review", json={"prompt": "", "output": "x", "feature": "f"})
        assert r.status_code == 422


def test_rate_limit_returns_429(monkeypatch):
    from app.core.rate_limit import RateLimiter

    monkeypatch.setattr(main_module, "_limiter", RateLimiter(requests_per_minute=1))
    with TestClient(app) as client:
        payload = {"prompt": "hi", "output": "hi there", "feature": "chat-bot"}
        first = client.post("/v1/review", json=payload)
        second = client.post("/v1/review", json=payload)
        assert first.status_code == 200
        assert second.status_code == 429
