"""Structural validation: is the output valid JSON matching the shape a
feature expects? Bad format is the cheapest failure to catch and the
most commonly ignored one, so it runs before anything else.
"""
from __future__ import annotations

import json

from app.core.models import Finding
from app.policies.store import Policy

_TYPE_MAP: dict[str, type | tuple[type, ...]] = {
    "str": str,
    "int": int,
    "float": (int, float),
    "bool": bool,
    "list": list,
    "dict": dict,
}


def validate_schema(output: str, expected_schema: dict[str, str] | None, policy: Policy) -> Finding | None:
    """Check `output` against `expected_schema` ({field: type_name}).

    Returns a Finding describing the first structural problem found, or
    None if `expected_schema` wasn't provided or the output matches it.
    """
    if not expected_schema:
        return None

    try:
        data = json.loads(output)
    except json.JSONDecodeError as exc:
        return _finding(policy, f"Output is not valid JSON: {exc.msg}", output[:200])

    if not isinstance(data, dict):
        return _finding(policy, "Top-level JSON value must be an object", output[:200])

    missing = [field for field in expected_schema if field not in data]
    if missing:
        return _finding(policy, f"Missing required fields: {', '.join(sorted(missing))}", "")

    wrong_type = [
        field
        for field, type_name in expected_schema.items()
        if (py_type := _TYPE_MAP.get(type_name)) is not None and not isinstance(data[field], py_type)
    ]
    if wrong_type:
        return _finding(policy, f"Fields with wrong type: {', '.join(sorted(wrong_type))}", "")

    return None


def _finding(policy: Policy, message: str, evidence: str) -> Finding:
    return Finding(
        policy_id=policy.id,
        category=policy.category,
        severity=policy.severity,
        detector="deterministic",
        confidence=1.0,
        evidence=evidence,
        message=message,
        recommended_action=policy.recommended_action,
    )
