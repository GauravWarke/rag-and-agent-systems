from datetime import datetime, timezone

from app.core.models import LogEntry, ProposedLabel
from app.labels.dedupe import EvalCandidateStore, dedupe_and_add


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


def _proposed() -> ProposedLabel:
    return ProposedLabel(eval_type="golden_answer", expected_behavior="Summary: handled.", confidence=0.8)


def test_first_candidate_is_accepted():
    store = EvalCandidateStore()
    candidate = dedupe_and_add(_log("1", "billing was charged twice this month"), _proposed(), store)
    assert candidate.status == "accepted"
    assert len(store.accepted()) == 1


def test_near_identical_prompt_is_rejected_as_duplicate():
    store = EvalCandidateStore()
    dedupe_and_add(_log("1", "billing was charged twice this month"), _proposed(), store, threshold=0.9)
    dup = dedupe_and_add(_log("2", "billing was charged twice this month"), _proposed(), store, threshold=0.9)
    assert dup.status == "rejected_duplicate"
    assert dup.duplicate_of is not None
    assert len(store.accepted()) == 1


def test_distinct_prompt_is_accepted():
    store = EvalCandidateStore()
    dedupe_and_add(_log("1", "billing was charged twice this month"), _proposed(), store, threshold=0.9)
    second = dedupe_and_add(
        _log("2", "the API returns a 500 error on the orders endpoint"), _proposed(), store, threshold=0.9
    )
    assert second.status == "accepted"
    assert len(store.accepted()) == 2


def test_all_returns_both_accepted_and_rejected():
    store = EvalCandidateStore()
    dedupe_and_add(_log("1", "billing was charged twice this month"), _proposed(), store, threshold=0.9)
    dedupe_and_add(_log("2", "billing was charged twice this month"), _proposed(), store, threshold=0.9)
    assert len(store.all()) == 2
