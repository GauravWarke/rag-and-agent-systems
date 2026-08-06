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
