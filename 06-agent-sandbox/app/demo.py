"""Portfolio walkthrough (Phase 6): runs one safe, low-risk task through the
agent workflow to completion, then a sensitive, high-risk task that the
permission layer routes to human approval instead of executing outright.
Prints a readable transcript of both — no API key or network access
required, matching this repo's offline-runnable-by-default convention.
"""
from __future__ import annotations

from datetime import datetime, timezone

from app.agent.graph import run_task
from app.core.models import AgentTask, AgentTaskRequest


def _render_task(label: str, task: AgentTask) -> str:
    lines = [f"=== {label} ===", f"request: {task.request!r} (user={task.user_id})", f"status: {task.status}"]
    for step in task.steps:
        lines.append(f"  [{step.node}] {step.detail}")
    if task.pending_action is not None:
        lines.append(
            f"pending approval: {task.pending_action.tool_name}"
            f" (risk={task.pending_action.risk_level}) args={task.pending_action.arguments}"
        )
    if task.final_response is not None:
        lines.append(f"final response: {task.final_response}")
    return "\n".join(lines)


def run_demo() -> str:
    now = datetime.now(timezone.utc)

    safe_task = run_task(
        AgentTaskRequest(user_id="u_analyst", request="what is 340 * 12 for the quarterly total?"),
        now=now,
    )
    unsafe_task = run_task(
        AgentTaskRequest(user_id="u_operator", request="please create a ticket for a payment outage"),
        now=now,
    )

    return "\n\n".join(
        [
            _render_task("Safe task: low-risk analysis (auto-completes)", safe_task),
            _render_task("Unsafe task: high-risk write (paused for human approval)", unsafe_task),
        ]
    )
