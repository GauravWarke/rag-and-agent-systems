from app.main import app
from app.planning.schema import parse_openapi_schema


def test_parse_openapi_schema_extracts_read_only_endpoint():
    endpoints = parse_openapi_schema(app.openapi())
    by_id = {e.operation_id: e for e in endpoints}

    get_customer = by_id["get_customer"]
    assert get_customer.method == "GET"
    assert get_customer.risk_level == "read_only"
    assert any(p.name == "customer_id" and p.required for p in get_customer.parameters)


def test_parse_openapi_schema_extracts_low_risk_write_endpoint():
    endpoints = parse_openapi_schema(app.openapi())
    by_id = {e.operation_id: e for e in endpoints}

    create_ticket = by_id["create_ticket"]
    assert create_ticket.method == "POST"
    assert create_ticket.risk_level == "low_risk_write"
    param_names = {p.name for p in create_ticket.parameters}
    assert {"customer_id", "subject", "description"} <= param_names


def test_parse_openapi_schema_extracts_high_risk_write_endpoint_with_roles():
    endpoints = parse_openapi_schema(app.openapi())
    by_id = {e.operation_id: e for e in endpoints}

    issue_refund = by_id["issue_refund"]
    assert issue_refund.method == "POST"
    assert issue_refund.risk_level == "high_risk_write"
    assert "admin" in issue_refund.required_roles
    param_names = {p.name for p in issue_refund.parameters}
    assert {"invoice_id", "amount_cents", "reason"} <= param_names


def test_parse_openapi_schema_covers_every_business_endpoint():
    endpoints = parse_openapi_schema(app.openapi())
    operation_ids = {e.operation_id for e in endpoints}
    assert {
        "list_customers",
        "get_customer",
        "list_customer_subscriptions",
        "list_invoices",
        "create_ticket",
        "update_subscription_plan",
        "issue_refund",
    } <= operation_ids
