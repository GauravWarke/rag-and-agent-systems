from datetime import datetime, timezone

from app.agent.graph import run_task
from app.core.models import AgentTaskRequest
from app.observability.tracing import build_trace

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def test_trace_has_one_span_per_step_in_order():
    task = run_task(AgentTaskRequest(user_id="u_viewer", request="what is 2 + 2?"), now=_NOW)
    trace = build_trace(task, decisions=[])

    assert trace.task_id == task.id
    assert trace.status == "completed"
    assert [s.node for s in trace.spans] == [s.node for s in task.steps]
    assert [s.index for s in trace.spans] == list(range(len(task.steps)))


def test_trace_captures_latency_and_cost_for_tool_execution_step():
    task = run_task(AgentTaskRequest(user_id="u_viewer", request="what is 2 + 2?"), now=_NOW)
    trace = build_trace(task, decisions=[])

    exec_spans = [s for s in trace.spans if s.node == "tool_execution"]
    assert exec_spans
    assert exec_spans[0].latency_ms is not None
    assert exec_spans[0].cost_usd == 0.0005
    assert trace.total_latency_ms > 0
    assert trace.total_cost_usd == 0.0005


def test_trace_leaves_latency_and_cost_unset_for_non_tool_steps():
    task = run_task(AgentTaskRequest(user_id="u_viewer", request="what is 2 + 2?"), now=_NOW)
    trace = build_trace(task, decisions=[])

    intake_span = next(s for s in trace.spans if s.node == "intake")
    assert intake_span.latency_ms is None
    assert intake_span.cost_usd is None


def test_trace_includes_decisions_passed_in():
    task = run_task(AgentTaskRequest(user_id="u_viewer", request="what is 2 + 2?"), now=_NOW)
    trace = build_trace(task, decisions=[])
    assert trace.decisions == []
