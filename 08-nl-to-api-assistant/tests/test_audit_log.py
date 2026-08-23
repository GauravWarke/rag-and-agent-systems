import logging
from datetime import datetime, timezone

from app.main import app
from app.planning.audit_log import log_workflow_event
from app.planning.models import CreateWorkflowRequest
from app.planning.workflow import create_workflow

_NOW = datetime(2026, 8, 22, tzinfo=timezone.utc)


def _schema() -> dict:
    return app.openapi()


def test_log_workflow_event_captures_single_call_fields(caplog):
    workflow = create_workflow(CreateWorkflowRequest(user_id="u1", request="get customer cust_1"), _schema(), now=_NOW)

    with caplog.at_level(logging.INFO, logger="app.assistant.audit"):
        log_workflow_event("create", workflow)

    assert len(caplog.records) == 1
    record = caplog.records[0]
    assert record.event == "create"
    assert record.workflow_id == workflow.id
    assert record.user_id == "u1"
    assert record.status == "completed"
    assert record.calls == [
        {
            "segment": "get customer cust_1",
            "operation_id": "get_customer",
            "parameters": {"customer_id": "cust_1"},
            "status": "completed",
            "error": None,
        }
    ]
    assert record.validation_valid is True
    assert record.result["id"] == "cust_1"


def test_log_workflow_event_captures_chain_calls(caplog):
    request = "find customer by email ana@example.com, then create a support ticket about a login problem"
    workflow = create_workflow(CreateWorkflowRequest(user_id="u1", request=request), _schema(), now=_NOW)

    with caplog.at_level(logging.INFO, logger="app.assistant.audit"):
        log_workflow_event("create", workflow)

    record = caplog.records[0]
    assert record.status == "awaiting_confirmation"
    assert len(record.calls) == 2
    assert record.calls[0]["operation_id"] == "list_customers"
    assert record.calls[0]["status"] == "completed"
    assert record.calls[1]["operation_id"] == "create_ticket"
    assert record.calls[1]["status"] == "pending"


def test_workflow_creation_emits_audit_log_via_http(caplog):
    from fastapi.testclient import TestClient

    with caplog.at_level(logging.INFO, logger="app.assistant.audit"), TestClient(app) as client:
        r = client.post("/v1/assistant/workflows", json={"user_id": "u1", "request": "get customer cust_2"})
        assert r.status_code == 200

    assert any(record.event == "create" and record.workflow_id == r.json()["id"] for record in caplog.records)
