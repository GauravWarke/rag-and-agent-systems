from app.agent.planner import StubPlanner

_planner = StubPlanner()


def test_plans_calculator_for_arithmetic():
    plan = _planner.plan("what is 4 * 5?")
    assert plan.tool_name == "calculator"
    assert "4" in plan.arguments["expression"]


def test_plans_file_reader_for_read_file_request():
    plan = _planner.plan("please read file welcome.txt")
    assert plan.tool_name == "file_reader"
    assert plan.arguments["path"] == "welcome.txt"


def test_plans_web_search_for_lookup_request():
    plan = _planner.plan("search for the refund policy")
    assert plan.tool_name == "web_search"
    assert plan.arguments["query"]


def test_plans_csv_query_for_customer_lookup():
    plan = _planner.plan("find customers where plan is pro")
    assert plan.tool_name == "csv_query"
    assert plan.arguments == {"column": "plan", "value": "pro"}


def test_plans_ticket_create_for_ticket_request():
    plan = _planner.plan("create a ticket for a broken login")
    assert plan.tool_name == "ticket_create"
    assert plan.arguments["description"]


def test_no_plan_for_unrelated_request():
    plan = _planner.plan("tell me a joke")
    assert plan.tool_name is None
    assert plan.confidence == 0.0
