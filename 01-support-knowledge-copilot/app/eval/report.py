"""Eval report rendering (Phase 5, steps 3-4).

Two output formats from the same `EvalSummary` data:

- Markdown: an aggregate scorecard plus a per-question pass/fail table. This
  is the artifact `eval.py` writes first, meant to be opened directly in a
  PR or terminal.
- HTML dashboard: question, answer, retrieved chunks, citation verdicts, and
  confidence breakdown per case, with a client-side toggle to compare
  dense-only vs. hybrid retrieval without re-running anything. Data is
  embedded as JSON and rendered with a small escaping helper so no case
  text (question/answer content) is ever interpreted as HTML/script.
"""
from __future__ import annotations

import json

from app.eval.metrics import EvalSummary


def render_markdown(summary: EvalSummary) -> str:
    lines = [
        f"# Eval Report — strategy: `{summary.strategy}`",
        "",
        f"- Total cases: {summary.total_cases}",
        f"- Retrieval hit rate: {summary.retrieval_hit_rate:.0%}",
        f"- Answer correct rate: {summary.answer_correct_rate:.0%}",
        f"- Citation valid rate: {summary.citation_valid_rate:.0%}",
        f"- Refusal correct rate: {summary.refusal_correct_rate:.0%}",
        "",
        "## Per-question results",
        "",
        "| ID | Category | Question | Retrieval | Answer | Citations | Refusal | Confidence |",
        "|---|---|---|---|---|---|---|---|",
    ]

    def mark(applicable: bool, correct: bool) -> str:
        if not applicable:
            return "n/a"
        return "pass" if correct else "FAIL"

    for c in summary.cases:
        question = c.question.replace("|", "\\|")
        lines.append(
            f"| {c.id} | {c.category} | {question} | "
            f"{mark(c.retrieval_applicable, c.retrieval_correct)} | "
            f"{mark(c.answer_applicable, c.answer_correct)} | "
            f"{mark(c.citation_applicable, c.citations_valid)} | "
            f"{'pass' if c.refusal_correct else 'FAIL'} | {c.confidence:.2f} |"
        )
    return "\n".join(lines) + "\n"


def render_html_dashboard(summaries: dict[str, EvalSummary]) -> str:
    """Render a single static HTML file with a strategy toggle (Phase 5,
    step 3). Pure client-side JS — no server required, so a reviewer can
    open the file directly."""
    if not summaries:
        raise ValueError("render_html_dashboard requires at least one strategy summary")

    data = {
        strategy: {
            "metrics": {
                "retrieval_hit_rate": s.retrieval_hit_rate,
                "answer_correct_rate": s.answer_correct_rate,
                "citation_valid_rate": s.citation_valid_rate,
                "refusal_correct_rate": s.refusal_correct_rate,
            },
            "cases": [c.model_dump() for c in s.cases],
        }
        for strategy, s in summaries.items()
    }
    # `.replace("</", ...)` stops a "</script>" inside question/answer text
    # from prematurely closing the embedding <script> tag; DOM-level escaping
    # of the same content happens in `esc()` below, at render time.
    payload = json.dumps(data).replace("</", "<\\/")
    default_strategy = next(iter(summaries))
    options = "\n".join(f'<option value="{s}">{s}</option>' for s in summaries)

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>Support Knowledge Copilot — Eval Dashboard</title>
<style>
body {{ font-family: system-ui, sans-serif; margin: 2rem; color: #1a1a1a; }}
table {{ border-collapse: collapse; width: 100%; margin-top: 1rem; }}
th, td {{ border: 1px solid #ddd; padding: 6px 10px; text-align: left; font-size: 0.9rem; vertical-align: top; }}
th {{ background: #f4f4f4; }}
.metrics span {{ margin-right: 1.5rem; font-weight: 600; }}
.ok {{ color: #1a7f37; }}
.bad {{ color: #c0392b; }}
.na {{ color: #999; }}
</style>
</head>
<body>
<h1>Eval Dashboard</h1>
<p>
  <label for="strategy">Retrieval strategy: </label>
  <select id="strategy">{options}</select>
</p>
<div class="metrics" id="metrics"></div>
<table>
<thead>
<tr><th>ID</th><th>Category</th><th>Question</th><th>Answer</th>
<th>Retrieved sources</th><th>Citations</th><th>Confidence</th></tr>
</thead>
<tbody id="rows"></tbody>
</table>
<script>
const DATA = {payload};

function esc(s) {{
  return String(s).replace(/[&<>"']/g, function (ch) {{
    return {{'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}}[ch];
  }});
}}

function verdict(applicable, correct) {{
  if (!applicable) return '<span class="na">n/a</span>';
  return correct ? '<span class="ok">pass</span>' : '<span class="bad">fail</span>';
}}

function render(strategy) {{
  const d = DATA[strategy];
  const m = d.metrics;
  document.getElementById('metrics').innerHTML =
    '<span>Retrieval: ' + (m.retrieval_hit_rate * 100).toFixed(0) + '%</span>' +
    '<span>Answer: ' + (m.answer_correct_rate * 100).toFixed(0) + '%</span>' +
    '<span>Citations: ' + (m.citation_valid_rate * 100).toFixed(0) + '%</span>' +
    '<span>Refusal: ' + (m.refusal_correct_rate * 100).toFixed(0) + '%</span>';

  document.getElementById('rows').innerHTML = d.cases.map(function (c) {{
    return '<tr>' +
      '<td>' + esc(c.id) + '</td>' +
      '<td>' + esc(c.category) + '</td>' +
      '<td>' + esc(c.question) + '</td>' +
      '<td>' + esc(c.answer) + '</td>' +
      '<td>' + esc(c.retrieved_sources.join(', ')) + '</td>' +
      '<td>' + verdict(c.citation_applicable, c.citations_valid) + '</td>' +
      '<td>' + c.confidence.toFixed(2) + '</td>' +
    '</tr>';
  }}).join('');
}}

document.getElementById('strategy').addEventListener('change', function (e) {{
  render(e.target.value);
}});
render('{default_strategy}');
</script>
</body>
</html>
"""
