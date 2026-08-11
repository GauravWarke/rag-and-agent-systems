"""Dataset health: size, composition, and review coverage of the growing
eval dataset — the numbers a reviewer or CI gate checks before trusting it.
"""
from __future__ import annotations

from collections import Counter
from datetime import datetime

from app.core.models import DatasetHealth, EvalCandidate, ReviewEditLogEntry


def compute_dataset_health(
    candidates: list[EvalCandidate],
    edit_entries: list[ReviewEditLogEntry],
    now: datetime,
) -> DatasetHealth:
    accepted = [c for c in candidates if c.status == "accepted"]
    total = len(accepted)

    reviewed_ids = {e.candidate_id for e in edit_entries}
    human_reviewed = sum(1 for c in accepted if c.id in reviewed_ids)
    auto_labeled = total - human_reviewed

    ages_days = [(now - c.created_at).total_seconds() / 86400 for c in accepted]

    return DatasetHealth(
        total_cases=total,
        by_eval_type=dict(Counter(c.eval_type for c in accepted)),
        by_difficulty=dict(Counter(c.difficulty for c in accepted)),
        by_review_status=dict(Counter(c.review_status for c in accepted)),
        auto_labeled_pct=round(100 * auto_labeled / total, 2) if total else 0.0,
        human_reviewed_pct=round(100 * human_reviewed / total, 2) if total else 0.0,
        avg_case_age_days=round(sum(ages_days) / len(ages_days), 2) if ages_days else 0.0,
        oldest_case_at=min((c.created_at for c in accepted), default=None),
        newest_case_at=max((c.created_at for c in accepted), default=None),
    )
