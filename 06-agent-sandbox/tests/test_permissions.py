from app.core.models import ToolSpec, User
from app.permissions.service import check_permission, permission_message

_LOW = ToolSpec(
    name="low_tool",
    description="d",
    input_schema={},
    output_schema={},
    allowed_roles=["analyst", "operator", "admin"],
    rate_limit_per_minute=60,
    risk_level="low",
)
_MEDIUM = _LOW.model_copy(update={"name": "medium_tool", "risk_level": "medium"})
_HIGH = _LOW.model_copy(update={"name": "high_tool", "risk_level": "high", "requires_approval": True})

_viewer = User(id="u_viewer", role="viewer")
_analyst = User(id="u_analyst", role="analyst")


def test_role_not_allowed_is_denied():
    assert check_permission(_viewer, _LOW, confirmed=False) == "denied"


def test_low_risk_allowed_immediately():
    assert check_permission(_analyst, _LOW, confirmed=False) == "allowed"


def test_medium_risk_needs_confirmation_until_confirmed():
    assert check_permission(_analyst, _MEDIUM, confirmed=False) == "needs_confirmation"
    assert check_permission(_analyst, _MEDIUM, confirmed=True) == "allowed"


def test_high_risk_always_needs_approval_even_if_confirmed():
    assert check_permission(_analyst, _HIGH, confirmed=True) == "needs_approval"


def test_high_risk_allowed_once_human_approved():
    assert check_permission(_analyst, _HIGH, confirmed=True, human_approved=True) == "allowed"


def test_permission_message_is_nonempty_for_each_blocking_status():
    for status, spec in (("denied", _LOW), ("needs_confirmation", _MEDIUM), ("needs_approval", _HIGH)):
        assert permission_message(status, spec, "viewer")
