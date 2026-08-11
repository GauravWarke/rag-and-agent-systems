from datetime import datetime, timedelta, timezone

from app.core.models import LogEntry, ProposedLabel, ReviewDecisionRequest
from app.eval_runner.health import compute_dataset_health
from app.labels.dedupe import EvalCandidateStore, dedupe_and_add
from app.review.decisions import ReviewEditLogStore, apply_decision

_DAY1 = datetime(2026, 1, 1, tzinfo=timezone.utc)
_DAY3 = _DAY1 + timedelta(days=2)


def _log(log_id: str, prompt: str) -> LogEntry:
    return LogEntry(
        id=log_id,
        timestamp=datetime.now(timezone.utc),
        feature="crm_note_summary",
        prompt=prompt,
        response="Summary: handled.",
        model="gpt-4o-mini",
        latency_ms=200.0,
        input_tokens=50,
        output_tokens=20,
        user_feedback="positive",
    )


def test_health_on_empty_dataset():
    health = compute_dataset_health([], [], now=_DAY3)
    assert health.total_cases == 0
    assert health.auto_labeled_pct == 0.0
    assert health.human_reviewed_pct == 0.0
    assert health.oldest_case_at is None


def test_health_counts_auto_vs_human_reviewed():
    store = EvalCandidateStore()
    edits = ReviewEditLogStore()

    auto_approved = dedupe_and_add(
        _log("1", "billing was charged twice this month"),
        ProposedLabel(eval_type="golden_answer", expected_behavior="Fixed.", confidence=0.9),
        store,
        now=_DAY1,
    )
    draft = dedupe_and_add(
        _log("2", "the API returns a 500 on orders"),
        ProposedLabel(eval_type="rubric", expected_behavior="Investigate.", confidence=0.4),
        store,
        now=_DAY3,
    )
    apply_decision(
        ReviewDecisionRequest(candidate_id=draft.id, action="approve", reviewer="alex", reason="looks fine"),
        store,
        edits,
        now=_DAY3,
    )

    health = compute_dataset_health(store.all(), edits.all(), now=_DAY3)
    assert health.total_cases == 2
    assert health.by_review_status["approved"] == 2
    assert health.human_reviewed_pct == 50.0
    assert health.auto_labeled_pct == 50.0
    assert health.oldest_case_at == _DAY1
    assert health.newest_case_at == _DAY3
    assert health.avg_case_age_days == 1.0
    assert auto_approved.review_status == "approved"


def test_health_excludes_rejected_duplicates_from_totals():
    store = EvalCandidateStore()
    proposed = ProposedLabel(eval_type="golden_answer", expected_behavior="Fixed.", confidence=0.9)
    dedupe_and_add(_log("1", "billing was charged twice this month"), proposed, store, threshold=0.9, now=_DAY1)
    dedupe_and_add(_log("2", "billing was charged twice this month"), proposed, store, threshold=0.9, now=_DAY1)

    health = compute_dataset_health(store.all(), [], now=_DAY1)
    assert health.total_cases == 1
