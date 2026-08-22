"""Validates a proposed `CallPlan`'s parameters against the target
endpoint's JSON Schema before any API call is made — missing, unknown, or
mistyped fields are rejected here rather than reaching a tool handler.
"""
from __future__ import annotations

from typing import Any

from app.planning.models import (
    CallPlan,
    EndpointSpec,
    ValidationIssue,
    ValidationResult,
)

_TYPE_MAP: dict[str, type | tuple[type, ...]] = {
    "string": str,
    "integer": int,
    "number": (int, float),
    "boolean": bool,
}


def _matches_type(value: Any, expected_type: str) -> bool:
    py_type = _TYPE_MAP.get(expected_type)
    if py_type is None:
        return True
    if py_type is int and isinstance(value, bool):
        return False
    return isinstance(value, py_type)


def validate_call(plan: CallPlan, endpoint: EndpointSpec) -> ValidationResult:
    issues: list[ValidationIssue] = []
    filled: dict[str, Any] = {}
    known_names = {param.name for param in endpoint.parameters}

    for param in endpoint.parameters:
        value = plan.parameters.get(param.name)
        if value in (None, ""):
            if param.required:
                issues.append(ValidationIssue(field=param.name, message=f"Missing required field '{param.name}'."))
            continue

        expected_type = param.param_schema.get("type")
        if expected_type and not _matches_type(value, expected_type):
            issues.append(
                ValidationIssue(
                    field=param.name,
                    message=f"Field '{param.name}' expected type {expected_type}, got {type(value).__name__}.",
                )
            )
            continue

        enum_values = param.param_schema.get("enum")
        if enum_values and value not in enum_values:
            issues.append(
                ValidationIssue(
                    field=param.name, message=f"Field '{param.name}' must be one of {enum_values}, got {value!r}."
                )
            )
            continue

        filled[param.name] = value

    for key in plan.parameters:
        if key not in known_names:
            issues.append(ValidationIssue(field=key, message=f"Field '{key}' is not a recognized parameter for this endpoint."))

    return ValidationResult(valid=not issues, issues=issues, filled_parameters=filled)
