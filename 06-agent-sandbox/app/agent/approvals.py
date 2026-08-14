"""Read-model over paused agent tasks: the human approval queue (Phase 4).

Turns the raw `AgentTask` list into the compact view a reviewer needs —
proposed action, risk level, a one-line model reasoning summary, and the
expected effect — without exposing the full step trace.
"""
from __future__ import annotations

from app.core.models import AgentTask, ApprovalQueueItem
from app.tools.registry import get_tool

_PENDING_STATUSES = ("awaiting_confirmation", "awaiting_approval")


def build_approval_queue(tasks: list[AgentTask]) -> list[ApprovalQueueItem]:
    items: list[ApprovalQueueItem] = []
    for task in tasks:
        if task.status not in _PENDING_STATUSES or task.pending_action is None:
            continue
        reasoning = next((s.detail for s in reversed(task.steps) if s.node == "plan"), "")
        tool = get_tool(task.pending_action.tool_name)
        expected_effect = tool.spec.description if tool else "Unknown tool."
        items.append(
            ApprovalQueueItem(
                task_id=task.id,
                user_id=task.user_id,
                request=task.request,
                status=task.status,
                tool_name=task.pending_action.tool_name,
                arguments=task.pending_action.arguments,
                risk_level=task.pending_action.risk_level,
                reasoning_summary=reasoning,
                expected_effect=expected_effect,
                created_at=task.created_at,
                updated_at=task.updated_at,
            )
        )
    return items
