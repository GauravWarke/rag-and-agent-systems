from fastapi.testclient import TestClient

from app.main import app


def _client() -> TestClient:
    return TestClient(app)


def test_list_customers():
    with _client() as client:
        r = client.get("/biz/customers")
        assert r.status_code == 200
        assert len(r.json()) >= 3


def test_get_customer_found():
    with _client() as client:
        r = client.get("/biz/customers/cust_1")
        assert r.status_code == 200
        assert r.json()["email"] == "ana@example.com"


def test_get_customer_not_found():
    with _client() as client:
        r = client.get("/biz/customers/cust_999")
        assert r.status_code == 404


def test_find_customer_by_email():
    with _client() as client:
        r = client.get("/biz/customers", params={"email": "ben@example.com"})
        assert r.status_code == 200
        assert r.json()[0]["id"] == "cust_2"


def test_list_customer_subscriptions():
    with _client() as client:
        r = client.get("/biz/customers/cust_1/subscriptions")
        assert r.status_code == 200
        assert r.json()[0]["plan"] == "pro"


def test_list_customer_subscriptions_unknown_customer():
    with _client() as client:
        r = client.get("/biz/customers/cust_999/subscriptions")
        assert r.status_code == 404


def test_list_invoices_filtered():
    with _client() as client:
        r = client.get("/biz/invoices", params={"customer_id": "cust_2"})
        assert r.status_code == 200
        assert all(inv["customer_id"] == "cust_2" for inv in r.json())


def test_create_ticket():
    with _client() as client:
        r = client.post(
            "/biz/tickets",
            json={"customer_id": "cust_1", "subject": "Login issue", "description": "Cannot log in"},
        )
        assert r.status_code == 201
        assert r.json()["status"] == "open"


def test_create_ticket_unknown_customer():
    with _client() as client:
        r = client.post(
            "/biz/tickets",
            json={"customer_id": "cust_999", "subject": "x", "description": "y"},
        )
        assert r.status_code == 404


def test_update_subscription_plan():
    with _client() as client:
        r = client.patch("/biz/subscriptions/sub_2", json={"plan": "enterprise"})
        assert r.status_code == 200
        assert r.json()["plan"] == "enterprise"


def test_update_subscription_plan_unknown_subscription():
    with _client() as client:
        r = client.patch("/biz/subscriptions/sub_999", json={"plan": "pro"})
        assert r.status_code == 404


def test_issue_refund():
    with _client() as client:
        r = client.post(
            "/biz/refunds",
            json={"invoice_id": "inv_1", "amount_cents": 500, "reason": "duplicate charge"},
        )
        assert r.status_code == 201
        assert r.json()["status"] == "issued"


def test_issue_refund_exceeds_invoice_amount():
    with _client() as client:
        r = client.post(
            "/biz/refunds",
            json={"invoice_id": "inv_1", "amount_cents": 10_000_000, "reason": "too much"},
        )
        assert r.status_code == 400


def test_issue_refund_unknown_invoice():
    with _client() as client:
        r = client.post(
            "/biz/refunds",
            json={"invoice_id": "inv_999", "amount_cents": 100, "reason": "n/a"},
        )
        assert r.status_code == 404


def test_openapi_has_risk_metadata():
    with _client() as client:
        schema = client.get("/openapi.json").json()
        refund_op = schema["paths"]["/biz/refunds"]["post"]
        assert refund_op["x-risk-level"] == "high_risk_write"
        assert "admin" in refund_op["x-required-roles"]

        get_customer_op = schema["paths"]["/biz/customers/{customer_id}"]["get"]
        assert get_customer_op["x-risk-level"] == "read_only"

        ticket_op = schema["paths"]["/biz/tickets"]["post"]
        assert ticket_op["x-risk-level"] == "low_risk_write"
