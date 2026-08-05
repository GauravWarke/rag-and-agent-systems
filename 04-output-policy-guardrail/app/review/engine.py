"""Orchestrates the review pipeline: cheap deterministic validators run
first; the LLM judge only runs for policies a deterministic check didn't
already resolve. Findings are then aggregated into one decision.
"""
from __future__ import annotations

import time
import uuid

from app.core.models import DecisionOutcome, Finding, ReviewRequest, ReviewResponse
from app.judge.review import PolicyJudge
from app.policies.store import PolicyStore
from app.validators.forbidden import ForbiddenTermsStore, check_forbidden
from app.validators.pii import build_pii_findings
from app.validators.schema import validate_schema

_DECISION_RANK: dict[DecisionOutcome, int] = {
    "approve": 0,
    "approve_with_warning": 1,
    "rewrite": 2,
    "block": 3,
    "human_review": 4,
}


class ReviewEngine:
    def __init__(self, policy_store: PolicyStore, forbidden_store: ForbiddenTermsStore, judge: PolicyJudge) -> None:
        self._policies = policy_store
        self._forbidden = forbidden_store
        self._judge = judge

    def review(self, req: ReviewRequest) -> ReviewResponse:
        start = time.perf_counter()
        findings: list[Finding] = []
        resolved_categories: set[str] = set()

        schema_policy = self._policies.get("schema_mismatch")
        if schema_policy is not None:
            finding = validate_schema(req.output, req.expected_schema, schema_policy)
            if finding is not None:
                findings.append(finding)
                resolved_categories.add(schema_policy.category)

        pii_policy = self._policies.get("pii_leakage")
        if pii_policy is not None:
            pii_findings = build_pii_findings(req.output, pii_policy, req.allowed_pii_types)
            findings.extend(pii_findings)
            if pii_findings:
                resolved_categories.add(pii_policy.category)

        already_handled = {p.id for p in (pii_policy, schema_policy) if p is not None}
        for policy in self._policies.by_strategy("deterministic"):
            if policy.id in already_handled:
                continue
            entry = self._forbidden.for_policy(policy.id)
            if entry is None:
                continue
            finding = check_forbidden(req.output, entry, policy)
            if finding is not None:
                findings.append(finding)
                resolved_categories.add(policy.category)

        findings.extend(self._judge.review(req.prompt, req.output, skip_categories=resolved_categories))

        decision = self._aggregate(findings)
        warnings = [f.message for f in findings if f.recommended_action == "approve_with_warning"]
        latency_ms = round((time.perf_counter() - start) * 1000, 4)
        return ReviewResponse(
            request_id=uuid.uuid4().hex,
            decision=decision,
            findings=findings,
            warnings=warnings,
            latency_ms=latency_ms,
        )

    @staticmethod
    def _aggregate(findings: list[Finding]) -> DecisionOutcome:
        if not findings:
            return "approve"
        return max((f.recommended_action for f in findings), key=lambda a: _DECISION_RANK[a])
