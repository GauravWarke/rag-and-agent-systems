from datetime import datetime, timezone

import pytest

from app.core.models import (
    DeprecateRequest,
    LogEntry,
    ProposedLabel,
    ReviewDecisionRequest,
    ReviewEditFields,
)
from app.labels.dedupe import EvalCandidateStore, dedupe_and_add
from app.review.decisions import ReviewEditLogStore, apply_decision, deprecate_candidate

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


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


def _draft_candidate(store: EvalCandidateStore):
    proposed = ProposedLabel(eval_type="rubric", expected_behavior="Resolve the issue.", confidence=0.4)
    return dedupe_and_add(_log("1", "billing was charged twice this month"), proposed, store)


def test_approve_sets_review_status_and_logs_decision():
    store = EvalCandidateStore()
    edits = ReviewEditLogStore()
    candidate = _draft_candidate(store)
    assert candidate.review_status == "draft"

    req = ReviewDecisionRequest(candidate_id=candidate.id, action="approve", reviewer="alex", reason="Looks correct.")
    resp = apply_decision(req, store, edits, now=_NOW)

    assert resp.candidate.review_status == "approved"
    assert resp.edit_log.changed_fields == []
    assert store.get(candidate.id).review_status == "approved"
    assert edits.for_candidate(candidate.id) == [resp.edit_log]


def test_reject_sets_review_status_rejected():
    store = EvalCandidateStore()
    edits = ReviewEditLogStore()
    candidate = _draft_candidate(store)

    req = ReviewDecisionRequest(candidate_id=candidate.id, action="reject", reviewer="alex", reason="Not usable.")
    resp = apply_decision(req, store, edits, now=_NOW)

    assert resp.candidate.review_status == "rejected"


def test_edit_records_field_diff_and_approves():
    store = EvalCandidateStore()
    edits = ReviewEditLogStore()
    candidate = _draft_candidate(store)

    req = ReviewDecisionRequest(
        candidate_id=candidate.id,
        action="edit",
        reviewer="alex",
        reason="Tightened the expected behavior wording.",
        edits=ReviewEditFields(expected_behavior="Resolve the billing double-charge and confirm the refund."),
    )
    resp = apply_decision(req, store, edits, now=_NOW)

    assert resp.candidate.review_status == "approved"
    assert resp.candidate.expected_behavior == "Resolve the billing double-charge and confirm the refund."
    assert len(resp.edit_log.changed_fields) == 1
    change = resp.edit_log.changed_fields[0]
    assert change.field == "expected_behavior"
    assert change.old_value == "Resolve the issue."


def test_edit_without_edits_payload_raises():
    store = EvalCandidateStore()
    edits = ReviewEditLogStore()
    candidate = _draft_candidate(store)

    req = ReviewDecisionRequest(candidate_id=candidate.id, action="edit", reviewer="alex", reason="oops")
    with pytest.raises(ValueError):
        apply_decision(req, store, edits, now=_NOW)


def test_unknown_candidate_raises_key_error():
    store = EvalCandidateStore()
    edits = ReviewEditLogStore()
    req = ReviewDecisionRequest(candidate_id="nope", action="approve", reviewer="alex", reason="n/a")
    with pytest.raises(KeyError):
        apply_decision(req, store, edits, now=_NOW)


def test_reviewing_a_rejected_duplicate_raises_value_error():
    store = EvalCandidateStore()
    edits = ReviewEditLogStore()
    proposed = ProposedLabel(eval_type="golden_answer", expected_behavior="Summary: handled.", confidence=0.8)
    dedupe_and_add(_log("1", "billing was charged twice this month"), proposed, store, threshold=0.9)
    dup = dedupe_and_add(_log("2", "billing was charged twice this month"), proposed, store, threshold=0.9)

    req = ReviewDecisionRequest(candidate_id=dup.id, action="approve", reviewer="alex", reason="n/a")
    with pytest.raises(ValueError):
        apply_decision(req, store, edits, now=_NOW)


def test_deprecate_only_allowed_for_approved_candidates():
    store = EvalCandidateStore()
    edits = ReviewEditLogStore()
    candidate = _draft_candidate(store)

    with pytest.raises(ValueError):
        deprecate_candidate(
            DeprecateRequest(candidate_id=candidate.id, reviewer="alex", reason="superseded"), store, edits, now=_NOW
        )

    approve_req = ReviewDecisionRequest(candidate_id=candidate.id, action="approve", reviewer="alex", reason="ok")
    apply_decision(approve_req, store, edits, now=_NOW)

    resp = deprecate_candidate(
        DeprecateRequest(candidate_id=candidate.id, reviewer="alex", reason="superseded by v2"), store, edits, now=_NOW
    )
    assert resp.candidate.review_status == "deprecated"
