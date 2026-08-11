import json
from datetime import datetime, timezone

from app.core.models import LogEntry, ProposedLabel, ReviewDecisionRequest
from app.eval_runner.export import export_jsonl
from app.labels.dedupe import EvalCandidateStore, dedupe_and_add
from app.review.decisions import ReviewEditLogStore, apply_decision

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
        user_feedback="positive",
    )


def test_export_only_includes_approved_cases():
    store = EvalCandidateStore()
    draft = dedupe_and_add(
        _log("1", "billing was charged twice this month"),
        ProposedLabel(eval_type="rubric", expected_behavior="Resolve it.", confidence=0.4),
        store,
        cluster_id=2,
        now=_NOW,
    )
    approved = dedupe_and_add(
        _log("2", "the API returns a 500 on orders"),
        ProposedLabel(eval_type="golden_answer", expected_behavior="Fixed.", confidence=0.9),
        store,
        cluster_id=1,
        now=_NOW,
    )

    body = export_jsonl(store.all())
    assert body.count("\n") == 0  # only the auto-approved case (confidence 0.9) qualifies
    record = json.loads(body)
    assert record["id"] == approved.id
    assert draft.id not in body


def test_export_record_shape():
    store = EvalCandidateStore()
    candidate = dedupe_and_add(
        _log("1", "billing was charged twice this month"),
        ProposedLabel(
            eval_type="golden_answer",
            expected_behavior="Fixed.",
            rubric=None,
            confidence=0.9,
        ),
        store,
        cluster_id=3,
        now=_NOW,
    )

    record = json.loads(export_jsonl(store.all()))
    assert record["input"] == candidate.input
    assert record["expected_behavior"] == "Fixed."
    assert record["tags"] == ["crm_note_summary"]
    assert record["difficulty"] == "easy"
    assert record["source_cluster"] == 3
    assert record["date_added"] == _NOW.isoformat()


def test_export_excludes_rejected_and_deprecated():
    store = EvalCandidateStore()
    edits = ReviewEditLogStore()
    candidate = dedupe_and_add(
        _log("1", "billing was charged twice this month"),
        ProposedLabel(eval_type="rubric", expected_behavior="Resolve it.", confidence=0.4),
        store,
        now=_NOW,
    )
    apply_decision(
        ReviewDecisionRequest(candidate_id=candidate.id, action="reject", reviewer="alex", reason="not usable"),
        store,
        edits,
        now=_NOW,
    )
    assert export_jsonl(store.all()) == ""
