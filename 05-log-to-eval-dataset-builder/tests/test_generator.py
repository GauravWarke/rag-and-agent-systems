from datetime import datetime, timezone

from app.core.models import EvalType, LogEntry, ProposedLabel
from app.labels.client import LabelClient
from app.labels.generator import decide_eval_type, generate_label


def _log(**overrides) -> LogEntry:
    defaults = {
        "id": "log-1",
        "timestamp": datetime.now(timezone.utc),
        "feature": "crm_note_summary",
        "prompt": "Customer reports billing charged twice.",
        "response": "Summary: billing double-charge reported.",
        "model": "gpt-4o-mini",
        "latency_ms": 200.0,
        "input_tokens": 50,
        "output_tokens": 20,
        "user_feedback": "positive",
    }
    defaults.update(overrides)
    return LogEntry(**defaults)


def test_decide_eval_type_safety_flag_wins():
    assert decide_eval_type(_log(safety_flag=True, user_feedback="positive")) == "expected_refusal"


def test_decide_eval_type_positive_clean_is_golden_answer():
    assert decide_eval_type(_log(user_feedback="positive")) == "golden_answer"


def test_decide_eval_type_negative_is_rubric():
    assert decide_eval_type(_log(user_feedback="negative")) == "rubric"


def test_decide_eval_type_error_overrides_positive_feedback():
    assert decide_eval_type(_log(user_feedback="positive", error=True)) == "rubric"


class _FixedClient(LabelClient):
    name = "fixed"

    def __init__(self, responses: list[ProposedLabel]) -> None:
        self._responses = iter(responses)

    def propose(self, log: LogEntry, eval_type: EvalType) -> ProposedLabel:
        return next(self._responses)


def _label(eval_type: EvalType, confidence: float) -> ProposedLabel:
    return ProposedLabel(eval_type=eval_type, expected_behavior="x", confidence=confidence)


def test_single_pass_for_normal_example():
    client = _FixedClient([_label("golden_answer", 0.8)])
    label = generate_label(_log(), client, important=False)
    assert label.confidence == 0.8


def test_two_passes_averages_confidence_when_agreeing():
    client = _FixedClient([_label("golden_answer", 0.8), _label("golden_answer", 0.6)])
    label = generate_label(_log(), client, important=True)
    assert label.confidence == 0.7


def test_two_passes_discounts_confidence_when_disagreeing():
    client = _FixedClient([_label("golden_answer", 0.8), _label("rubric", 0.6)])
    label = generate_label(_log(), client, important=True)
    assert label.confidence < 0.6
