"""Derives a normalized trace (an ordered timeline of spans) from an agent
task's step log — the Phase 5 "trace viewer" read-model.

This repo has no live billing or tracing backend (offline-runnable by
default), so `cost_usd` is a flat, documented per-risk-level stub estimate
rather than real provider pricing — directional, not exact.
"""
from __future__ import annotations

from app.core.models import AgentTask, DecisionLog, TraceResponse, TraceSpan

STUB_COST_PER_CALL_USD: dict[str, float] = {"low": 0.0005, "medium": 0.002, "high": 0.01}


def build_trace(task: AgentTask, decisions: list[DecisionLog]) -> TraceResponse:
    spans: list[TraceSpan] = []
    for index, step in enumerate(task.steps):
        latency_ms = None
        cost_usd = None
        if step.node == "tool_execution" and task.result is not None and task.result.tool_name in step.detail:
            latency_ms = task.result.latency_ms
            cost_usd = STUB_COST_PER_CALL_USD.get(task.result.risk_level)
        spans.append(
            TraceSpan(
                index=index,
                node=step.node,
                detail=step.detail,
                timestamp=step.timestamp,
                latency_ms=latency_ms,
                cost_usd=cost_usd,
            )
        )

    total_latency_ms = sum(s.latency_ms for s in spans if s.latency_ms is not None)
    total_cost_usd = sum(s.cost_usd for s in spans if s.cost_usd is not None)
    return TraceResponse(
        task_id=task.id,
        status=task.status,
        spans=spans,
        decisions=decisions,
        total_latency_ms=round(total_latency_ms, 2),
        total_cost_usd=round(total_cost_usd, 6),
    )
