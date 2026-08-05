"""Runs the LLM judge across every applicable policy, with a second pass
and human-review escalation for high-risk findings.

Confidence and disagreement handling: a single judge call is trusted for
low/medium severity policies, but a lone high/critical-severity verdict
is not enough to block someone's output outright. For those, a second
independent pass runs; if the two passes disagree, the finding is
downgraded to `human_review` instead of pretending the guardrail is
certain.
"""
from __future__ import annotations

from app.core.models import Finding
from app.judge.client import JudgeClient, JudgeVerdict
from app.policies.store import Policy, PolicyStore

DUAL_PASS_SEVERITIES = {"high", "critical"}


class PolicyJudge:
    def __init__(self, policy_store: PolicyStore, client: JudgeClient) -> None:
        self._policies = policy_store
        self._client = client

    def review(self, prompt: str, output: str, skip_categories: set[str] | None = None) -> list[Finding]:
        """Judge `output` against every llm_judge/both policy.

        `skip_categories` lets the caller skip categories a deterministic
        validator already flagged, since a cheap check finding a clear
        violation makes the (slower, costlier) LLM judge redundant.
        """
        skip = skip_categories or set()
        findings: list[Finding] = []
        for policy in self._policies.by_strategy("llm_judge"):
            if policy.category in skip:
                continue
            findings.extend(self._review_policy(policy, prompt, output))
        return findings

    def _review_policy(self, policy: Policy, prompt: str, output: str) -> list[Finding]:
        first = self._client.review(policy, prompt, output)
        if not first.violation:
            return []

        if policy.severity not in DUAL_PASS_SEVERITIES:
            return [self._to_finding(policy, first)]

        second = self._client.review(policy, prompt, output)
        if second.violation != first.violation or second.severity != first.severity:
            return [self._disagreement_finding(policy, first, second)]
        return [self._to_finding(policy, first)]

    def _to_finding(self, policy: Policy, verdict: JudgeVerdict) -> Finding:
        return Finding(
            policy_id=policy.id,
            category=policy.category,
            severity=policy.severity,
            detector="llm_judge",
            confidence=verdict.confidence,
            evidence=verdict.evidence,
            message=verdict.rationale or f"LLM judge flagged a violation of '{policy.name}'.",
            recommended_action=policy.recommended_action,
        )

    def _disagreement_finding(self, policy: Policy, first: JudgeVerdict, second: JudgeVerdict) -> Finding:
        return Finding(
            policy_id=policy.id,
            category=policy.category,
            severity=policy.severity,
            detector="llm_judge",
            confidence=min(first.confidence, second.confidence),
            evidence=first.evidence or second.evidence,
            message=f"Judge passes disagreed on '{policy.name}'; routed to human review.",
            recommended_action="human_review",
        )
