from app.core.models import ToolCallRequest
from app.tools.executor import execute_tool_call


def test_unknown_user_is_denied():
    result = execute_tool_call(ToolCallRequest(user_id="nope", tool_name="calculator", arguments={}))
    assert result.permission_status == "denied"
    assert result.success is False


def test_unknown_tool_is_denied():
    result = execute_tool_call(ToolCallRequest(user_id="u_admin", tool_name="nope", arguments={}))
    assert result.permission_status == "denied"


def test_role_without_access_is_denied():
    result = execute_tool_call(
        ToolCallRequest(user_id="u_viewer", tool_name="file_reader", arguments={"path": "welcome.txt"})
    )
    assert result.permission_status == "denied"


def test_low_risk_tool_executes_immediately():
    result = execute_tool_call(
        ToolCallRequest(user_id="u_viewer", tool_name="calculator", arguments={"expression": "1 + 1"})
    )
    assert result.permission_status == "allowed"
    assert result.success is True
    assert result.output["result"] == 2


def test_medium_risk_tool_needs_confirmation_first():
    result = execute_tool_call(
        ToolCallRequest(user_id="u_analyst", tool_name="csv_query", arguments={"column": "plan", "value": "pro"})
    )
    assert result.permission_status == "needs_confirmation"
    assert result.success is False


def test_medium_risk_tool_executes_once_confirmed():
    result = execute_tool_call(
        ToolCallRequest(
            user_id="u_analyst",
            tool_name="csv_query",
            arguments={"column": "plan", "value": "pro"},
            confirmed=True,
        )
    )
    assert result.permission_status == "allowed"
    assert result.success is True


def test_high_risk_tool_always_needs_approval():
    result = execute_tool_call(
        ToolCallRequest(
            user_id="u_operator",
            tool_name="ticket_create",
            arguments={"title": "t", "description": "d"},
            confirmed=True,
        )
    )
    assert result.permission_status == "needs_approval"
    assert result.success is False


def test_high_risk_tool_executes_once_human_approved():
    result = execute_tool_call(
        ToolCallRequest(
            user_id="u_operator",
            tool_name="ticket_create",
            arguments={"title": "t", "description": "d"},
            confirmed=True,
            human_approved=True,
        )
    )
    assert result.permission_status == "allowed"
    assert result.success is True


def test_invalid_arguments_are_rejected_before_execution():
    result = execute_tool_call(
        ToolCallRequest(user_id="u_viewer", tool_name="calculator", arguments={"not_expression": "1+1"})
    )
    assert result.permission_status == "invalid_input"
    assert result.success is False


def test_handler_error_surfaces_as_failed_but_allowed():
    result = execute_tool_call(
        ToolCallRequest(user_id="u_viewer", tool_name="calculator", arguments={"expression": "1/0"})
    )
    assert result.permission_status == "allowed"
    assert result.success is False
    assert result.error
