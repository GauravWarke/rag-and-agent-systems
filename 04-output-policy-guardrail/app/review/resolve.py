"""Turns an aggregated decision into the safe payload a caller actually
gets: the original output, a rewritten one, or nothing at all.
"""
from __future__ import annotations

from pydantic import BaseModel

from app.core.models import DecisionOutcome, Finding
from app.rewrite.block import build_block
from app.rewrite.rewrite import apply_rewrite


class ResolvedOutput(BaseModel):
    final_output: str | None
    reason_codes: list[str]


def resolve_output(
    output: str,
    decision: DecisionOutcome,
    findings: list[Finding],
    expected_schema: dict[str, str] | None,
) -> ResolvedOutput:
    if decision in ("approve", "approve_with_warning"):
        return ResolvedOutput(final_output=output, reason_codes=[])

    if decision == "rewrite":
        result = apply_rewrite(output, findings, expected_schema)
        return ResolvedOutput(final_output=result.text, reason_codes=result.applied_policy_ids)

    if decision == "block":
        block = build_block(findings)
        return ResolvedOutput(final_output=None, reason_codes=block.reason_codes)

    # human_review: nothing safe to show until a human decides.
    reason_codes = sorted({f.policy_id for f in findings if f.recommended_action == "human_review"})
    return ResolvedOutput(final_output=None, reason_codes=reason_codes)
