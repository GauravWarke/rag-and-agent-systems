"""Structured audit logging for every assistant workflow event: the user
request, selected endpoints/parameters, validation result, approval status,
and final outcome. This is a server-side audit trail independent of what
the API returns to the caller — useful even if the in-memory workflow
store is later swapped out or wiped.
"""
from __future__ import annotations

import logging
from typing import Any

from app.planning.models import Workflow

logger = logging.getLogger("app.assistant.audit")


def _call_summary(workflow: Workflow) -> list[dict[str, Any]]:
    """One entry per proposed API call: which endpoint, with which
    parameters, and what happened to it. A single-call workflow has one
    entry; a chained workflow has one per step.
    """
    if workflow.chain is not None:
        return [
            {
                "segment": step.segment,
                "operation_id": step.operation_id,
                "parameters": step.parameters,
                "status": step.status,
                "error": step.error,
            }
            for step in workflow.chain
        ]
    if workflow.plan is None:
        return []
    return [
        {
            "segment": workflow.request,
            "operation_id": workflow.plan.operation_id,
            "parameters": workflow.plan.parameters,
            "status": workflow.status,
            "error": workflow.error,
        }
    ]


def log_workflow_event(event: str, workflow: Workflow) -> None:
    """Emit one structured audit record for a workflow create/resume event.

    Captures the user request, the selected endpoint(s) and parameters,
    the validation result, the approval status, the API response, and the
    final answer — everything an auditor would need to reconstruct what
    the assistant proposed and did, without depending on the in-memory
    workflow store still holding the record.
    """
    logger.info(
        "assistant_workflow",
        extra={
            "event": event,
            "workflow_id": workflow.id,
            "user_id": workflow.user_id,
            "request": workflow.request,
            "status": workflow.status,
            "calls": _call_summary(workflow),
            "validation_valid": workflow.validation.valid if workflow.validation else None,
            "result": workflow.result,
            "error": workflow.error,
        },
    )
