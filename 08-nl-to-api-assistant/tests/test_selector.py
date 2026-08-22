from app.planning.models import EndpointSpec
from app.planning.selector import select_endpoints


def _endpoint(operation_id: str, summary: str, description: str = "") -> EndpointSpec:
    return EndpointSpec(
        operation_id=operation_id,
        method="GET",
        path=f"/biz/{operation_id}",
        summary=summary,
        description=description,
        parameters=[],
        risk_level="read_only",
        required_roles=["viewer"],
    )


_ENDPOINTS = [
    _endpoint("get_customer", "Get a customer by id", "Fetch one customer's profile."),
    _endpoint("issue_refund", "Issue a refund", "Issue a refund against an existing invoice."),
    _endpoint("create_ticket", "Create a support ticket", "Open a new support ticket for a customer."),
]


def test_select_endpoints_ranks_relevant_first():
    results = select_endpoints("please issue a refund for this invoice", _ENDPOINTS)
    assert results[0].operation_id == "issue_refund"


def test_select_endpoints_returns_empty_when_no_overlap():
    results = select_endpoints("xyz completely unrelated gibberish", _ENDPOINTS)
    assert results == []


def test_select_endpoints_respects_top_k():
    results = select_endpoints("customer refund ticket", _ENDPOINTS, top_k=1)
    assert len(results) == 1
