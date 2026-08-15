"""Safety analytics (Phase 5) — fleet-wide metrics rolled up from every
agent task and human decision seen so far: which tools actually got used,
how often the permission layer blocked a request before a human ever saw
it, the approval rate on paused tasks, and the most common failure
reasons. This is the aggregate counterpart to `app.observability.tracing`,
which renders a single task's timeline.
"""
from __future__ import annotations

import re
from collections import Counter

from app.core.models import (
    AgentTask,
    DecisionLog,
    FailureReasonCount,
    SafetyAnalytics,
    ToolUsageCount,
)

_TOOL_EXECUTED_RE = re.compile(r"^Executed '([^']+)':")
_PERMISSION_DENIED_DETAIL = "Permission denied."


def build_safety_analytics(tasks: list[AgentTask], decisions: list[DecisionLog]) -> SafetyAnalytics:
    tool_usage: Counter[str] = Counter()
    failure_reasons: Counter[str] = Counter()
    blocked_attempts = 0

    for task in tasks:
        for step in task.steps:
            if step.node != "tool_execution":
                continue
            match = _TOOL_EXECUTED_RE.match(step.detail)
            if match:
                tool_usage[match.group(1)] += 1

        if task.status == "denied" and any(step.detail == _PERMISSION_DENIED_DETAIL for step in task.steps):
            blocked_attempts += 1

        if task.status == "failed":
            reason = (task.result.error if task.result else None) or task.final_response or "unknown error"
            failure_reasons[reason] += 1

    approved_actions = sum(1 for d in decisions if d.decision in ("approve", "modify"))
    rejected_actions = sum(1 for d in decisions if d.decision == "reject")
    decided_total = approved_actions + rejected_actions
    approval_rate = round(approved_actions / decided_total, 4) if decided_total else None

    return SafetyAnalytics(
        total_tasks=len(tasks),
        tool_usage=[
            ToolUsageCount(tool_name=name, count=count)
            for name, count in sorted(tool_usage.items(), key=lambda kv: (-kv[1], kv[0]))
        ],
        blocked_attempts=blocked_attempts,
        approved_actions=approved_actions,
        rejected_actions=rejected_actions,
        approval_rate=approval_rate,
        top_failure_reasons=[
            FailureReasonCount(reason=reason, count=count)
            for reason, count in sorted(failure_reasons.items(), key=lambda kv: (-kv[1], kv[0]))
        ],
    )
