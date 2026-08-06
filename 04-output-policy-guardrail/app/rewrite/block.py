"""Structured block responses for non-fixable policy violations.

A block never leaks a policy's internal description or examples — the
caller only gets a stable reason code (the policy id) and one generic
message, so a blocked response stays auditable without exposing rule
internals that could help someone probe around the guardrail.
"""
from __future__ import annotations

from pydantic import BaseModel

from app.core.models import Finding

BLOCK_MESSAGE = "This response was blocked because it did not meet content policy requirements."


class BlockResult(BaseModel):
    message: str
    reason_codes: list[str]


def build_block(findings: list[Finding]) -> BlockResult:
    reason_codes = sorted({f.policy_id for f in findings if f.recommended_action == "block"})
    return BlockResult(message=BLOCK_MESSAGE, reason_codes=reason_codes)
