from app.core.models import NoteSummary
from app.generation.summarizer import run_prompt
from app.prompts.loader import load_prompt

V1 = load_prompt("crm_summary_v1")
V2 = load_prompt("crm_summary_v2")


def test_run_prompt_produces_schema_valid_output():
    raw, meta = run_prompt("Hi, my card got charged twice for order #4821, please fix asap!!", V1)
    result = NoteSummary.model_validate(raw)
    assert result.sentiment.value in {"negative", "frustrated"}
    assert result.urgency.value in {"high", "critical"}
    assert meta["error"] is None
    assert meta["prompt_version"] == "v1"


def test_run_prompt_detects_positive_sentiment():
    raw, _ = run_prompt("Thanks so much, the team was awesome and fixed everything!", V1)
    assert raw["sentiment"] == "positive"


def test_run_prompt_detects_question_next_action():
    raw, _ = run_prompt("Does the pro plan include api access? cant find it in the docs", V1)
    assert "documentation" in raw["next_action"].lower()


def test_run_prompt_detects_refund_next_action():
    raw, _ = run_prompt("I want a refund for my last invoice please", V1)
    assert "refund" in raw["next_action"].lower()


def test_verbose_style_produces_longer_summary_and_higher_cost():
    note = "The app keeps crashing every time I try to export a report, this has been happening for a week."
    raw_v1, meta_v1 = run_prompt(note, V1)
    raw_v2, meta_v2 = run_prompt(note, V2)
    assert len(raw_v2["summary"]) > len(raw_v1["summary"])
    assert meta_v2["output_tokens"] >= meta_v1["output_tokens"]
    assert meta_v2["cost_usd"] >= meta_v1["cost_usd"]


def test_run_prompt_confidence_in_range():
    raw, _ = run_prompt("hi", V1)
    assert 0.0 <= raw["confidence"] <= 1.0
