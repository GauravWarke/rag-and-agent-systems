from fastapi.testclient import TestClient

from app.main import app


def _client() -> TestClient:
    return TestClient(app)


def test_list_users():
    with _client() as client:
        r = client.get("/v1/users")
        assert r.status_code == 200
        roles = {u["role"] for u in r.json()}
        assert roles == {"viewer", "analyst", "operator", "admin"}


def test_list_tools():
    with _client() as client:
        r = client.get("/v1/tools")
        assert r.status_code == 200
        assert len(r.json()) == 5


def test_call_tool_directly_low_risk():
    with _client() as client:
        r = client.post(
            "/v1/tools/call",
            json={"user_id": "u_viewer", "tool_name": "calculator", "arguments": {"expression": "6 * 7"}},
        )
        assert r.status_code == 200
        body = r.json()
        assert body["success"] is True
        assert body["output"]["result"] == 42


def test_agent_task_low_risk_completes():
    with _client() as client:
        r = client.post("/v1/agent/tasks", json={"user_id": "u_viewer", "request": "what is 3 + 4?"})
        assert r.status_code == 200
        task = r.json()
        assert task["status"] == "completed"

        fetched = client.get(f"/v1/agent/tasks/{task['id']}")
        assert fetched.status_code == 200
        assert fetched.json()["id"] == task["id"]


def test_agent_task_high_risk_pauses_and_resumes():
    with _client() as client:
        create = client.post(
            "/v1/agent/tasks",
            json={"user_id": "u_operator", "request": "please create a ticket for a login bug"},
        )
        task = create.json()
        assert task["status"] == "awaiting_approval"

        resume = client.post(
            f"/v1/agent/tasks/{task['id']}/resume",
            json={"decision": "approve", "reviewer": "u_admin", "reason": "verified"},
        )
        assert resume.status_code == 200
        resumed = resume.json()
        assert resumed["status"] == "completed"
        assert resumed["result"]["output"]["status"] == "created"


def test_resume_unknown_task_404():
    with _client() as client:
        r = client.post(
            "/v1/agent/tasks/does-not-exist/resume",
            json={"decision": "approve", "reviewer": "x", "reason": "y"},
        )
        assert r.status_code == 404


def test_get_unknown_task_404():
    with _client() as client:
        r = client.get("/v1/agent/tasks/does-not-exist")
        assert r.status_code == 404


def test_approval_queue_and_decision_log_via_http():
    with _client() as client:
        create = client.post(
            "/v1/agent/tasks",
            json={"user_id": "u_operator", "request": "please create a ticket for a login bug"},
        )
        task = create.json()
        assert task["status"] == "awaiting_approval"

        queue = client.get("/v1/agent/approvals")
        assert queue.status_code == 200
        queued_ids = [item["task_id"] for item in queue.json()]
        assert task["id"] in queued_ids

        resume = client.post(
            f"/v1/agent/tasks/{task['id']}/resume",
            json={
                "decision": "modify",
                "reviewer": "u_admin",
                "reason": "tightened the title",
                "modified_arguments": {"title": "Login outage", "description": "cannot log in"},
            },
        )
        assert resume.status_code == 200
        assert resume.json()["status"] == "completed"

        # the resolved task should have left the approval queue
        queue_after = client.get("/v1/agent/approvals")
        assert task["id"] not in [item["task_id"] for item in queue_after.json()]

        decisions = client.get("/v1/agent/decisions", params={"task_id": task["id"]})
        assert decisions.status_code == 200
        logged = decisions.json()
        assert len(logged) == 1
        assert logged[0]["decision"] == "modify"
        assert logged[0]["modified_arguments"]["title"] == "Login outage"


def test_task_trace_via_http():
    with _client() as client:
        create = client.post("/v1/agent/tasks", json={"user_id": "u_viewer", "request": "what is 5 + 5?"})
        task = create.json()

        trace = client.get(f"/v1/agent/tasks/{task['id']}/trace")
        assert trace.status_code == 200
        body = trace.json()
        assert body["task_id"] == task["id"]
        assert len(body["spans"]) == len(task["steps"])
        assert body["total_cost_usd"] >= 0


def test_task_trace_unknown_task_404():
    with _client() as client:
        r = client.get("/v1/agent/tasks/does-not-exist/trace")
        assert r.status_code == 404


def test_safety_analytics_via_http():
    with _client() as client:
        before = client.get("/v1/agent/safety").json()

        client.post("/v1/agent/tasks", json={"user_id": "u_viewer", "request": "what is 6 + 6?"})
        denied = client.post(
            "/v1/agent/tasks",
            json={"user_id": "u_viewer", "request": "please create a ticket for a login bug"},
        )
        assert denied.json()["status"] == "denied"

        approve_flow = client.post(
            "/v1/agent/tasks",
            json={"user_id": "u_operator", "request": "please create a ticket for a login bug"},
        )
        client.post(
            f"/v1/agent/tasks/{approve_flow.json()['id']}/resume",
            json={"decision": "approve", "reviewer": "u_admin", "reason": "verified"},
        )

        r = client.get("/v1/agent/safety")
        assert r.status_code == 200
        body = r.json()
        assert body["total_tasks"] == before["total_tasks"] + 3
        assert body["blocked_attempts"] == before["blocked_attempts"] + 1
        assert body["approved_actions"] == before["approved_actions"] + 1
        assert body["approval_rate"] == 1.0
        tool_names = {entry["tool_name"] for entry in body["tool_usage"]}
        assert "calculator" in tool_names
        assert "ticket_create" in tool_names
