"""Ties the registry, permission checks, and Pydantic argument validation
together into one entry point: raw model/user text never reaches a tool
handler without going through all three first.
"""
from __future__ import annotations

import time

from pydantic import ValidationError

from app.core.models import ToolCallRequest, ToolCallResult
from app.permissions.service import check_permission, permission_message
from app.permissions.users import get_user
from app.tools.registry import get_tool


def execute_tool_call(req: ToolCallRequest) -> ToolCallResult:
    user = get_user(req.user_id)
    if user is None:
        return ToolCallResult(
            tool_name=req.tool_name,
            permission_status="denied",
            success=False,
            error=f"Unknown user '{req.user_id}'.",
            risk_level="low",
        )

    tool = get_tool(req.tool_name)
    if tool is None:
        return ToolCallResult(
            tool_name=req.tool_name,
            permission_status="denied",
            success=False,
            error=f"Unknown tool '{req.tool_name}'.",
            risk_level="low",
        )

    status = check_permission(user, tool.spec, req.confirmed, req.human_approved)
    if status != "allowed":
        return ToolCallResult(
            tool_name=req.tool_name,
            permission_status=status,
            success=False,
            error=permission_message(status, tool.spec, user.role),
            risk_level=tool.spec.risk_level,
        )

    start = time.perf_counter()
    try:
        parsed_args = tool.args_model(**req.arguments)
    except ValidationError as exc:
        return ToolCallResult(
            tool_name=req.tool_name,
            permission_status="invalid_input",
            success=False,
            error=str(exc),
            risk_level=tool.spec.risk_level,
            latency_ms=round((time.perf_counter() - start) * 1000, 2),
        )

    try:
        output = tool.handler(parsed_args)
    except ValueError as exc:
        return ToolCallResult(
            tool_name=req.tool_name,
            permission_status="allowed",
            success=False,
            error=str(exc),
            risk_level=tool.spec.risk_level,
            latency_ms=round((time.perf_counter() - start) * 1000, 2),
        )

    return ToolCallResult(
        tool_name=req.tool_name,
        permission_status="allowed",
        success=True,
        output=output,
        risk_level=tool.spec.risk_level,
        latency_ms=round((time.perf_counter() - start) * 1000, 2),
    )
