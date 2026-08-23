from app.planning.chain import (
    carry_forward_parameters,
    extract_state_updates,
    plan_chain,
    split_chain_requests,
)
from app.planning.models import EndpointParam, EndpointSpec
from app.planning.planner import StubPlanner


def test_split_chain_requests_single_clause_unchanged():
    assert split_chain_requests("get customer cust_1") == ["get customer cust_1"]


def test_split_chain_requests_splits_on_then():
    segments = split_chain_requests("find the customer, then open a ticket")
    assert segments == ["find the customer", "open a ticket"]


def test_split_chain_requests_splits_commas_within_a_then_group():
    request = "find customer by email ana@example.com, fetch her subscription, check invoice status, then create a support ticket"
    segments = split_chain_requests(request)
    assert segments == [
        "find customer by email ana@example.com",
        "fetch her subscription",
        "check invoice status",
        "create a support ticket",
    ]


def test_split_chain_requests_handles_and_then():
    segments = split_chain_requests("look up cust_1 and then open a ticket")
    assert segments == ["look up cust_1", "open a ticket"]


def _endpoint(operation_id: str, param_names: list[str]) -> EndpointSpec:
    return EndpointSpec(
        operation_id=operation_id,
        method="GET",
        path=f"/{operation_id}",
        summary="",
        description="",
        parameters=[EndpointParam(name=name, location="path", required=True) for name in param_names],
        risk_level="read_only",
    )


def test_carry_forward_parameters_fills_missing_known_param():
    endpoint = _endpoint("list_customer_subscriptions", ["customer_id"])
    filled = carry_forward_parameters({}, endpoint, {"customer_id": "cust_1"})
    assert filled == {"customer_id": "cust_1"}


def test_carry_forward_parameters_does_not_override_explicit_value():
    endpoint = _endpoint("list_customer_subscriptions", ["customer_id"])
    filled = carry_forward_parameters({"customer_id": "cust_2"}, endpoint, {"customer_id": "cust_1"})
    assert filled == {"customer_id": "cust_2"}


def test_carry_forward_parameters_ignores_unrelated_state():
    endpoint = _endpoint("list_customer_subscriptions", ["customer_id"])
    filled = carry_forward_parameters({}, endpoint, {"invoice_id": "inv_1"})
    assert filled == {}


def test_extract_state_updates_single_item_list():
    updates, clarification = extract_state_updates("list_customers", [{"id": "cust_1", "name": "Ana"}])
    assert clarification is None
    assert updates == {"customer_id": "cust_1", "customer": {"id": "cust_1", "name": "Ana"}}


def test_extract_state_updates_empty_list_is_noop():
    updates, clarification = extract_state_updates("list_customers", [])
    assert updates == {}
    assert clarification is None


def test_extract_state_updates_multiple_matches_asks_for_clarification():
    updates, clarification = extract_state_updates(
        "list_invoices", [{"id": "inv_1"}, {"id": "inv_2"}]
    )
    assert updates == {}
    assert clarification is not None
    assert "inv_1" in clarification and "inv_2" in clarification


def test_extract_state_updates_unmapped_operation_is_noop():
    updates, clarification = extract_state_updates("list_invoices_unmapped_op", {"id": "x"})
    assert updates == {}
    assert clarification is None


def test_plan_chain_produces_one_step_per_clause():
    endpoints = [
        _endpoint("list_customers", ["email"]),
        _endpoint("create_ticket", ["customer_id", "subject", "description"]),
    ]
    steps = plan_chain(
        "find customer by email ana@example.com, then create a ticket", endpoints, StubPlanner()
    )
    assert len(steps) == 2
    assert steps[0].segment == "find customer by email ana@example.com"
    assert steps[1].segment == "create a ticket"
