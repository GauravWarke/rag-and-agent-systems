"""Release gate thresholds (Phase 3, step 4): turn a `ComparisonReport`
into a block / warn / pass decision with explicit reasons.
"""
from __future__ import annotations

from enum import Enum

from pydantic import BaseModel

from app.core.config import settings
from app.eval.comparison import ComparisonReport


class GateDecision(str, Enum):
    pass_ = "pass"
    warn = "warn"
    block = "block"


class GateResult(BaseModel):
    decision: GateDecision
    reasons: list[str]


def evaluate_gate(
    report: ComparisonReport,
    schema_validity_drop_block_pct: float | None = None,
    cost_increase_block_pct: float | None = None,
    latency_increase_warn_pct: float | None = None,
) -> GateResult:
    schema_drop_limit = (
        settings.schema_validity_drop_block_pct
        if schema_validity_drop_block_pct is None
        else schema_validity_drop_block_pct
    )
    cost_limit = settings.cost_increase_block_pct if cost_increase_block_pct is None else cost_increase_block_pct
    latency_limit = (
        settings.latency_increase_warn_pct if latency_increase_warn_pct is None else latency_increase_warn_pct
    )

    block_reasons: list[str] = []
    warn_reasons: list[str] = []

    schema_drop = report.baseline.schema_validity_pct - report.candidate.schema_validity_pct
    if schema_drop > schema_drop_limit:
        block_reasons.append(
            f"schema validity dropped {schema_drop:.2f} points "
            f"({report.baseline.schema_validity_pct:.2f}% -> {report.candidate.schema_validity_pct:.2f}%), "
            f"exceeding the {schema_drop_limit:.2f}-point block threshold"
        )

    if report.safety_failure_delta > 0:
        block_reasons.append(
            f"safety failures increased by {report.safety_failure_delta} case(s) "
            f"({report.baseline.safety_failure_count} -> {report.candidate.safety_failure_count})"
        )

    if report.cost_delta_pct > cost_limit:
        block_reasons.append(
            f"average cost rose {report.cost_delta_pct:.2f}%, exceeding the {cost_limit:.2f}% block threshold"
        )

    if not block_reasons:
        if report.latency_delta_pct > latency_limit:
            warn_reasons.append(
                f"average latency rose {report.latency_delta_pct:.2f}%, "
                f"exceeding the {latency_limit:.2f}% warn threshold"
            )
        if report.regressed_categories:
            warn_reasons.append(f"categories regressed: {', '.join(report.regressed_categories)}")
        if report.newly_failing:
            warn_reasons.append(f"{len(report.newly_failing)} case(s) newly failing: {', '.join(report.newly_failing)}")

    if block_reasons:
        return GateResult(decision=GateDecision.block, reasons=block_reasons)
    if warn_reasons:
        return GateResult(decision=GateDecision.warn, reasons=warn_reasons)
    return GateResult(decision=GateDecision.pass_, reasons=["no regressions detected"])
