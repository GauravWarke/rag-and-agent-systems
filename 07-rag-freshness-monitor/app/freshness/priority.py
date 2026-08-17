"""Rank freshness changes by how urgently they need re-indexing.

Not all document changes are equal: a typo fix and a pricing change both
show up as "modified", but only one should page someone. Priority is
driven by user-impact keywords in the section, not by file modification
time alone.
"""
from __future__ import annotations

from app.core.models import (
    FreshnessDiff,
    PrioritizedChange,
    PriorityLevel,
    SectionChange,
)

_KEYWORDS: dict[PriorityLevel, list[str]] = {
    "critical": ["security", "breach", "password", "credential", "incident"],
    "high": ["pricing", "price", "refund", "policy", "api", "rate limit", "cost", "deprecat"],
    "medium": ["troubleshooting", "error", "failure", "sync", "login", "integration"],
}

# Below this score, a "modified" change is treated as cosmetic (e.g. a typo
# fix) and never escalated past low priority regardless of keyword hits.
_TRIVIAL_CHANGE_THRESHOLD = 0.02


def _keyword_hits(text: str) -> tuple[PriorityLevel | None, list[str]]:
    lowered = text.lower()
    for level in ("critical", "high", "medium"):
        hits = [kw for kw in _KEYWORDS[level] if kw in lowered]
        if hits:
            return level, hits  # type: ignore[return-value]
    return None, []


def classify_change(change: SectionChange) -> PrioritizedChange:
    haystack = " ".join(
        filter(None, [change.section_heading, change.old_text, change.new_text])
    )
    level, hits = _keyword_hits(haystack)
    reasons = [f"matched keyword {hit!r}" for hit in hits]

    if change.change_type == "modified" and change.semantic_change_score is not None:
        if change.semantic_change_score < _TRIVIAL_CHANGE_THRESHOLD:
            reasons.append("semantic change score below cosmetic-edit threshold")
            return PrioritizedChange(change=change, priority="low", reasons=reasons)
        reasons.append(f"semantic change score {change.semantic_change_score:.3f}")

    if level is None:
        level = "medium" if change.change_type in ("added", "removed") else "low"
        reasons.append(f"no impact keywords found; defaulted by change_type={change.change_type!r}")

    return PrioritizedChange(change=change, priority=level, reasons=reasons)


_PRIORITY_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3}


def prioritize_diff(diff: FreshnessDiff) -> list[PrioritizedChange]:
    changes = [*diff.added, *diff.removed, *diff.modified]
    classified = [classify_change(c) for c in changes]
    return sorted(classified, key=lambda pc: _PRIORITY_ORDER[pc.priority])
