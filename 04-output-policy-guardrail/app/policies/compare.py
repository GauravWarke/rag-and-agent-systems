"""Policy-version comparison: replays a caller-supplied set of example
prompt/output pairs against the live policy set and a candidate policy
set, side by side, so a policy author can see how a proposed edit would
have changed real decisions before it ships.

Examples are supplied by the caller rather than pulled from the audit
log, because the audit log only stores prompt/output hashes (see
`app/core/audit.py`) — replaying a comparison never needs, and must
never require, un-hashing logged content.

Each comparison runs through the same `ReviewEngine` pipeline used in
production, but against a throwaway `AuditLog`, so replaying examples
never pollutes the real audit trail.
"""
from __future__ import annotations

from pydantic import BaseModel, Field

from app.core.audit import AuditLog
from app.core.models import DecisionOutcome, ReviewRequest
from app.judge.client import JudgeClient
from app.judge.review import PolicyJudge
from app.policies.store import PolicyStore
from app.review.engine import ReviewEngine
from app.validators.forbidden import ForbiddenTermsStore


class ComparisonExample(BaseModel):
    label: str = Field(min_length=1, max_length=64)
    prompt: str = Field(min_length=1, max_length=8000)
    output: str = Field(min_length=1, max_length=8000)
    feature: str = Field(min_length=1, max_length=64)
    expected_schema: dict[str, str] | None = None
    allowed_pii_types: list[str] = Field(default_factory=list, max_length=10)


class PolicyComparisonRequest(BaseModel):
    # Full candidate policy YAML, in the same shape as data/policies.yaml.
    policies_yaml: str = Field(min_length=1, max_length=20_000)
    examples: list[ComparisonExample] = Field(min_length=1, max_length=50)


class ExampleDiff(BaseModel):
    label: str
    baseline_decision: DecisionOutcome
    candidate_decision: DecisionOutcome
    changed: bool
    added_policy_ids: list[str]
    removed_policy_ids: list[str]


class PolicyComparisonResult(BaseModel):
    baseline_version: str
    candidate_version: str
    total_examples: int
    changed_count: int
    diffs: list[ExampleDiff]


def compare_policy_versions(
    examples: list[ComparisonExample],
    baseline_store: PolicyStore,
    candidate_store: PolicyStore,
    forbidden_store: ForbiddenTermsStore,
    judge_client: JudgeClient,
) -> PolicyComparisonResult:
    baseline_engine = ReviewEngine(
        baseline_store, forbidden_store, PolicyJudge(baseline_store, judge_client), AuditLog()
    )
    candidate_engine = ReviewEngine(
        candidate_store, forbidden_store, PolicyJudge(candidate_store, judge_client), AuditLog()
    )

    diffs: list[ExampleDiff] = []
    for example in examples:
        req = ReviewRequest(
            prompt=example.prompt,
            output=example.output,
            feature=example.feature,
            expected_schema=example.expected_schema,
            allowed_pii_types=example.allowed_pii_types,
        )
        baseline_resp = baseline_engine.review(req)
        candidate_resp = candidate_engine.review(req)
        baseline_ids = {f.policy_id for f in baseline_resp.findings}
        candidate_ids = {f.policy_id for f in candidate_resp.findings}
        diffs.append(
            ExampleDiff(
                label=example.label,
                baseline_decision=baseline_resp.decision,
                candidate_decision=candidate_resp.decision,
                changed=baseline_resp.decision != candidate_resp.decision,
                added_policy_ids=sorted(candidate_ids - baseline_ids),
                removed_policy_ids=sorted(baseline_ids - candidate_ids),
            )
        )

    return PolicyComparisonResult(
        baseline_version=baseline_store.version,
        candidate_version=candidate_store.version,
        total_examples=len(examples),
        changed_count=sum(1 for d in diffs if d.changed),
        diffs=diffs,
    )
