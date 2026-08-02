from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import _quality_store, app
from app.quality.store import QualityCheckEntry


def _payload(content: str, feature: str = "generic-feature", **overrides) -> dict:
    body = {
        "messages": [{"role": "user", "content": content}],
        "team_id": "team-alpha",
        "feature": feature,
    }
    body.update(overrides)
    return body


def _seed_misses(feature: str, count: int) -> None:
    for i in range(count):
        _quality_store.log(
            QualityCheckEntry(
                request_id=f"seed-{feature}-{i}",
                timestamp=datetime.now(timezone.utc),
                team_id="team-alpha",
                feature=feature,
                cheap_model="stub-fast",
                reference_model="stub-strong",
                similarity_score=0.1,
                is_routing_miss=True,
                prompt_preview="seeded miss",
                reason="seeded for test",
            )
        )


def test_high_priority_escalates_to_strongest_tier():
    with TestClient(app) as client:
        r = client.post(
            "/v1/chat",
            json=_payload("Extract the order ID from this text.", feature="escalation-high-prio", priority="high"),
        )
        assert r.status_code == 200
        body = r.json()
        assert body["escalated"] is True
        assert body["escalation_reason"] == "high_priority"
        assert body["routing_tier"] == 3
        assert body["model_used"] == "stub-strong"


def test_repeated_routing_misses_escalate_future_requests_for_that_feature():
    feature = "flaky-routing-feature"
    _seed_misses(feature, settings.escalation_min_samples)
    with TestClient(app) as client:
        r = client.post("/v1/chat", json=_payload("Extract the order ID from this text.", feature=feature))
        assert r.status_code == 200
        body = r.json()
        assert body["escalated"] is True
        assert body["escalation_reason"] == "low_confidence"
        assert body["routing_tier"] == 3


def test_few_routing_misses_do_not_escalate_yet():
    feature = "barely-flaky-feature"
    _seed_misses(feature, settings.escalation_min_samples - 1)
    with TestClient(app) as client:
        r = client.post("/v1/chat", json=_payload("Extract the order ID from this text.", feature=feature))
        assert r.status_code == 200
        body = r.json()
        assert body["escalated"] is False
        assert body["routing_tier"] == 1


def test_already_top_tier_requests_are_never_marked_escalated():
    with TestClient(app) as client:
        r = client.post(
            "/v1/chat",
            json=_payload("Please analyze and diagnose this outage.", feature="already-top-tier", priority="high"),
        )
        assert r.status_code == 200
        body = r.json()
        assert body["routing_tier"] == 3
        assert body["escalated"] is False


def test_sampled_verification_logs_a_quality_check(monkeypatch):
    monkeypatch.setattr(settings, "quality_sample_rate", 1.0)
    feature = "sampling-test-feature"
    with TestClient(app) as client:
        r = client.post("/v1/chat", json=_payload("Extract the order ID from this text.", feature=feature))
        assert r.status_code == 200
    assert _quality_store.sample_count_for_feature(feature) == 1


def test_zero_sample_rate_never_triggers_verification(monkeypatch):
    monkeypatch.setattr(settings, "quality_sample_rate", 0.0)
    feature = "never-sampled-feature"
    with TestClient(app) as client:
        r = client.post("/v1/chat", json=_payload("Extract the order ID from this text.", feature=feature))
        assert r.status_code == 200
    assert _quality_store.sample_count_for_feature(feature) == 0


def test_quality_summary_endpoint_shape():
    with TestClient(app) as client:
        r = client.get("/v1/quality/summary")
        assert r.status_code == 200
        body = r.json()
        assert set(body.keys()) == {"total_checks", "routing_miss_count", "pass_rate", "misses"}
