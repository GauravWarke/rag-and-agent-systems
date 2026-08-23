"""Orchestrates one natural-language request end to end: parse the OpenAPI
schema, select candidate endpoints, propose a call plan, validate its
parameters, and either execute immediately (read-only), dry-run and pause
for confirmation (low-risk write), or dry-run and pause for human approval
(high-risk write).

A request that describes several actions ("find the customer, then open a
ticket") is split into a chain of steps by `app.planning.chain` and run one
at a time, threading each step's output into the next via typed workflow
state; execution still pauses for confirmation/approval at the first write
step and resumes from there.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from app.business_api import actions
from app.planning.chain import (
    carry_forward_parameters,
    extract_state_updates,
    plan_chain,
    split_chain_requests,
)
from app.planning.models import (
    CallPlan,
    ChainStepPlan,
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

    segments = split_chain_requests(req.request)
    if len(segments) > 1:
        chain = plan_chain(req.request, endpoints, _planner)
        steps.append(
            _step(
                "planning",
                f"Split into a {len(chain)}-step chain: {[c.operation_id for c in chain]}",
                now,
            )
        )
        return _run_chain(workflow_id, req, endpoints, chain, {}, 0, steps, now)

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


def _run_chain(
    workflow_id: str,
    req: CreateWorkflowRequest,
    endpoints: list[EndpointSpec],
    chain: list[ChainStepPlan],
    state: dict[str, Any],
    start_index: int,
    steps: list[WorkflowStep],
    now: datetime,
    resuming: bool = False,
) -> Workflow:
    """Execute chain steps in order starting at `start_index`. Pauses (and
    returns) the first time a write-risk step is reached that hasn't
    already been approved this call. `resuming=True` with `start_index`
    pointing at the step that was just approved skips that one step's gate
    and executes it directly, then keeps going.
    """
    endpoints_by_id = {e.operation_id: e for e in endpoints}

    for index in range(start_index, len(chain)):
        current = chain[index]

        if current.operation_id is None:
            current.status = "failed"
            current.error = "No endpoint matches this step confidently enough to propose a call."
            steps.append(_step("chain_step", f"Step {index + 1} ('{current.segment}'): {current.error}", now))
            return Workflow(
                id=workflow_id,
                user_id=req.user_id,
                request=req.request,
                status="denied",
                chain=chain,
                state=state,
                steps=steps,
                created_at=now,
                updated_at=now,
            )

        endpoint = endpoints_by_id[current.operation_id]
        parameters = carry_forward_parameters(current.parameters, endpoint, state)
        plan = CallPlan(
            operation_id=current.operation_id,
            method=current.method,
            path=current.path,
            parameters=parameters,
            reason=current.reason,
            expected_result=current.expected_result,
            requires_confirmation=endpoint.risk_level != "read_only",
            risk_level=endpoint.risk_level,
            confidence=current.confidence,
        )
        validation = validate_call(plan, endpoint)
        if not validation.valid:
            current.status = "failed"
            current.error = "; ".join(issue.message for issue in validation.issues)
            steps.append(
                _step("chain_step", f"Step {index + 1} ('{current.segment}'): invalid — {current.error}", now)
            )
            return Workflow(
                id=workflow_id,
                user_id=req.user_id,
                request=req.request,
                status="invalid",
                chain=chain,
                state=state,
                steps=steps,
                created_at=now,
                updated_at=now,
            )
        current.parameters = validation.filled_parameters

        already_approved = resuming and index == start_index
        if endpoint.risk_level != "read_only" and not already_approved:
            preview = _dry_run_preview(plan, endpoint)
            steps.append(_step("dry_run", f"Step {index + 1}: {preview}", now))
            status = "awaiting_approval" if endpoint.risk_level == "high_risk_write" else "awaiting_confirmation"
            steps.append(
                _step("approval_wait", f"Step {index + 1} ('{current.operation_id}') needs approval before executing.", now)
            )
            return Workflow(
                id=workflow_id,
                user_id=req.user_id,
                request=req.request,
                status=status,
                chain=chain,
                state=state,
                dry_run_preview=preview,
                steps=steps,
                created_at=now,
                updated_at=now,
            )

        result, error = _execute(current.operation_id, current.parameters)
        if error is not None:
            current.status = "failed"
            current.error = error
            steps.append(_step("chain_step", f"Step {index + 1} ('{current.operation_id}') failed: {error}", now))
            return Workflow(
                id=workflow_id,
                user_id=req.user_id,
                request=req.request,
                status="failed",
                chain=chain,
                state=state,
                error=error,
                steps=steps,
                created_at=now,
                updated_at=now,
            )

        current.status = "completed"
        current.result = result
        state_updates, clarification = extract_state_updates(current.operation_id, result)
        if clarification is not None:
            steps.append(_step("chain_step", f"Step {index + 1} ('{current.operation_id}'): {clarification}", now))
            return Workflow(
                id=workflow_id,
                user_id=req.user_id,
                request=req.request,
                status="needs_clarification",
                chain=chain,
                state=state,
                error=clarification,
                steps=steps,
                created_at=now,
                updated_at=now,
            )
        state.update(state_updates)
        steps.append(_step("chain_step", f"Step {index + 1} ('{current.operation_id}') completed.", now))

    steps.append(_step("final_response", "All chain steps completed.", now))
    return Workflow(
        id=workflow_id,
        user_id=req.user_id,
        request=req.request,
        status="completed",
        chain=chain,
        state=state,
        result=chain[-1].result if chain else None,
        steps=steps,
        created_at=now,
        updated_at=now,
    )


def resume_workflow(
    workflow: Workflow, req: ResumeWorkflowRequest, now: datetime, openapi_schema: dict[str, Any] | None = None
) -> Workflow:
    if workflow.status not in ("awaiting_confirmation", "awaiting_approval"):
        raise ValueError(f"Workflow '{workflow.id}' is not awaiting a decision (status='{workflow.status}').")

    steps = list(workflow.steps)

    if workflow.chain is not None:
        if req.decision == "reject":
            steps.append(_step("final_response", f"Rejected by {req.reviewer}: {req.reason}", now))
            return workflow.model_copy(update={"status": "rejected", "steps": steps, "updated_at": now})
        if openapi_schema is None:
            raise ValueError(f"Workflow '{workflow.id}' is a chain and needs the current OpenAPI schema to resume.")

        steps.append(_step("approval_decision", f"Approved by {req.reviewer} ({req.reason}).", now))
        endpoints = parse_openapi_schema(openapi_schema)
        chain = [step.model_copy() for step in workflow.chain]
        pending_index = next((i for i, step in enumerate(chain) if step.status == "pending"), None)
        if pending_index is None:
            raise ValueError(f"Workflow '{workflow.id}' has no pending chain step to resume.")
        fresh_req = CreateWorkflowRequest(user_id=workflow.user_id, request=workflow.request)
        return _run_chain(
            workflow.id, fresh_req, endpoints, chain, dict(workflow.state), pending_index, steps, now, resuming=True
        )

    if workflow.plan is None or workflow.plan.operation_id is None or workflow.validation is None:
        raise ValueError(f"Workflow '{workflow.id}' has no pending plan to resume.")

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
