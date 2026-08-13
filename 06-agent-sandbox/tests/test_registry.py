from app.tools.registry import get_tool, list_tools


def test_lists_all_starter_tools():
    names = {spec.name for spec in list_tools()}
    assert names == {"calculator", "file_reader", "web_search", "csv_query", "ticket_create"}


def test_every_tool_has_a_risk_level_and_roles():
    for spec in list_tools():
        assert spec.risk_level in ("low", "medium", "high")
        assert spec.allowed_roles


def test_high_risk_tools_require_approval():
    for spec in list_tools():
        if spec.risk_level == "high":
            assert spec.requires_approval is True


def test_get_tool_unknown_returns_none():
    assert get_tool("does_not_exist") is None
