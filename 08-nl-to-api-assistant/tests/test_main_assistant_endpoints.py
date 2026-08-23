from fastapi.testclient import TestClient

from app.main import app


def _client() -> TestClient:
    return TestClient(app)


def test_read_only_workflow_completes_via_http():
    with _client() as client:
        r = client.post("/v1/assistant/workflows", json={"user_id": "u1", "request": "get customer cust_2"})
        assert r.status_code == 200
        body = r.json()
        assert body["status"] == "completed"
        assert body["result"]["id"] == "cust_2"

        fetched = client.get(f"/v1/assistant/workflows/{body['id']}")
        assert fetched.status_code == 200
        assert fetched.json()["id"] == body["id"]


def test_high_risk_workflow_pauses_and_resumes_via_http():
    with _client() as client:
        create = client.post(
            "/v1/assistant/workflows",
            json={"user_id": "u1", "request": "issue a refund of $8 for inv_1, service outage credit"},
        )
        assert create.status_code == 200
        workflow = create.json()
        assert workflow["status"] == "awaiting_approval"

        resume = client.post(
            f"/v1/assistant/workflows/{workflow['id']}/resume",
            json={"decision": "approve", "reviewer": "admin_1", "reason": "confirmed outage"},
        )
        assert resume.status_code == 200
        assert resume.json()["status"] == "completed"


def test_resume_unknown_workflow_404():
    with _client() as client:
        r = client.post(
            "/v1/assistant/workflows/does-not-exist/resume",
            json={"decision": "approve", "reviewer": "admin_1", "reason": "n/a"},
        )
        assert r.status_code == 404


def test_get_unknown_workflow_404():
    with _client() as client:
        r = client.get("/v1/assistant/workflows/does-not-exist")
        assert r.status_code == 404


def test_resume_twice_returns_400():
    with _client() as client:
        create = client.post(
            "/v1/assistant/workflows",
            json={"user_id": "u1", "request": "issue a refund of $8 for inv_3, double resume test"},
        )
        workflow_id = create.json()["id"]
        first = client.post(
            f"/v1/assistant/workflows/{workflow_id}/resume",
            json={"decision": "approve", "reviewer": "admin_1", "reason": "ok"},
        )
        assert first.status_code == 200
        second = client.post(
            f"/v1/assistant/workflows/{workflow_id}/resume",
            json={"decision": "approve", "reviewer": "admin_1", "reason": "ok"},
        )
        assert second.status_code == 400


def test_chained_workflow_via_http():
    with _client() as client:
        create = client.post(
            "/v1/assistant/workflows",
            json={
                "user_id": "u1",
                "request": (
                    "find customer by email ben@example.com, then create a support ticket about billing"
                ),
            },
        )
        assert create.status_code == 200
        workflow = create.json()
        assert workflow["status"] == "awaiting_confirmation"
        assert len(workflow["chain"]) == 2
        assert workflow["chain"][0]["status"] == "completed"

        resume = client.post(
            f"/v1/assistant/workflows/{workflow['id']}/resume",
            json={"decision": "approve", "reviewer": "admin_1", "reason": "fine"},
        )
        assert resume.status_code == 200
        body = resume.json()
        assert body["status"] == "completed"
        assert body["chain"][-1]["status"] == "completed"


def test_list_workflows_via_http():
    with _client() as client:
        before = len(client.get("/v1/assistant/workflows").json())
        client.post("/v1/assistant/workflows", json={"user_id": "u1", "request": "get customer cust_1"})
        after = client.get("/v1/assistant/workflows").json()
        assert len(after) == before + 1
