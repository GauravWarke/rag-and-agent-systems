"""Permission checks: role gating plus risk-level execution rules.

Low-risk tools execute immediately once the role check passes. Medium-risk
tools need the caller to resubmit with `confirmed=true`. High-risk tools
always need a separate human approval step, regardless of `confirmed`.
"""
from __future__ import annotations

from app.core.models import PermissionStatus, ToolSpec, User


def check_permission(
    user: User, spec: ToolSpec, confirmed: bool, human_approved: bool = False
) -> PermissionStatus:
    if user.role not in spec.allowed_roles:
        return "denied"
    if spec.requires_approval and not human_approved:
        return "needs_approval"
    if spec.risk_level == "medium" and not confirmed:
        return "needs_confirmation"
    return "allowed"


def permission_message(status: PermissionStatus, spec: ToolSpec, role: str) -> str:
    if status == "denied":
        return f"Role '{role}' is not permitted to use '{spec.name}'."
    if status == "needs_confirmation":
        return f"'{spec.name}' is medium risk — resubmit the call with confirmed=true."
    if status == "needs_approval":
        return f"'{spec.name}' is high risk and requires human approval before it can run."
    return ""
