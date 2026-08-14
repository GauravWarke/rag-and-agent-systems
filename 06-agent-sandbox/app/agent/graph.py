"""The agent workflow: a small, explicit state machine (no external
orchestration service required, matching this repo's offline-runnable
convention) that "the model proposes, the system disposes" over.

Nodes: intake -> plan -> tool_selection -> permission_check ->
  (tool_execution | approval_wait) -> result_reflection -> final_response

If permission is denied the task ends immediately with a safe explanation.
If the tool is medium/high risk the task pauses (`awaiting_confirmation` /
`awaiting_approval`) with its pending action persisted so a human can
resume it later via `resume_task`. If the chosen tool fails and it has a
lower-risk `fallback_tool`, the workflow retries once with that tool
before giving up.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from app.core.models import (
    AgentStep,
    AgentTask,
    AgentTaskRequest,
    NodeName,
    PendingAction,
    ResumeTaskRequest,
    TaskStatus,
    ToolCallRequest,
    ToolCallResult,
    User,
)
from app.permissions.service import check_permission
from app.permissions.users import get_user
from app.tools.executor import execute_tool_call
from app.tools.registry import get_tool

from .planner import Planner, StubPlanner, ToolPlan

_default_planner = StubPlanner()


def _step(node: NodeName, detail: str, now: datetime) -> AgentStep:
    return AgentStep(node=node, detail=detail, timestamp=now)


def _format_final(result: ToolCallResult) -> str:
    if result.success:
        return f"Done — {result.tool_name} returned: {result.output}"
    return f"I couldn't complete this with {result.tool_name}: {result.error}"


def _build_fallback_arguments(fallback_tool_name: str, request: str, original_args: dict[str, Any]) -> dict[str, Any]:
    if fallback_tool_name == "web_search":
        seed = " ".join(str(v) for v in original_args.values()) or request
        return {"query": seed}
    return original_args


def _execute_with_fallback(
    user: User,
    tool_name: str,
    arguments: dict[str, Any],
    request: str,
    now: datetime,
    human_approved: bool = False,
) -> tuple[ToolCallResult, list[AgentStep]]:
    steps: list[AgentStep] = []
    result = execute_tool_call(
        ToolCallRequest(
            user_id=user.id,
            tool_name=tool_name,
            arguments=arguments,
            confirmed=True,
            human_approved=human_approved,
        )
    )
    steps.append(_step("tool_execution", f"Executed '{tool_name}': success={result.success}.", now))
    if result.success:
        return result, steps

    tool = get_tool(tool_name)
    fallback_name = tool.spec.fallback_tool if tool else None
    if not fallback_name:
        return result, steps

    fallback_tool = get_tool(fallback_name)
    if fallback_tool is None:
        return result, steps
    if check_permission(user, fallback_tool.spec, confirmed=True, human_approved=human_approved) != "allowed":
        return result, steps

    fallback_args = _build_fallback_arguments(fallback_name, request, arguments)
    steps.append(
        _step("tool_execution", f"'{tool_name}' failed — retrying with safer alternative '{fallback_name}'.", now)
    )
    fallback_result = execute_tool_call(
        ToolCallRequest(user_id=user.id, tool_name=fallback_name, arguments=fallback_args, confirmed=True)
    )
    steps.append(_step("tool_execution", f"Executed fallback '{fallback_name}': success={fallback_result.success}.", now))
    return fallback_result, steps


def _route_plan(
    user: User, request: str, plan: ToolPlan, steps: list[AgentStep], now: datetime
) -> tuple[TaskStatus, dict[str, Any]]:
    """Given a plan, select and permission-check its tool, then either
    execute it or pause for approval. Shared by `run_task` and the
    "replan" resume path, which both need to route a fresh `ToolPlan`
    through the same selection/permission/execution rules.
    """
    if plan.tool_name is None:
        steps.append(_step("final_response", "No tool matched this request.", now))
        return "failed", {"final_response": "I could not find a safe tool for that request. Try rephrasing."}

    tool = get_tool(plan.tool_name)
    if tool is None:
        steps.append(_step("final_response", f"Planned tool '{plan.tool_name}' is not registered.", now))
        return "failed", {"final_response": f"Planned tool '{plan.tool_name}' does not exist."}
    steps.append(_step("tool_selection", f"Selected tool '{plan.tool_name}'.", now))

    status = check_permission(user, tool.spec, confirmed=False)
    steps.append(_step("permission_check", f"Permission status: {status}.", now))

    if status == "denied":
        steps.append(_step("final_response", "Permission denied.", now))
        return "denied", {"final_response": f"Your role '{user.role}' cannot use '{plan.tool_name}'."}

    if status in ("needs_confirmation", "needs_approval"):
        wait_status = "awaiting_confirmation" if status == "needs_confirmation" else "awaiting_approval"
        steps.append(_step("approval_wait", f"Task paused: {wait_status}.", now))
        return wait_status, {
            "pending_action": PendingAction(
                tool_name=plan.tool_name, arguments=plan.arguments, risk_level=tool.spec.risk_level
            )
        }

    result, exec_steps = _execute_with_fallback(user, plan.tool_name, plan.arguments, request, now)
    steps.extend(exec_steps)
    final_response = _format_final(result)
    steps.append(_step("result_reflection", final_response, now))
    steps.append(_step("final_response", final_response, now))
    return ("completed" if result.success else "failed"), {"result": result, "final_response": final_response}


def run_task(
    req: AgentTaskRequest,
    now: datetime,
    planner: Planner | None = None,
    task_id: str | None = None,
) -> AgentTask:
    planner = planner or _default_planner
    task_id = task_id or str(uuid.uuid4())
    steps = [_step("intake", f"Received request from '{req.user_id}': {req.request!r}", now)]

    user = get_user(req.user_id)
    if user is None:
        steps.append(_step("final_response", "Unknown user; request denied.", now))
        return AgentTask(
            id=task_id,
            user_id=req.user_id,
            request=req.request,
            status="denied",
            steps=steps,
            final_response=f"Unknown user '{req.user_id}'.",
            created_at=now,
            updated_at=now,
        )

    plan: ToolPlan = planner.plan(req.request)
    steps.append(_step("plan", f"tool={plan.tool_name!r} confidence={plan.confidence} — {plan.reasoning}", now))

    status, extra = _route_plan(user, req.request, plan, steps, now)
    return AgentTask(
        id=task_id,
        user_id=req.user_id,
        request=req.request,
        status=status,
        steps=steps,
        created_at=now,
        updated_at=now,
        **extra,
    )


def resume_task(
    task: AgentTask, req: ResumeTaskRequest, now: datetime, planner: Planner | None = None
) -> AgentTask:
    """Apply a reviewer's decision to a paused task.

    - "reject" ends the task immediately with no side effects.
    - "approve" runs the pending action as originally proposed.
    - "modify" runs the pending action with `req.modified_arguments` in
      place of what the model proposed (validated by `ResumeTaskRequest`).
    - "replan" discards the pending action and asks the planner to propose
      a new one for the same request, which is then routed through
      selection/permission/execution again — it may complete, fail, or
      pause once more for a fresh approval.
    """
    if task.status not in ("awaiting_confirmation", "awaiting_approval"):
        raise ValueError(f"Task '{task.id}' is not waiting on a decision (status={task.status}).")
    if task.pending_action is None:
        raise ValueError(f"Task '{task.id}' has no pending action to resume.")

    steps = list(task.steps)
    steps.append(
        _step(
            "approval_wait",
            f"{req.reviewer} {req.decision}d the pending action. Reason: {req.reason}",
            now,
        )
    )

    if req.decision == "reject":
        steps.append(_step("final_response", "Action was rejected by a reviewer.", now))
        return task.model_copy(
            update={
                "status": "denied",
                "steps": steps,
                "final_response": f"Rejected by {req.reviewer}: {req.reason}",
                "pending_action": None,
                "updated_at": now,
            }
        )

    user = get_user(task.user_id)
    if user is None:
        raise ValueError(f"Unknown user '{task.user_id}'.")

    if req.decision == "replan":
        planner = planner or _default_planner
        new_plan = planner.plan(task.request)
        steps.append(
            _step("plan", f"tool={new_plan.tool_name!r} confidence={new_plan.confidence} — {new_plan.reasoning}", now)
        )
        status, extra = _route_plan(user, task.request, new_plan, steps, now)
        return task.model_copy(
            update={"status": status, "steps": steps, "pending_action": None, "updated_at": now, **extra}
        )

    arguments = req.modified_arguments if req.modified_arguments is not None else task.pending_action.arguments
    result, exec_steps = _execute_with_fallback(
        user, task.pending_action.tool_name, arguments, task.request, now, human_approved=True
    )
    steps.extend(exec_steps)
    final_response = _format_final(result)
    steps.append(_step("result_reflection", final_response, now))
    steps.append(_step("final_response", final_response, now))

    return task.model_copy(
        update={
            "status": "completed" if result.success else "failed",
            "steps": steps,
            "result": result,
            "final_response": final_response,
            "pending_action": None,
            "updated_at": now,
        }
    )
