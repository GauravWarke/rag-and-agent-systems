"""Decide the eval type for a log and generate a proposed label for it.

Important examples (currently: safety edge cases, since getting those
wrong is the costliest labeling mistake) get a second independent pass;
if the two passes disagree on eval type, confidence is discounted so
the low-confidence example is more likely to be routed to human review
downstream.
"""
from __future__ import annotations

from app.core.models import EvalType, LogEntry, ProposedLabel
from app.labels.client import LabelClient


def decide_eval_type(log: LogEntry) -> EvalType:
    if log.safety_flag:
        return "expected_refusal"
    if log.user_feedback == "positive" and not log.error and not log.malformed_output:
        return "golden_answer"
    return "rubric"


def generate_label(log: LogEntry, client: LabelClient, important: bool = False) -> ProposedLabel:
    eval_type = decide_eval_type(log)
    passes = 2 if important else 1

    proposals = [client.propose(log, eval_type) for _ in range(passes)]
    if len(proposals) == 1:
        return proposals[0]

    first, second = proposals
    if first.eval_type != second.eval_type:
        return first.model_copy(update={"confidence": round(min(first.confidence, second.confidence) * 0.7, 4)})

    avg_confidence = round((first.confidence + second.confidence) / 2, 4)
    return first.model_copy(update={"confidence": avg_confidence})
