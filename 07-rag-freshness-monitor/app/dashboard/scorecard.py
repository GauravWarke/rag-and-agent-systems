"""Roll up every freshness signal into one scorecard: docs changed,
chunks needing re-index, probe drift, answer drift, and stale-answer
risk. This is the artifact a reviewer opens first — it doesn't compute
anything new, it just summarizes the reports the other endpoints already
produce.

Every input is optional so the scorecard degrades gracefully before the
full pipeline (build, freshness scan, probe run, answer run) has been
exercised yet, instead of erroring out.
"""
from __future__ import annotations

from datetime import UTC, datetime

from app.core.models import (
    AnswerDriftReport,
    DriftReport,
    FreshnessReport,
    FreshnessScorecard,
    ProbeRunSummary,
    StaleAnswerReport,
)

# Priorities urgent enough to surface as a re-index recommendation.
_REINDEX_PRIORITIES = {"critical", "high"}


def build_scorecard(
    freshness: FreshnessReport | None,
    probes: ProbeRunSummary | None,
    probe_drift: DriftReport | None,
    answer_drift: AnswerDriftReport | None,
    stale_answer: StaleAnswerReport | None,
) -> FreshnessScorecard:
    docs_changed = 0
    recommendations = []
    if freshness is not None:
        diff = freshness.diff
        docs_changed = len(diff.added) + len(diff.removed) + len(diff.modified)
        recommendations = [pc for pc in freshness.prioritized if pc.priority in _REINDEX_PRIORITIES]

    return FreshnessScorecard(
        generated_at=datetime.now(UTC).isoformat(),
        manifest_available=freshness is not None,
        docs_changed=docs_changed,
        chunks_needing_reindex=len(recommendations),
        probes_total=probes.total_probes if probes is not None else 0,
        probes_drifting=probe_drift.drift_count if probe_drift is not None else 0,
        answer_drift_checked=len(answer_drift.verdicts) if answer_drift is not None else 0,
        answer_drift_changed=answer_drift.changed_count if answer_drift is not None else 0,
        stale_answer_risks=stale_answer.at_risk_count if stale_answer is not None else 0,
        recommendations=recommendations,
    )
