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
        assert body["final_output"] is not None
        assert "jane.doe@example.com" not in body["final_output"]


def test_review_block_is_queued_for_human_review():
    with TestClient(app) as client:
        review_resp = client.post(
            "/v1/review",
            json={"prompt": "Insult me", "output": "Well, shut up and listen.", "feature": "chat-bot"},
        )
        assert review_resp.status_code == 200
        body = review_resp.json()
        assert body["decision"] == "block"
        assert body["final_output"] is None
        request_id = body["request_id"]

        queue = client.get("/v1/audit/queue")
        assert queue.status_code == 200
        assert any(e["request_id"] == request_id for e in queue.json())

        decided = client.post(
            f"/v1/audit/{request_id}/review",
            json={"reviewer": "alice", "action": "reject", "note": "confirmed unsafe"},
        )
        assert decided.status_code == 200
        assert decided.json()["reviewed"] is True

        queue_after = client.get("/v1/audit/queue")
        assert all(e["request_id"] != request_id for e in queue_after.json())


def test_audit_review_returns_404_for_unknown_request_id():
    with TestClient(app) as client:
        r = client.post(
            "/v1/audit/does-not-exist/review",
            json={"reviewer": "alice", "action": "approve"},
        )
        assert r.status_code == 404


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
