"""Lightweight, rule-based request complexity classifier.

Tier 1: extraction and formatting — short, mechanical instructions.
Tier 2: summarization and classification — the default for anything
        that isn't clearly mechanical or clearly high-stakes.
Tier 3: reasoning-heavy or high-risk work — long context, explicit
        risk tags, or verbs that imply judgment rather than transcription.

A simple model is fine here; the point is that routing decisions are
explainable, not that the classifier is state of the art.
"""
from __future__ import annotations

from collections.abc import Sequence

_TIER1_VERBS = (
    "extract", "format", "list", "convert", "translate", "capitalize",
    "parse", "reformat", "tabulate",
)
_TIER3_VERBS = (
    "analyze", "reason", "decide", "diagnose", "recommend", "strategize",
    "evaluate", "investigate", "audit", "negotiate",
)
_HIGH_RISK_TAGS = frozenset({"legal", "medical", "financial", "security"})

_TIER1_MAX_CHARS = 500
_TIER3_MIN_CHARS = 2000


def classify_complexity(text: str, risk_tags: Sequence[str] = ()) -> int:
    """Return a routing tier (1, 2, or 3) for the given request text."""
    if any(tag in _HIGH_RISK_TAGS for tag in risk_tags):
        return 3

    lower = text.lower()
    if len(text) >= _TIER3_MIN_CHARS or any(v in lower for v in _TIER3_VERBS):
        return 3
    if len(text) <= _TIER1_MAX_CHARS and any(v in lower for v in _TIER1_VERBS):
        return 1
    return 2
