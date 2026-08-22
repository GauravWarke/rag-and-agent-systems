"""Orchestrates one natural-language request end to end: parse the OpenAPI
schema, select candidate endpoints, propose a call plan, validate its
parameters, and either execute immediately (read-only), dry-run and pause
for confirmation (low-risk write), or dry-run and pause for human approval
(high-risk write).

Multi-step/chained calls are out of scope here — each workflow proposes
and (eventually) executes exactly one endpoint call.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from app.business_api import actions
from app.planning.models import (
    CallPlan,
    CreateWorkflowRequest,
    EndpointSpec,
    ResumeWorkflowRequest,
    ValidationResult,
    Workflow,
    WorkflowStep,
)
from app.planning.planner import StubPlanner
from app.planning.schema import parse_openapi_schema
from app.planning.selector import select_endpoints
from app.planning.validation import validate_call

_planner = StubPlanner()


def _step(node: str, detail: str, now: datetime) -> WorkflowStep:
    return WorkflowStep(node=node, detail=detail, timestamp=now)


def _dry_run_preview(plan: CallPlan, endpoint: EndpointSpec) -> str:
    params_desc = ", ".join(f"{k}={v!r}" for k, v in plan.parameters.items()) or "no parameters"
    return (
        f"DRY RUN: would call {plan.method} {plan.path} ({params_desc}). "
        f"No data has been changed yet. {plan.expected_result}"
    )


def _execute(operation_id: str, parameters: dict[str, Any]) -> tuple[Any, str | None]:
    try:
        return actions.execute(operation_id, parameters), None
    except ValueError as exc:
        return None, str(exc)


def create_workflow(req: CreateWorkflowRequest, openapi_schema: dict[str, Any], now: datetime) -> Workflow:
    workflow_id = str(uuid.uuid4())
    endpoints = parse_openapi_schema(openapi_schema)
    steps = [_step("intake", f"Received request: {req.request!r}", now)]

    candidates = select_endpoints(req.request, endpoints)
    steps.append(
        _step(
            "endpoint_selection",
            f"Selected {len(candidates)} candidate endpoint(s): {[c.operation_id for c in candidates]}",
            now,
        )
    )

    plan = _planner.plan(req.request, candidates)
    steps.append(_step("planning", plan.reason, now))

    if plan.operation_id is None:
        steps.append(_step("final_response", "No endpoint matches this request confidently enough to propose a call.", now))
        return Workflow(
            id=workflow_id,
            user_id=req.user_id,
            request=req.request,
            status="denied",
            plan=plan,
            steps=steps,
            created_at=now,
            updated_at=now,
        )

    endpoint = next(e for e in endpoints if e.operation_id == plan.operation_id)
    validation = validate_call(plan, endpoint)
    steps.append(
        _step(
            "validation",
            "All parameters valid." if validation.valid else "; ".join(i.message for i in validation.issues),
            now,
        )
    )

    if not validation.valid:
        steps.append(_step("final_response", "Could not build a valid call — see validation issues.", now))
        return Workflow(
            id=workflow_id,
            user_id=req.user_id,
            request=req.request,
            status="invalid",
            plan=plan,
            validation=validation,
            steps=steps,
            created_at=now,
            updated_at=now,
        )

    if endpoint.risk_level == "read_only":
        return _run_and_finalize(workflow_id, req, plan, validation, steps, now)

    preview = _dry_run_preview(plan, endpoint)
    steps.append(_step("dry_run", preview, now))

    if endpoint.risk_level == "high_risk_write":
        steps.append(_step("approval_wait", "High-risk write — waiting for human approval before executing.", now))
        status = "awaiting_approval"
    else:
        steps.append(_step("approval_wait", "Low-risk write — waiting for confirmation before executing.", now))
        status = "awaiting_confirmation"

    return Workflow(
        id=workflow_id,
        user_id=req.user_id,
        request=req.request,
        status=status,
        plan=plan,
        validation=validation,
        dry_run_preview=preview,
        steps=steps,
        created_at=now,
        updated_at=now,
    )


def _run_and_finalize(
    workflow_id: str,
    req: CreateWorkflowRequest,
    plan: CallPlan,
    validation: ValidationResult,
    steps: list[WorkflowStep],
    now: datetime,
) -> Workflow:
    result, error = _execute(plan.operation_id, validation.filled_parameters)
    if error is not None:
        steps.append(_step("execution", f"Execution failed: {error}", now))
        return Workflow(
            id=workflow_id,
            user_id=req.user_id,
            request=req.request,
            status="failed",
            plan=plan,
            validation=validation,
            error=error,
            steps=steps,
            created_at=now,
            updated_at=now,
        )
    steps.append(_step("execution", f"Executed {plan.operation_id} successfully.", now))
    steps.append(_step("final_response", "Request completed.", now))
    return Workflow(
        id=workflow_id,
        user_id=req.user_id,
        request=req.request,
        status="completed",
        plan=plan,
        validation=validation,
        result=result,
        steps=steps,
        created_at=now,
        updated_at=now,
    )


def resume_workflow(workflow: Workflow, req: ResumeWorkflowRequest, now: datetime) -> Workflow:
    if workflow.status not in ("awaiting_confirmation", "awaiting_approval"):
        raise ValueError(f"Workflow '{workflow.id}' is not awaiting a decision (status='{workflow.status}').")
    if workflow.plan is None or workflow.plan.operation_id is None or workflow.validation is None:
        raise ValueError(f"Workflow '{workflow.id}' has no pending plan to resume.")

    steps = list(workflow.steps)

    if req.decision == "reject":
        steps.append(_step("final_response", f"Rejected by {req.reviewer}: {req.reason}", now))
        return workflow.model_copy(update={"status": "rejected", "steps": steps, "updated_at": now})

    result, error = _execute(workflow.plan.operation_id, workflow.validation.filled_parameters)
    if error is not None:
        steps.append(_step("execution", f"Approved by {req.reviewer} ({req.reason}); execution failed: {error}", now))
        return workflow.model_copy(update={"status": "failed", "error": error, "steps": steps, "updated_at": now})

    steps.append(
        _step("execution", f"Approved by {req.reviewer} ({req.reason}); executed {workflow.plan.operation_id}.", now)
    )
    steps.append(_step("final_response", "Request completed.", now))
    return workflow.model_copy(update={"status": "completed", "result": result, "steps": steps, "updated_at": now})
