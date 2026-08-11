"""Export approved eval cases to JSONL.

Only `review_status == "approved"` candidates ship — drafts haven't cleared
review yet, and rejected/deprecated cases shouldn't feed a live eval suite.
"""
from __future__ import annotations

import json

from app.core.models import EvalCandidate


def eval_case_record(candidate: EvalCandidate) -> dict:
    return {
        "id": candidate.id,
        "input": candidate.input,
        "expected_behavior": candidate.expected_behavior,
        "eval_type": candidate.eval_type,
        "rubric": candidate.rubric,
        "tags": candidate.tags,
        "difficulty": candidate.difficulty,
        "source_cluster": candidate.cluster_id,
        "date_added": candidate.created_at.isoformat(),
    }


def export_jsonl(candidates: list[EvalCandidate]) -> str:
    approved = [c for c in candidates if c.review_status == "approved"]
    lines = [json.dumps(eval_case_record(c), sort_keys=True) for c in approved]
    return "\n".join(lines)
