from datetime import datetime, timezone

from app.agent.approvals import build_approval_queue
from app.agent.graph import run_task
from app.agent.planner import Planner, ToolPlan
from app.core.models import AgentTaskRequest

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


class _FixedPlanner(Planner):
    name = "fixed"

    def __init__(self, plan: ToolPlan) -> None:
        self._plan = plan

    def plan(self, request: str) -> ToolPlan:
        return self._plan


def test_approval_queue_lists_pending_tasks_with_context():
    plan = ToolPlan(
        tool_name="ticket_create",
        arguments={"title": "Broken login", "description": "User cannot log in."},
        reasoning="looks like a support ticket",
        confidence=0.9,
    )
    req = AgentTaskRequest(user_id="u_operator", request="create a ticket for a broken login")
    task = run_task(req, now=_NOW, planner=_FixedPlanner(plan))

    queue = build_approval_queue([task])
    assert len(queue) == 1
    item = queue[0]
    assert item.task_id == task.id
    assert item.tool_name == "ticket_create"
    assert item.risk_level == "high"
    assert item.arguments == plan.arguments
    assert "looks like a support ticket" in item.reasoning_summary
    assert item.expected_effect


def test_approval_queue_excludes_completed_and_denied_tasks():
    completed = run_task(AgentTaskRequest(user_id="u_viewer", request="what is 2 + 2?"), now=_NOW)
    denied = run_task(AgentTaskRequest(user_id="ghost", request="what is 2 + 2?"), now=_NOW)

    queue = build_approval_queue([completed, denied])
    assert queue == []
