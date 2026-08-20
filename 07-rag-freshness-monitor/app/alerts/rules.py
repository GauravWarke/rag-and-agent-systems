"""Turn a freshness scorecard into human-readable alert messages.

Not every signal is alert-worthy on its own — a scorecard with zero
high-risk changes, zero drifting probes, and zero stale-answer risks
should not page anyone.
"""
from __future__ import annotations

from app.core.models import FreshnessScorecard


def build_alerts(scorecard: FreshnessScorecard) -> list[str]:
    alerts: list[str] = []
    if scorecard.chunks_needing_reindex:
        alerts.append(
            f"{scorecard.chunks_needing_reindex} high-priority doc change(s) "
            "need re-indexing (docs changed without a rebuild)."
        )
    if scorecard.probes_drifting:
        alerts.append(f"{scorecard.probes_drifting} probe question(s) are showing retrieval drift.")
    if scorecard.stale_answer_risks:
        alerts.append(
            f"{scorecard.stale_answer_risks} probe answer(s) may be stale "
            "(source changed but the answer did not)."
        )
    return alerts
