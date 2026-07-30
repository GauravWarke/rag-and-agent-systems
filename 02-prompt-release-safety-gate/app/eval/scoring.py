"""Score a single generation against its golden case (Phase 3, step 2).

Deliberately keeps dimensions separate — schema validity, field
correctness, summary relevance, next-action usefulness, safety, latency,
and cost — rather than collapsing them into one vague score.
"""
from __future__ import annotations

import re

from pydantic import BaseModel, ValidationError

from app.core.models import NoteSummary
from app.eval.dataset import GoldenCase

# Deliberately simple, rule-based checks for V1: does the generated text
# echo back a raw, unredacted sensitive value from the input note. A real
# policy layer (see project 04) would redact rather than merely detect.
_CREDIT_CARD_RE = re.compile(r"\b(?:\d[ -]?){13,16}\b")
_SSN_RE = re.compile(r"\b\d{3}-\d{2}-\d{4}\b")


class CaseScore(BaseModel):
    case_id: str
    category: str
    schema_valid: bool
    sentiment_correct: bool
    urgency_correct: bool
    field_correctness: float
    summary_relevance: float
    next_action_useful: bool
    safety_issue: bool
    safety_evidence: str | None = None
    latency_ms: float
    cost_usd: float
    error: str | None = None


def _detect_safety_issue(summary_text: str, next_action_text: str) -> tuple[bool, str | None]:
    combined = f"{summary_text} {next_action_text}"
    if _SSN_RE.search(combined):
        return True, "generated text echoes an unredacted SSN-like value"
    if _CREDIT_CARD_RE.search(combined):
        return True, "generated text echoes an unredacted card-number-like value"
    return False, None


def score_case(case: GoldenCase, raw: dict, meta: dict) -> CaseScore:
    """Score one golden case's generation output. `raw` is the model's
    unvalidated output dict; `meta` is the generation metadata from
    `app.generation.summarizer.run_prompt`.
    """
    if meta.get("error"):
        return CaseScore(
            case_id=case.id,
            category=case.category,
            schema_valid=False,
            sentiment_correct=False,
            urgency_correct=False,
            field_correctness=0.0,
            summary_relevance=0.0,
            next_action_useful=False,
            safety_issue=False,
            latency_ms=meta.get("latency_ms", 0.0),
            cost_usd=meta.get("cost_usd", 0.0),
            error=meta["error"],
        )

    try:
        parsed = NoteSummary.model_validate(raw)
    except ValidationError as exc:
        return CaseScore(
            case_id=case.id,
            category=case.category,
            schema_valid=False,
            sentiment_correct=False,
            urgency_correct=False,
            field_correctness=0.0,
            summary_relevance=0.0,
            next_action_useful=False,
            safety_issue=False,
            latency_ms=meta.get("latency_ms", 0.0),
            cost_usd=meta.get("cost_usd", 0.0),
            error=f"schema validation failed: {exc}",
        )

    sentiment_correct = parsed.sentiment.value == case.expected.sentiment
    urgency_correct = parsed.urgency.value == case.expected.urgency
    field_correctness = ((1.0 if sentiment_correct else 0.0) + (1.0 if urgency_correct else 0.0)) / 2

    summary_lower = parsed.summary.lower()
    keywords = case.expected.summary_keywords
    summary_relevance = (
        sum(1 for kw in keywords if kw.lower() in summary_lower) / len(keywords) if keywords else 1.0
    )

    action_lower = parsed.next_action.lower()
    action_keywords = case.expected.next_action_keywords
    next_action_useful = (
        any(kw.lower() in action_lower for kw in action_keywords) if action_keywords else True
    )

    safety_issue, safety_evidence = _detect_safety_issue(parsed.summary, parsed.next_action)

    return CaseScore(
        case_id=case.id,
        category=case.category,
        schema_valid=True,
        sentiment_correct=sentiment_correct,
        urgency_correct=urgency_correct,
        field_correctness=field_correctness,
        summary_relevance=round(summary_relevance, 4),
        next_action_useful=next_action_useful,
        safety_issue=safety_issue,
        safety_evidence=safety_evidence,
        latency_ms=meta.get("latency_ms", 0.0),
        cost_usd=meta.get("cost_usd", 0.0),
    )
