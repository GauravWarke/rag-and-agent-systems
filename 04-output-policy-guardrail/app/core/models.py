"""Request/response contracts for the policy guardrail review pipeline.

`ReviewRequest` is what every feature sends before showing an LLM output
to a user. `ReviewResponse` is the one shape every caller gets back,
carrying a single actionable `decision` plus the individual `findings`
that produced it, so the decision is always explainable.
"""
from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

Severity = Literal["low", "medium", "high", "critical"]
DecisionOutcome = Literal["approve", "approve_with_warning", "rewrite", "block", "human_review"]
Detector = Literal["deterministic", "llm_judge"]


class ReviewRequest(BaseModel):
    prompt: str = Field(min_length=1, max_length=8000)
    output: str = Field(min_length=1, max_length=8000)
    feature: str = Field(min_length=1, max_length=64)
    # Expected JSON shape for the output, as {field_name: type_name}. Omit
    # if the feature doesn't produce structured output.
    expected_schema: dict[str, str] | None = None
    # PII categories this feature explicitly allows (e.g. a feature that
    # legitimately echoes back an email address the user just typed).
    allowed_pii_types: list[str] = Field(default_factory=list, max_length=10)
    risk_tags: list[str] = Field(default_factory=list, max_length=10)


class Finding(BaseModel):
    policy_id: str
    category: str
    severity: Severity
    detector: Detector
    confidence: float = Field(ge=0.0, le=1.0)
    # Exact quoted span from `output` that triggered the finding, or ""
    # when no specific span applies (e.g. a missing required JSON field).
    evidence: str
    message: str
    recommended_action: DecisionOutcome


class ReviewResponse(BaseModel):
    request_id: str
    decision: DecisionOutcome
    findings: list[Finding] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    # The output to actually show the caller: the original output for
    # approve/approve_with_warning, the repaired/redacted text for
    # rewrite, or None for block/human_review (nothing safe to show yet).
    final_output: str | None = None
    # Policy ids behind a rewrite/block/human_review outcome. Stable
    # identifiers only — never the policy's internal description text.
    reason_codes: list[str] = Field(default_factory=list)
    latency_ms: float
