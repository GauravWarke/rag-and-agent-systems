from fastapi.testclient import TestClient

from app.main import app


def test_dashboard_spend_endpoint_shape():
    with TestClient(app) as client:
        client.post(
            "/v1/chat",
            json={
                "messages": [{"role": "user", "content": "Extract the order ID from this text."}],
                "team_id": "team-alpha",
                "feature": "dashboard-test-feature",
            },
        )
        r = client.get("/v1/dashboard/spend")
        assert r.status_code == 200
        body = r.json()
        assert set(body.keys()) == {
            "daily_cost_usd",
            "monthly_cost_usd",
            "monthly_projection_usd",
            "top_expensive_requests",
            "by_team",
            "by_feature",
            "by_model",
        }
        assert body["daily_cost_usd"] >= 0
        assert body["monthly_cost_usd"] >= body["daily_cost_usd"]
        assert isinstance(body["top_expensive_requests"], list)
        assert "dashboard-test-feature" in body["by_feature"]


def test_dashboard_savings_endpoint_shape():
    with TestClient(app) as client:
        client.post(
            "/v1/chat",
            json={
                "messages": [{"role": "user", "content": "Extract the order ID from this text."}],
                "team_id": "team-alpha",
                "feature": "savings-test-feature",
            },
        )
        r = client.get("/v1/dashboard/savings")
        assert r.status_code == 200
        body = r.json()
        assert set(body.keys()) == {
            "strongest_model",
            "request_count",
            "actual_cost_usd",
            "hypothetical_strongest_model_cost_usd",
            "savings_usd",
            "savings_pct",
        }
        assert body["request_count"] >= 1
        assert body["actual_cost_usd"] >= 0
        assert body["hypothetical_strongest_model_cost_usd"] >= 0


def test_dashboard_routing_quality_endpoint_shape():
    with TestClient(app) as client:
        client.post(
            "/v1/chat",
            json={
                "messages": [{"role": "user", "content": "Extract the order ID from this text."}],
                "team_id": "team-alpha",
                "feature": "routing-quality-test-feature",
            },
        )
        r = client.get("/v1/dashboard/routing-quality")
        assert r.status_code == 200
        body = r.json()
        assert set(body.keys()) == {
            "escalation_rate",
            "verifier_pass_rate",
            "latency_ms_by_model",
            "error_rate_by_provider",
        }
        assert 0.0 <= body["escalation_rate"] <= 1.0
        assert 0.0 <= body["verifier_pass_rate"] <= 1.0
        assert isinstance(body["latency_ms_by_model"], dict)
        assert isinstance(body["error_rate_by_provider"], dict)
