"""Structured, queryable log of every human approval decision (Phase 4) —
records who decided what, on which task, what changed, and why. Kept
separate from the free-text step already appended to `AgentTask.steps` so
it can be listed and filtered on its own for auditing.
"""
from __future__ import annotations

import uuid
from datetime import datetime

from app.core.models import AgentTask, DecisionLog, ResumeTaskRequest


def build_decision_log(task: AgentTask, req: ResumeTaskRequest, updated: AgentTask, now: datetime) -> DecisionLog:
    """Build the audit record for a resume decision. `task` must be the
    task *before* `resume_task` was applied (so `pending_action` is still
    present); `updated` is the result returned by `resume_task`.
    """
    pending = task.pending_action
    if pending is None:
        raise ValueError(f"Task '{task.id}' had no pending action to log a decision for.")
    return DecisionLog(
        id=str(uuid.uuid4()),
        task_id=task.id,
        tool_name=pending.tool_name,
        risk_level=pending.risk_level,
        decision=req.decision,
        reviewer=req.reviewer,
        reason=req.reason,
        original_arguments=pending.arguments,
        modified_arguments=req.modified_arguments,
        outcome_status=updated.status,
        timestamp=now,
    )


class DecisionStore:
    """In-memory append-only audit log, matching this repo's offline-runnable,
    dependency-light convention (see `app.agent.store.TaskStore`)."""

    def __init__(self) -> None:
        self._decisions: list[DecisionLog] = []

    def add(self, decision: DecisionLog) -> DecisionLog:
        self._decisions.append(decision)
        return decision

    def all(self) -> list[DecisionLog]:
        return list(self._decisions)

    def for_task(self, task_id: str) -> list[DecisionLog]:
        return [d for d in self._decisions if d.task_id == task_id]
