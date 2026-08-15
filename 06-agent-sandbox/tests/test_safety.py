from datetime import datetime, timezone

from app.agent.decisions import build_decision_log
from app.agent.graph import resume_task, run_task
from app.core.models import AgentTaskRequest, ResumeTaskRequest
from app.observability.safety import build_safety_analytics

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_safety_analytics_on_empty_history():
    analytics = build_safety_analytics(tasks=[], decisions=[])

    assert analytics.total_tasks == 0
    assert analytics.tool_usage == []
    assert analytics.blocked_attempts == 0
    assert analytics.approved_actions == 0
    assert analytics.rejected_actions == 0
    assert analytics.approval_rate is None
    assert analytics.top_failure_reasons == []


def test_safety_analytics_counts_tool_usage_across_tasks():
    completed = run_task(AgentTaskRequest(user_id="u_viewer", request="what is 3 + 4?"), now=_NOW)
    also_completed = run_task(AgentTaskRequest(user_id="u_viewer", request="what is 10 - 2?"), now=_NOW)

    analytics = build_safety_analytics(tasks=[completed, also_completed], decisions=[])

    assert analytics.total_tasks == 2
    assert [t.model_dump() for t in analytics.tool_usage] == [{"tool_name": "calculator", "count": 2}]


def test_safety_analytics_counts_permission_denied_as_blocked_attempt():
    denied = run_task(
        AgentTaskRequest(user_id="u_viewer", request="please create a ticket for a login bug"), now=_NOW
    )
    assert denied.status == "denied"

    analytics = build_safety_analytics(tasks=[denied], decisions=[])

    assert analytics.blocked_attempts == 1
    assert analytics.tool_usage == []


def test_safety_analytics_reports_approval_rate_and_rejected_actions():
    approved_task = run_task(
        AgentTaskRequest(user_id="u_operator", request="please create a ticket for a login bug"), now=_NOW
    )
    approve_req = ResumeTaskRequest(decision="approve", reviewer="u_admin", reason="verified")
    approved_updated = resume_task(approved_task, approve_req, now=_NOW)
    approve_log = build_decision_log(approved_task, approve_req, approved_updated, now=_NOW)

    rejected_task = run_task(
        AgentTaskRequest(user_id="u_operator", request="please create a ticket for a billing bug"), now=_NOW
    )
    reject_req = ResumeTaskRequest(decision="reject", reviewer="u_admin", reason="duplicate")
    rejected_updated = resume_task(rejected_task, reject_req, now=_NOW)
    reject_log = build_decision_log(rejected_task, reject_req, rejected_updated, now=_NOW)

    analytics = build_safety_analytics(
        tasks=[approved_updated, rejected_updated], decisions=[approve_log, reject_log]
    )

    assert analytics.approved_actions == 1
    assert analytics.rejected_actions == 1
    assert analytics.approval_rate == 0.5


def test_safety_analytics_tracks_top_failure_reasons():
    failed = run_task(AgentTaskRequest(user_id="u_analyst", request="read file ../../etc/passwd"), now=_NOW)
    assert failed.status == "failed"

    analytics = build_safety_analytics(tasks=[failed], decisions=[])

    assert analytics.top_failure_reasons
    assert analytics.top_failure_reasons[0].count == 1
