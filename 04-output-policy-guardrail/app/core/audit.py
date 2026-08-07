"""In-memory audit trail of every review decision.

Auditability is the point of a guardrail service: every decision
should be reconstructable later — what was reviewed, which policy
version made the call, what was found, and what a human reviewer later
did about it. In-memory for this demo; a production deployment would
back this with a table so the log survives restarts, but the query
surface (`pending_review`, `get`, `submit_review`) would stay the same.

The raw prompt/output are stored only as hashes so the audit trail
itself doesn't become a second place PII or sensitive content can leak
from. `final_output` is stored as-is because by the time a decision is
logged it has already been through rewrite/redaction, or withheld
entirely for block/human_review.
"""
from __future__ import annotations

import hashlib
from collections import Counter
from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

from app.core.models import DecisionOutcome, Finding

ReviewAction = Literal["approve", "reject", "approve_rewrite"]


def hash_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


class AuditLogEntry(BaseModel):
    request_id: str
    timestamp: datetime
    feature: str
    input_hash: str
    output_hash: str
    policy_version: str
    findings: list[Finding] = Field(default_factory=list)
    decision: DecisionOutcome
    latency_ms: float
    final_output: str | None = None
    reason_codes: list[str] = Field(default_factory=list)
    # Set once a human reviewer has looked at this entry (Phase 5 queue).
    reviewed: bool = False
    reviewer: str | None = None
    review_action: ReviewAction | None = None
    review_note: str | None = None


class ViolationCount(BaseModel):
    policy_id: str
    category: str
    count: int


class PolicyMetrics(BaseModel):
    total_reviewed: int
    block_rate: float
    rewrite_rate: float
    approve_rate: float
    human_review_rate: float
    avg_latency_ms: float
    # None until at least one flagged (block/human_review) decision has
    # been reviewed by a human — there's nothing to compute a rate from yet.
    false_positive_rate: float | None
    top_violations: list[ViolationCount]


class AuditLog:
    def __init__(self) -> None:
        self._entries: list[AuditLogEntry] = []

    def log(self, entry: AuditLogEntry) -> None:
        self._entries.append(entry)

    def all(self) -> list[AuditLogEntry]:
        return list(self._entries)

    def get(self, request_id: str) -> AuditLogEntry | None:
        return next((e for e in self._entries if e.request_id == request_id), None)

    def pending_review(self) -> list[AuditLogEntry]:
        """Entries a human still needs to look at: blocked or uncertain
        (human_review) decisions that haven't been reviewed yet."""
        return [e for e in self._entries if not e.reviewed and e.decision in ("block", "human_review")]

    def submit_review(
        self, request_id: str, reviewer: str, action: ReviewAction, note: str | None = None
    ) -> AuditLogEntry | None:
        entry = self.get(request_id)
        if entry is None:
            return None
        entry.reviewed = True
        entry.reviewer = reviewer
        entry.review_action = action
        entry.review_note = note
        return entry

    def metrics(self, top_n: int = 5) -> PolicyMetrics:
        """Aggregate policy performance across every logged decision.

        `false_positive_rate` is scoped to flagged (block/human_review)
        decisions a human has since reviewed: an `approve` review action
        on one of those means the guardrail flagged good output, i.e. a
        false positive. Unreviewed flagged decisions don't count either
        way yet.
        """
        total = len(self._entries)
        if total == 0:
            return PolicyMetrics(
                total_reviewed=0,
                block_rate=0.0,
                rewrite_rate=0.0,
                approve_rate=0.0,
                human_review_rate=0.0,
                avg_latency_ms=0.0,
                false_positive_rate=None,
                top_violations=[],
            )

        decision_counts = Counter(e.decision for e in self._entries)
        avg_latency_ms = sum(e.latency_ms for e in self._entries) / total

        reviewed_flagged = [
            e for e in self._entries if e.reviewed and e.decision in ("block", "human_review")
        ]
        false_positive_rate = (
            sum(1 for e in reviewed_flagged if e.review_action == "approve") / len(reviewed_flagged)
            if reviewed_flagged
            else None
        )

        violation_counts: Counter[tuple[str, str]] = Counter()
        for entry in self._entries:
            for finding in entry.findings:
                violation_counts[(finding.policy_id, finding.category)] += 1
        top_violations = [
            ViolationCount(policy_id=policy_id, category=category, count=count)
            for (policy_id, category), count in violation_counts.most_common(top_n)
        ]

        return PolicyMetrics(
            total_reviewed=total,
            block_rate=decision_counts.get("block", 0) / total,
            rewrite_rate=decision_counts.get("rewrite", 0) / total,
            approve_rate=(decision_counts.get("approve", 0) + decision_counts.get("approve_with_warning", 0))
            / total,
            human_review_rate=decision_counts.get("human_review", 0) / total,
            avg_latency_ms=round(avg_latency_ms, 4),
            false_positive_rate=false_positive_rate,
            top_violations=top_violations,
        )
