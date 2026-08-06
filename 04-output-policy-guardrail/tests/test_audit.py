from datetime import datetime, timezone

from app.core.audit import AuditLog, AuditLogEntry, hash_text


def _entry(request_id: str, decision: str) -> AuditLogEntry:
    return AuditLogEntry(
        request_id=request_id,
        timestamp=datetime.now(timezone.utc),
        feature="support-bot",
        input_hash=hash_text("prompt"),
        output_hash=hash_text("output"),
        policy_version="abc123",
        findings=[],
        decision=decision,
        latency_ms=1.0,
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
