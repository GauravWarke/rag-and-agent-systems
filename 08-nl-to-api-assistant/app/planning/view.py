"""Builds the Phase 5 "workflow UI" read-model: given a `Workflow`, produce
a `WorkflowView` that a frontend can render directly — the request, the
planned call(s) whether single or chained, the dry-run preview, which
actions a reviewer can currently take, and the final result — without
needing to know the difference between a single-call and a chained
workflow.
"""
from __future__ import annotations

from app.planning.models import PlannedCallView, ResumeDecision, Workflow, WorkflowView

_AWAITING_STATUSES = {"awaiting_confirmation", "awaiting_approval"}


def _available_actions(workflow: Workflow) -> list[ResumeDecision]:
    if workflow.status in _AWAITING_STATUSES:
        return ["approve", "reject"]
    return []


def _single_call_view(workflow: Workflow) -> list[PlannedCallView]:
    if workflow.plan is None or workflow.plan.operation_id is None:
        return []
    plan = workflow.plan
    status: str = "pending"
    if workflow.status in ("completed",):
        status = "completed"
    elif workflow.status in ("failed", "invalid", "denied", "rejected"):
        status = "failed"
    return [
        PlannedCallView(
            operation_id=plan.operation_id,
            method=plan.method,
            path=plan.path,
            parameters=plan.parameters,
            reason=plan.reason,
            expected_result=plan.expected_result,
            risk_level=plan.risk_level,
            confidence=plan.confidence,
            status=status,
            result=workflow.result if status == "completed" else None,
            error=workflow.error,
        )
    ]


def _chain_view(workflow: Workflow) -> list[PlannedCallView]:
    return [
        PlannedCallView(
            operation_id=step.operation_id,
            method=step.method,
            path=step.path,
            parameters=step.parameters,
            reason=step.reason,
            expected_result=step.expected_result,
            risk_level=step.risk_level,
            confidence=step.confidence,
            status=step.status,
            result=step.result,
            error=step.error,
        )
        for step in (workflow.chain or [])
    ]


def build_workflow_view(workflow: Workflow) -> WorkflowView:
    planned_calls = _chain_view(workflow) if workflow.chain is not None else _single_call_view(workflow)
    final_result = workflow.result if workflow.status == "completed" else None
    return WorkflowView(
        id=workflow.id,
        request=workflow.request,
        status=workflow.status,
        planned_calls=planned_calls,
        dry_run_preview=workflow.dry_run_preview,
        available_actions=_available_actions(workflow),
        final_result=final_result,
        error=workflow.error,
        steps=workflow.steps,
        created_at=workflow.created_at,
        updated_at=workflow.updated_at,
    )
