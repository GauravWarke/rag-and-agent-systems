from app.main import app
from app.planning.planner import StubPlanner
from app.planning.schema import parse_openapi_schema

_ENDPOINTS = parse_openapi_schema(app.openapi())
_PLANNER = StubPlanner()


def test_planner_plans_refund():
    plan = _PLANNER.plan("please issue a refund of $10 for inv_2, duplicate charge", _ENDPOINTS)
    assert plan.operation_id == "issue_refund"
    assert plan.parameters["invoice_id"] == "inv_2"
    assert plan.parameters["amount_cents"] == 1000
    assert plan.risk_level == "high_risk_write"


def test_planner_plans_create_ticket():
    plan = _PLANNER.plan("open a ticket for cust_1, they can't reset their password", _ENDPOINTS)
    assert plan.operation_id == "create_ticket"
    assert plan.parameters["customer_id"] == "cust_1"
    assert plan.risk_level == "low_risk_write"


def test_planner_plans_update_subscription_plan():
    plan = _PLANNER.plan("upgrade sub_2 to the enterprise plan", _ENDPOINTS)
    assert plan.operation_id == "update_subscription_plan"
    assert plan.parameters["subscription_id"] == "sub_2"
    assert plan.parameters["plan"] == "enterprise"


def test_planner_plans_get_customer_by_email():
    plan = _PLANNER.plan("look up the customer with email ana@example.com", _ENDPOINTS)
    assert plan.operation_id == "list_customers"
    assert plan.parameters["email"] == "ana@example.com"


def test_planner_returns_none_when_no_candidates():
    plan = _PLANNER.plan("asdkjhaskjdh qweoiuqwoeiu", [])
    assert plan.operation_id is None
    assert plan.confidence == 0.0


def test_planner_flags_low_confidence_fallback():
    plan = _PLANNER.plan("do something with this thing", _ENDPOINTS[:1])
    assert plan.operation_id == _ENDPOINTS[0].operation_id
    assert plan.confidence < 0.5
