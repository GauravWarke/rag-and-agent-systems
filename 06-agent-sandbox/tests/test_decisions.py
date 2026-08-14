from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from app.agent.decisions import DecisionStore, build_decision_log
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


def _paused_ticket_task():
    plan = ToolPlan(
        tool_name="ticket_create",
        arguments={"title": "Broken login", "description": "User cannot log in."},
        reasoning="r",
        confidence=0.9,
    )
    req = AgentTaskRequest(user_id="u_operator", request="create a ticket for a broken login")
    return run_task(req, now=_NOW, planner=_FixedPlanner(plan))


def test_modify_decision_requires_modified_arguments():
    with pytest.raises(ValidationError):
        ResumeTaskRequest(decision="modify", reviewer="u_admin", reason="need to fix the title")


def test_modify_decision_runs_with_edited_arguments():
    task = _paused_ticket_task()
    resumed = resume_task(
        task,
        ResumeTaskRequest(
            decision="modify",
            reviewer="u_admin",
            reason="tightened the title",
            modified_arguments={"title": "Login outage", "description": "User cannot log in."},
        ),
        now=_NOW,
    )
    assert resumed.status == "completed"
    assert resumed.result.output["status"] == "created"


def test_replan_decision_reroutes_to_a_new_plan():
    task = _paused_ticket_task()
    new_plan = ToolPlan(tool_name="calculator", arguments={"expression": "6 * 7"}, reasoning="safer tool", confidence=0.5)
    resumed = resume_task(
        task,
        ResumeTaskRequest(decision="replan", reviewer="u_admin", reason="ticket wasn't warranted"),
        now=_NOW,
        planner=_FixedPlanner(new_plan),
    )
    assert resumed.status == "completed"
    assert resumed.result.tool_name == "calculator"
    assert resumed.pending_action is None


def test_replan_can_pause_again_on_another_risky_tool():
    task = _paused_ticket_task()
    same_plan = ToolPlan(
        tool_name="ticket_create",
        arguments={"title": "Broken login", "description": "still broken"},
        reasoning="still a ticket",
        confidence=0.8,
    )
    resumed = resume_task(
        task,
        ResumeTaskRequest(decision="replan", reviewer="u_admin", reason="wanted a second look"),
        now=_NOW,
        planner=_FixedPlanner(same_plan),
    )
    assert resumed.status == "awaiting_approval"
    assert resumed.pending_action.tool_name == "ticket_create"


def test_build_decision_log_captures_original_and_modified_arguments():
    task = _paused_ticket_task()
    req = ResumeTaskRequest(
        decision="modify",
        reviewer="u_admin",
        reason="tightened the title",
        modified_arguments={"title": "Login outage", "description": "User cannot log in."},
    )
    resumed = resume_task(task, req, now=_NOW)
    log = build_decision_log(task, req, resumed, now=_NOW)

    assert log.task_id == task.id
    assert log.tool_name == "ticket_create"
    assert log.risk_level == "high"
    assert log.decision == "modify"
    assert log.original_arguments == task.pending_action.arguments
    assert log.modified_arguments == req.modified_arguments
    assert log.outcome_status == "completed"


def test_decision_store_add_all_and_filter_by_task():
    store = DecisionStore()
    task_a = _paused_ticket_task()
    task_b = _paused_ticket_task()
    req = ResumeTaskRequest(decision="reject", reviewer="u_admin", reason="not enough detail")

    for task in (task_a, task_b):
        resumed = resume_task(task, req, now=_NOW)
        store.add(build_decision_log(task, req, resumed, now=_NOW))

    assert len(store.all()) == 2
    assert [d.task_id for d in store.for_task(task_a.id)] == [task_a.id]
