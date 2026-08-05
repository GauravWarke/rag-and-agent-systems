"""Forbidden content checks: regex/keyword rules for obvious policy
violations. These are cheap and deterministic, so they run before the
LLM judge and can short-circuit it entirely for clear-cut cases.
"""
from __future__ import annotations

import re
from pathlib import Path

import yaml
from pydantic import BaseModel

from app.core.models import Finding
from app.policies.store import Policy


class ForbiddenEntry(BaseModel):
    policy_id: str
    keywords: list[str] = []
    regexes: list[str] = []


class ForbiddenTermsStore:
    def __init__(self, entries: list[ForbiddenEntry]) -> None:
        self._entries = entries

    @classmethod
    def load(cls, path: str | Path) -> ForbiddenTermsStore:
        data = yaml.safe_load(Path(path).read_text()) or {}
        entries = [ForbiddenEntry.model_validate(e) for e in data.get("entries", [])]
        return cls(entries)

    def for_policy(self, policy_id: str) -> ForbiddenEntry | None:
        return next((e for e in self._entries if e.policy_id == policy_id), None)


def check_forbidden(text: str, entry: ForbiddenEntry, policy: Policy) -> Finding | None:
    lowered = text.lower()
    for keyword in entry.keywords:
        idx = lowered.find(keyword.lower())
        if idx != -1:
            return _finding(policy, text[idx : idx + len(keyword)], f"Matched forbidden phrase '{keyword}'.")
    for pattern in entry.regexes:
        match = re.search(pattern, text)
        if match:
            return _finding(policy, match.group(0), f"Matched forbidden pattern '{pattern}'.")
    return None


def _finding(policy: Policy, evidence: str, message: str) -> Finding:
    return Finding(
        policy_id=policy.id,
        category=policy.category,
        severity=policy.severity,
        detector="deterministic",
        confidence=0.95,
        evidence=evidence,
        message=message,
        recommended_action=policy.recommended_action,
    )
