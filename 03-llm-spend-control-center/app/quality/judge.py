"""Offline stand-in for an LLM-as-judge quality comparison.

A real deployment would send both outputs to a judge model and ask it to
score whether the cheaper response is as good as the reference. Token
overlap is a much weaker signal, but it's deterministic and keyless, which
keeps routing verification testable offline like the rest of this project.
"""
from __future__ import annotations

import re

_WORD_RE = re.compile(r"[a-z0-9]+")


def _tokenize(text: str) -> set[str]:
    return set(_WORD_RE.findall(text.lower()))


def score_similarity(candidate: str, reference: str) -> float:
    """Jaccard token overlap between two outputs, in [0, 1]."""
    candidate_tokens = _tokenize(candidate)
    reference_tokens = _tokenize(reference)
    if not candidate_tokens and not reference_tokens:
        return 1.0
    if not candidate_tokens or not reference_tokens:
        return 0.0
    intersection = candidate_tokens & reference_tokens
    union = candidate_tokens | reference_tokens
    return len(intersection) / len(union)
