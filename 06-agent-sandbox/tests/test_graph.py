from datetime import datetime, timezone

from app.agent.graph import resume_task, run_task
from app.agent.planner import Planner, ToolPlan
from app.core.models import AgentTaskRequest, ResumeTaskRequest

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


class _FixedPlanner(Planner):
    name = "fixed"

    def __init__(self, plan: ToolPlan) -> None:
        self._plan = plan

    def plan(self, request: str) -> ToolPlan:
        return self._plan


def test_low_risk_tool_completes_immediately():
    req = AgentTaskRequest(user_id="u_viewer", request="what is 2 + 2?")
    task = run_task(req, now=_NOW)
    assert task.status == "completed"
    assert task.result.success is True
    assert [s.node for s in task.steps][:3] == ["intake", "plan", "tool_selection"]


def test_unknown_user_is_denied():
    req = AgentTaskRequest(user_id="ghost", request="what is 2 + 2?")
    task = run_task(req, now=_NOW)
    assert task.status == "denied"


def test_no_matching_tool_fails_gracefully():
    req = AgentTaskRequest(user_id="u_viewer", request="tell me a joke")
    task = run_task(req, now=_NOW)
    assert task.status == "failed"
    assert "tool" in task.final_response.lower()


def test_role_without_access_is_denied():
    req = AgentTaskRequest(user_id="u_viewer", request="read file welcome.txt")
    task = run_task(req, now=_NOW)
    assert task.status == "denied"


def test_medium_risk_pauses_then_resumes_on_approval():
    plan = ToolPlan(
        tool_name="csv_query", arguments={"column": "plan", "value": "pro"}, reasoning="r", confidence=0.9
    )
    req = AgentTaskRequest(user_id="u_analyst", request="find pro customers")
    task = run_task(req, now=_NOW, planner=_FixedPlanner(plan))
    assert task.status == "awaiting_confirmation"
    assert task.pending_action.tool_name == "csv_query"

    resumed = resume_task(
        task,
        ResumeTaskRequest(decision="approve", reviewer="u_analyst", reason="confirmed by requester"),
        now=_NOW,
    )
    assert resumed.status == "completed"
    assert resumed.result.success is True
    assert resumed.pending_action is None


def test_high_risk_pauses_then_resumes_on_approval():
    plan = ToolPlan(
        tool_name="ticket_create",
        arguments={"title": "Broken login", "description": "User cannot log in."},
        reasoning="r",
        confidence=0.9,
    )
    req = AgentTaskRequest(user_id="u_operator", request="create a ticket for a broken login")
    task = run_task(req, now=_NOW, planner=_FixedPlanner(plan))
    assert task.status == "awaiting_approval"

    resumed = resume_task(
        task,
        ResumeTaskRequest(decision="approve", reviewer="u_admin", reason="looks legitimate"),
        now=_NOW,
    )
    assert resumed.status == "completed"
    assert resumed.result.output["status"] == "created"


def test_high_risk_reject_denies_task():
    plan = ToolPlan(
        tool_name="ticket_create",
        arguments={"title": "Broken login", "description": "User cannot log in."},
        reasoning="r",
        confidence=0.9,
    )
    req = AgentTaskRequest(user_id="u_operator", request="create a ticket for a broken login")
    task = run_task(req, now=_NOW, planner=_FixedPlanner(plan))

    resumed = resume_task(
        task,
        ResumeTaskRequest(decision="reject", reviewer="u_admin", reason="not enough detail"),
        now=_NOW,
    )
    assert resumed.status == "denied"
    assert resumed.pending_action is None


def test_resuming_a_completed_task_raises():
    req = AgentTaskRequest(user_id="u_viewer", request="what is 2 + 2?")
    task = run_task(req, now=_NOW)
    try:
        resume_task(
            task, ResumeTaskRequest(decision="approve", reviewer="x", reason="y"), now=_NOW
        )
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_failed_tool_falls_back_to_safer_alternative():
    plan = ToolPlan(
        tool_name="csv_query", arguments={"column": "ssn", "value": "123"}, reasoning="r", confidence=0.9
    )
    req = AgentTaskRequest(user_id="u_analyst", request="look up ssn 123")
    task = run_task(req, now=_NOW, planner=_FixedPlanner(plan))
    resumed = resume_task(
        task, ResumeTaskRequest(decision="approve", reviewer="u_analyst", reason="ok"), now=_NOW
    )
    fallback_steps = [s for s in resumed.steps if "safer alternative" in s.detail]
    assert fallback_steps
    assert resumed.result.tool_name == "web_search"
