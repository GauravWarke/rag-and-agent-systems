from app.eval.metrics import CaseResult, EvalSummary
from app.eval.report import render_html_dashboard, render_markdown


def _summary(strategy: str) -> EvalSummary:
    case = CaseResult(
        id="q1",
        question="What does </script><b>error 429</b> mean?",
        category="simple_lookup",
        strategy=strategy,
        answer="It means 'rate limit' & retry.",
        confidence=0.8,
        retrieved_sources=["faq"],
        retrieval_applicable=True,
        retrieval_correct=True,
        answer_applicable=True,
        answer_correct=True,
        citation_applicable=True,
        citations_valid=True,
        refusal_correct=True,
    )
    return EvalSummary(
        strategy=strategy,
        total_cases=1,
        retrieval_hit_rate=1.0,
        answer_correct_rate=1.0,
        citation_valid_rate=1.0,
        refusal_correct_rate=1.0,
        cases=[case],
    )


def test_render_markdown_includes_metrics_and_case_row():
    md = render_markdown(_summary("hybrid"))

    assert "strategy: `hybrid`" in md
    assert "Retrieval hit rate: 100%" in md
    assert "q1" in md
    assert "pass" in md


def test_render_html_dashboard_embeds_all_strategies_and_neutralizes_script_breakout():
    html = render_html_dashboard({"hybrid": _summary("hybrid"), "dense": _summary("dense")})

    assert "<select id=\"strategy\">" in html
    assert 'value="hybrid"' in html
    assert 'value="dense"' in html
    assert "error 429" in html
    # a literal "</script>" inside case text must not close the embedding
    # script tag early — only the real closing tag at the end should remain.
    assert html.count("</script>") == 1
    # DOM injection uses the esc() helper rather than raw innerHTML content.
    assert "function esc(" in html


def test_render_html_dashboard_requires_at_least_one_summary():
    import pytest

    with pytest.raises(ValueError):
        render_html_dashboard({})
