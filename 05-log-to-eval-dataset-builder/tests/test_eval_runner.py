from datetime import datetime, timezone

from app.core.models import EvalCandidate
from app.eval_runner.runner import StubEvalTargetClient, run_eval, score_case

_NOW = datetime(2026, 1, 1, tzinfo=timezone.utc)


def _candidate(candidate_id: str, eval_type: str, **overrides) -> EvalCandidate:
    defaults = {
        "id": candidate_id,
        "log_id": "log-1",
        "feature": "crm_note_summary",
        "input": "Customer reports billing charged twice.",
        "eval_type": eval_type,
        "expected_behavior": "Refund the duplicate charge and confirm with the customer.",
        "key_assertions": ["mentions refund", "confirms with customer"],
        "forbidden_assertions": ["response invents a policy"],
        "rubric": None,
        "confidence": 0.9,
        "status": "accepted",
        "reason": "accepted: no existing case above the similarity threshold",
        "review_status": "approved",
        "created_at": _NOW,
    }
    defaults.update(overrides)
    return EvalCandidate(**defaults)


def test_score_case_golden_answer_pass_and_fail():
    candidate = _candidate("1", "golden_answer")
    passing = score_case(candidate, candidate.expected_behavior)
    assert passing.passed is True

    failing = score_case(candidate, "I have no idea what you mean.")
    assert failing.passed is False


def test_score_case_expected_refusal():
    candidate = _candidate("1", "expected_refusal")
    refused = score_case(candidate, "I can't help with that, but here's a safe alternative.")
    assert refused.passed is True

    complied = score_case(candidate, "Sure, here's how to do that.")
    assert complied.passed is False


def test_score_case_rubric_uses_key_assertions():
    candidate = _candidate("1", "rubric")
    good = score_case(candidate, "Here's a refund, and I will confirm with the customer directly.")
    assert good.passed is True

    bad = score_case(candidate, "This is a generic, unhelpful reply.")
    assert bad.passed is False


def test_score_case_forbidden_assertion_forces_fail():
    candidate = _candidate("1", "golden_answer", forbidden_assertions=["invents a policy"])
    result = score_case(
        candidate, candidate.expected_behavior + " Note this response invents a policy that does not exist."
    )
    assert result.passed is False
    assert "forbidden" in result.explanation


def test_stub_client_is_deterministic():
    client = StubEvalTargetClient()
    candidate = _candidate("stable-id", "golden_answer")
    assert client.respond(candidate) == client.respond(candidate)


def test_run_eval_computes_pass_rate_and_totals():
    candidates = [_candidate(str(i), "golden_answer") for i in range(20)]
    run = run_eval(candidates, StubEvalTargetClient(), timestamp=_NOW)
    assert run.total_cases == 20
    assert run.passed + run.failed == 20
    assert 0.0 <= run.pass_rate <= 1.0
    assert run.pass_rate_delta is None
    assert run.newly_failing == []
    assert run.newly_passing == []


def test_run_eval_diffs_against_previous_run():
    candidates = [_candidate(str(i), "golden_answer") for i in range(20)]
    client = StubEvalTargetClient()
    first = run_eval(candidates, client, timestamp=_NOW)
    second = run_eval(candidates, client, timestamp=_NOW, previous=first)

    # Same candidates, same deterministic client -> identical outcomes, no regressions.
    assert second.pass_rate == first.pass_rate
    assert second.pass_rate_delta == 0.0
    assert second.newly_failing == []
    assert second.newly_passing == []
