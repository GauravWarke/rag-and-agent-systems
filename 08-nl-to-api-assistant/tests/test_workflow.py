from datetime import datetime, timezone

import pytest

from app.main import app
from app.planning.models import CreateWorkflowRequest, ResumeWorkflowRequest
from app.planning.workflow import create_workflow, resume_workflow

_NOW = datetime(2026, 8, 22, tzinfo=timezone.utc)


def _schema() -> dict:
    return app.openapi()


def test_workflow_read_only_completes_immediately():
    workflow = create_workflow(CreateWorkflowRequest(user_id="u1", request="get customer cust_1"), _schema(), now=_NOW)
    assert workflow.status == "completed"
    assert workflow.result["id"] == "cust_1"


def test_workflow_read_only_execution_failure_is_captured():
    workflow = create_workflow(CreateWorkflowRequest(user_id="u1", request="get customer cust_999"), _schema(), now=_NOW)
    assert workflow.status == "failed"
    assert workflow.error is not None


def test_workflow_low_risk_write_awaits_confirmation():
    workflow = create_workflow(
        CreateWorkflowRequest(user_id="u1", request="open a ticket for cust_1 about a login problem"),
        _schema(),
        now=_NOW,
    )
    assert workflow.status == "awaiting_confirmation"
    assert workflow.dry_run_preview is not None
    assert workflow.result is None


def test_workflow_high_risk_write_awaits_approval_then_executes():
    workflow = create_workflow(
        CreateWorkflowRequest(user_id="u1", request="issue a refund of $5 for inv_2, wrong charge"),
        _schema(),
        now=_NOW,
    )
    assert workflow.status == "awaiting_approval"

    approved = resume_workflow(
        workflow,
        ResumeWorkflowRequest(decision="approve", reviewer="admin_1", reason="verified with customer"),
        now=_NOW,
    )
    assert approved.status == "completed"
    assert approved.result["status"] == "issued"


def test_workflow_rejected_does_not_execute():
    workflow = create_workflow(
        CreateWorkflowRequest(user_id="u1", request="issue a refund of $5 for inv_3, goodwill"),
        _schema(),
        now=_NOW,
    )
    rejected = resume_workflow(
        workflow,
        ResumeWorkflowRequest(decision="reject", reviewer="admin_1", reason="not eligible"),
        now=_NOW,
    )
    assert rejected.status == "rejected"
    assert rejected.result is None


def test_workflow_invalid_missing_field():
    workflow = create_workflow(
        CreateWorkflowRequest(user_id="u1", request="open a ticket about a login problem"),
        _schema(),
        now=_NOW,
    )
    assert workflow.status == "invalid"
    assert any(issue.field == "customer_id" for issue in workflow.validation.issues)


def test_workflow_denied_when_no_endpoint_matches():
    workflow = create_workflow(
        CreateWorkflowRequest(user_id="u1", request="asdkjh qweiouqwoeiu zxcvzxcv"),
        _schema(),
        now=_NOW,
    )
    assert workflow.status == "denied"


def test_resume_raises_when_workflow_not_pending():
    workflow = create_workflow(CreateWorkflowRequest(user_id="u1", request="get customer cust_1"), _schema(), now=_NOW)
    assert workflow.status == "completed"
    with pytest.raises(ValueError):
        resume_workflow(
            workflow,
            ResumeWorkflowRequest(decision="approve", reviewer="admin_1", reason="n/a"),
            now=_NOW,
        )
