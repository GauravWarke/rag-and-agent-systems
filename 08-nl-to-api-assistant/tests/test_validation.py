from app.planning.models import CallPlan, EndpointParam, EndpointSpec
from app.planning.validation import validate_call

_TICKET_ENDPOINT = EndpointSpec(
    operation_id="create_ticket",
    method="POST",
    path="/biz/tickets",
    summary="Create a support ticket",
    description="",
    parameters=[
        EndpointParam(name="customer_id", location="body", required=True, param_schema={"type": "string"}),
        EndpointParam(name="subject", location="body", required=True, param_schema={"type": "string"}),
        EndpointParam(name="description", location="body", required=True, param_schema={"type": "string"}),
    ],
    risk_level="low_risk_write",
    required_roles=["analyst", "operator", "admin"],
)


def _ticket_plan(parameters: dict) -> CallPlan:
    return CallPlan(
        operation_id="create_ticket",
        method="POST",
        path="/biz/tickets",
        parameters=parameters,
        reason="test",
        expected_result="test",
        requires_confirmation=True,
        risk_level="low_risk_write",
    )


def test_validate_call_valid():
    result = validate_call(
        _ticket_plan({"customer_id": "cust_1", "subject": "Login issue", "description": "Can't log in"}),
        _TICKET_ENDPOINT,
    )
    assert result.valid
    assert result.filled_parameters["customer_id"] == "cust_1"


def test_validate_call_missing_required_field():
    result = validate_call(_ticket_plan({"subject": "Login issue"}), _TICKET_ENDPOINT)
    assert not result.valid
    fields = {issue.field for issue in result.issues}
    assert "customer_id" in fields
    assert "description" in fields


def test_validate_call_rejects_unknown_field():
    result = validate_call(
        _ticket_plan({"customer_id": "cust_1", "subject": "x", "description": "y", "mystery": "z"}),
        _TICKET_ENDPOINT,
    )
    assert not result.valid
    assert any(issue.field == "mystery" for issue in result.issues)


def test_validate_call_wrong_type():
    endpoint = EndpointSpec(
        operation_id="issue_refund",
        method="POST",
        path="/biz/refunds",
        summary="",
        description="",
        parameters=[
            EndpointParam(name="amount_cents", location="body", required=True, param_schema={"type": "integer"}),
        ],
        risk_level="high_risk_write",
        required_roles=["admin"],
    )
    plan = CallPlan(
        operation_id="issue_refund",
        method="POST",
        path="/biz/refunds",
        parameters={"amount_cents": "not-a-number"},
        reason="test",
        expected_result="test",
        requires_confirmation=True,
        risk_level="high_risk_write",
    )
    result = validate_call(plan, endpoint)
    assert not result.valid


def test_validate_call_rejects_invalid_enum_value():
    endpoint = EndpointSpec(
        operation_id="update_subscription_plan",
        method="PATCH",
        path="/biz/subscriptions/{subscription_id}",
        summary="",
        description="",
        parameters=[
            EndpointParam(name="subscription_id", location="path", required=True, param_schema={"type": "string"}),
            EndpointParam(
                name="plan",
                location="body",
                required=True,
                param_schema={"type": "string", "enum": ["basic", "pro", "enterprise"]},
            ),
        ],
        risk_level="high_risk_write",
        required_roles=["operator", "admin"],
    )
    plan = CallPlan(
        operation_id="update_subscription_plan",
        method="PATCH",
        path="/biz/subscriptions/{subscription_id}",
        parameters={"subscription_id": "sub_1", "plan": "ultra"},
        reason="test",
        expected_result="test",
        requires_confirmation=True,
        risk_level="high_risk_write",
    )
    result = validate_call(plan, endpoint)
    assert not result.valid
    assert any(issue.field == "plan" for issue in result.issues)
