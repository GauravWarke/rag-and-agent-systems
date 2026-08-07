from datetime import datetime, timezone

from app.core.audit import AuditLog, AuditLogEntry, hash_text
from app.core.models import Finding


def _finding(policy_id: str, category: str) -> Finding:
    return Finding(
        policy_id=policy_id,
        category=category,
        severity="high",
        detector="deterministic",
        confidence=1.0,
        evidence="",
        message="m",
        recommended_action="block",
    )


def _entry(request_id: str, decision: str, latency_ms: float = 1.0, findings: list[Finding] | None = None) -> AuditLogEntry:
    return AuditLogEntry(
        request_id=request_id,
        timestamp=datetime.now(timezone.utc),
        feature="support-bot",
        input_hash=hash_text("prompt"),
        output_hash=hash_text("output"),
        policy_version="abc123",
        findings=findings or [],
        decision=decision,
        latency_ms=latency_ms,
        final_output=None,
        reason_codes=[],
    )


def test_hash_text_is_stable_and_does_not_return_the_input():
    h1 = hash_text("secret value")
    h2 = hash_text("secret value")
    assert h1 == h2
    assert h1 != "secret value"


def test_pending_review_includes_block_and_human_review_only():
    log = AuditLog()
    log.log(_entry("r1", "approve"))
    log.log(_entry("r2", "block"))
    log.log(_entry("r3", "human_review"))
    log.log(_entry("r4", "rewrite"))
    pending_ids = {e.request_id for e in log.pending_review()}
    assert pending_ids == {"r2", "r3"}


def test_submit_review_marks_entry_reviewed_and_removes_from_queue():
    log = AuditLog()
    log.log(_entry("r1", "block"))
    updated = log.submit_review("r1", reviewer="alice", action="reject", note="confirmed unsafe")
    assert updated is not None
    assert updated.reviewed
    assert updated.reviewer == "alice"
    assert updated.review_action == "reject"
    assert updated.review_note == "confirmed unsafe"
    assert log.pending_review() == []


def test_submit_review_returns_none_for_unknown_request_id():
    log = AuditLog()
    assert log.submit_review("missing", reviewer="alice", action="approve") is None


def test_get_returns_the_matching_entry():
    log = AuditLog()
    log.log(_entry("r1", "approve"))
    assert log.get("r1").feature == "support-bot"
    assert log.get("missing") is None


def test_metrics_on_empty_log():
    metrics = AuditLog().metrics()
    assert metrics.total_reviewed == 0
    assert metrics.block_rate == 0.0
    assert metrics.false_positive_rate is None
    assert metrics.top_violations == []


def test_metrics_computes_rates_and_avg_latency():
    log = AuditLog()
    log.log(_entry("r1", "approve", latency_ms=10.0))
    log.log(_entry("r2", "approve_with_warning", latency_ms=20.0))
    log.log(_entry("r3", "rewrite", latency_ms=30.0))
    log.log(_entry("r4", "block", latency_ms=40.0))

    metrics = log.metrics()
    assert metrics.total_reviewed == 4
    assert metrics.block_rate == 0.25
    assert metrics.rewrite_rate == 0.25
    assert metrics.approve_rate == 0.5
    assert metrics.human_review_rate == 0.0
    assert metrics.avg_latency_ms == 25.0


def test_metrics_false_positive_rate_only_counts_reviewed_flagged_entries():
    log = AuditLog()
    log.log(_entry("r1", "block"))
    log.log(_entry("r2", "human_review"))
    log.log(_entry("r3", "approve"))  # never flagged, irrelevant to the rate
    log.submit_review("r1", reviewer="alice", action="approve")  # overturned: false positive
    log.submit_review("r2", reviewer="alice", action="reject")  # confirmed correct

    metrics = log.metrics()
    assert metrics.false_positive_rate == 0.5


def test_metrics_ranks_top_violations_by_count():
    log = AuditLog()
    log.log(_entry("r1", "block", findings=[_finding("toxic_language", "toxicity")]))
    log.log(_entry("r2", "block", findings=[_finding("toxic_language", "toxicity")]))
    log.log(_entry("r3", "rewrite", findings=[_finding("pii_leakage", "pii")]))

    top = log.metrics(top_n=1).top_violations
    assert len(top) == 1
    assert top[0].policy_id == "toxic_language"
    assert top[0].count == 2
