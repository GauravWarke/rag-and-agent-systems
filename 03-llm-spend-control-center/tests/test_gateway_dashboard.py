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
