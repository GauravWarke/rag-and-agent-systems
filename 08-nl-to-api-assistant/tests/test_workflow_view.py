from fastapi.testclient import TestClient

from app.main import app


def _client() -> TestClient:
    return TestClient(app)


def test_view_unknown_workflow_404():
    with _client() as client:
        r = client.get("/v1/assistant/workflows/does-not-exist/view")
        assert r.status_code == 404


def test_view_of_completed_read_only_workflow():
    with _client() as client:
        create = client.post("/v1/assistant/workflows", json={"user_id": "u1", "request": "get customer cust_2"})
        workflow_id = create.json()["id"]

        view = client.get(f"/v1/assistant/workflows/{workflow_id}/view")
        assert view.status_code == 200
        body = view.json()
        assert body["request"] == "get customer cust_2"
        assert body["status"] == "completed"
        assert body["available_actions"] == []
        assert len(body["planned_calls"]) == 1
        call = body["planned_calls"][0]
        assert call["operation_id"] == "get_customer"
        assert call["status"] == "completed"
        assert call["result"]["id"] == "cust_2"
        assert body["final_result"]["id"] == "cust_2"


def test_view_of_awaiting_approval_workflow_offers_approve_and_reject():
    with _client() as client:
        create = client.post(
            "/v1/assistant/workflows",
            json={"user_id": "u1", "request": "issue a refund of $8 for inv_1, service outage credit"},
        )
        workflow_id = create.json()["id"]

        view = client.get(f"/v1/assistant/workflows/{workflow_id}/view").json()
        assert view["status"] == "awaiting_approval"
        assert set(view["available_actions"]) == {"approve", "reject"}
        assert view["dry_run_preview"] is not None
        assert view["planned_calls"][0]["operation_id"] == "issue_refund"
        assert view["planned_calls"][0]["status"] == "pending"
        assert view["final_result"] is None

        client.post(
            f"/v1/assistant/workflows/{workflow_id}/resume",
            json={"decision": "approve", "reviewer": "admin_1", "reason": "confirmed outage"},
        )
        resolved = client.get(f"/v1/assistant/workflows/{workflow_id}/view").json()
        assert resolved["status"] == "completed"
        assert resolved["available_actions"] == []
        assert resolved["final_result"]["invoice_id"] == "inv_1"


def test_view_of_chained_workflow_lists_each_step():
    with _client() as client:
        create = client.post(
            "/v1/assistant/workflows",
            json={
                "user_id": "u1",
                "request": "find customer by email ben@example.com, then create a support ticket about billing",
            },
        )
        workflow_id = create.json()["id"]

        view = client.get(f"/v1/assistant/workflows/{workflow_id}/view").json()
        assert view["status"] == "awaiting_confirmation"
        assert len(view["planned_calls"]) == 2
        assert view["planned_calls"][0]["operation_id"] == "list_customers"
        assert view["planned_calls"][0]["status"] == "completed"
        assert view["planned_calls"][1]["operation_id"] == "create_ticket"
        assert view["planned_calls"][1]["status"] == "pending"
