from datetime import datetime, timezone

from app.core.models import LogEntry, ProposedLabel
from app.labels.dedupe import EvalCandidateStore, dedupe_and_add
from app.logs.store import LogStore
from app.review.queue import (
    build_queue,
    build_queue_item,
    pending_review,
    similar_cases,
)


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
        user_feedback="none",
    )


def _low_confidence() -> ProposedLabel:
    return ProposedLabel(eval_type="rubric", expected_behavior="Resolve the issue.", confidence=0.55)


def _high_confidence() -> ProposedLabel:
    return ProposedLabel(eval_type="golden_answer", expected_behavior="Summary: handled.", confidence=0.9)


def test_pending_review_only_includes_draft_candidates():
    store = EvalCandidateStore()
    draft = dedupe_and_add(_log("1", "billing was charged twice"), _low_confidence(), store, threshold=0.9)
    approved = dedupe_and_add(_log("2", "reset the API key please"), _high_confidence(), store, threshold=0.9)

    assert draft.review_status == "draft"
    assert approved.review_status == "approved"

    queue = pending_review(store)
    assert [c.id for c in queue] == [draft.id]


def test_similar_cases_only_returns_approved_and_excludes_self():
    store = EvalCandidateStore()
    approved = dedupe_and_add(_log("1", "billing was charged twice this month"), _high_confidence(), store, threshold=0.99)
    draft = dedupe_and_add(_log("2", "billing was charged twice this month again"), _low_confidence(), store, threshold=0.99)

    matches = similar_cases(draft, store, top_n=3)
    assert [c.id for c in matches] == [approved.id]


def test_build_queue_item_returns_none_for_missing_log():
    log_store = LogStore()
    store = EvalCandidateStore()
    candidate = dedupe_and_add(_log("missing", "a prompt with no matching log entry"), _low_confidence(), store)

    assert build_queue_item(candidate, log_store, store) is None


def test_build_queue_pairs_candidates_with_their_source_log():
    log_store = LogStore()
    store = EvalCandidateStore()
    log = _log("1", "billing was charged twice this month")
    log_store.add_entry(log)
    dedupe_and_add(log, _low_confidence(), store)

    items = build_queue(store, log_store)
    assert len(items) == 1
    assert items[0].log.id == log.id
    assert items[0].candidate.review_status == "draft"
