from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import _usage_store, app
from app.usage.store import UsageLogEntry


def _seed_spend(team_id: str, cost_usd: float, feature: str = "unconfigured-feature") -> None:
    _usage_store.log(
        UsageLogEntry(
            request_id="seed",
            timestamp=datetime.now(timezone.utc),
            team_id=team_id,
            feature=feature,
            model="stub-fast",
            provider="stub",
            input_tokens=1,
            output_tokens=1,
            latency_ms=1.0,
            status="ok",
            cost_usd=cost_usd,
        )
    )


def _chat_payload(team_id: str, feature: str = "unconfigured-feature", **overrides) -> dict:
    body = {
        "messages": [{"role": "user", "content": "hello"}],
        "team_id": team_id,
        "feature": feature,
    }
    body.update(overrides)
    return body


def test_chat_blocked_when_team_over_daily_budget():
    team_id = "team-budget-test-blocked"
    _seed_spend(team_id, 999.0)  # far beyond the $1/day default limit
    with TestClient(app) as client:
        r = client.post("/v1/chat", json=_chat_payload(team_id))
        assert r.status_code == 402


def test_chat_high_priority_bypasses_block():
    team_id = "team-budget-test-highprio"
    _seed_spend(team_id, 999.0)
    with TestClient(app) as client:
        r = client.post("/v1/chat", json=_chat_payload(team_id, priority="high"))
        assert r.status_code == 200


def test_chat_override_flag_bypasses_block():
    team_id = "team-budget-test-override"
    _seed_spend(team_id, 999.0)
    with TestClient(app) as client:
        r = client.post("/v1/chat", json=_chat_payload(team_id, override_budget_block=True))
        assert r.status_code == 200


def test_chat_warning_included_when_near_limit():
    team_id = "team-budget-test-warning"
    _seed_spend(team_id, 0.85)  # 85% of the $1/day default limit
    with TestClient(app) as client:
        r = client.post("/v1/chat", json=_chat_payload(team_id))
        assert r.status_code == 200
        body = r.json()
        assert body["budget_status"] == "warning"
        assert body["warnings"]


def test_budget_status_endpoint_reports_spend():
    team_id = "team-budget-status-check"
    _seed_spend(team_id, 0.5)
    with TestClient(app) as client:
        r = client.get(f"/v1/budgets/{team_id}")
        assert r.status_code == 200
        body = r.json()
        assert body["team_id"] == team_id
        assert body["spent_usd"] == 0.5


def test_usage_summary_endpoint_shape():
    with TestClient(app) as client:
        r = client.get("/v1/usage/summary")
        assert r.status_code == 200
        body = r.json()
        assert set(body.keys()) == {"by_team", "by_feature", "by_model"}
