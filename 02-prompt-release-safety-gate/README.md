# P2: Prompt Release Safety Gate

**Topic:** LLMOps, PromptOps, CI/CD, Regression Testing, Evals

## What you're building

A CI/CD safety gate for prompt changes. Whenever a prompt file changes in a pull request, the system runs a regression suite, compares the new prompt against the current production prompt, and blocks release if quality, cost, latency, or safety metrics degrade beyond a threshold.

## Why this project lands interviews

> Interviewers care less about a clever prompt and more about how it is shipped safely. This build gives you a clean story around prompt versioning, test data, release gates, and rollback.

## Tech stack

| Component | Tool / Library |
|-----------|----------------|
| Language | Python 3.11+ |
| Prompt Format | YAML |
| Structured Output | Pydantic |
| LLM Provider | OpenAI / Anthropic / local model |
| Eval Runner | Custom + DeepEval |
| Storage | SQLite + JSON artifacts |
| CI/CD | GitHub Actions |
| Reporting | Markdown + HTML report |
| Alerting | Slack webhook |

## Build phases

### Phase 1: Pick the AI Feature Under Test (Day 1-2)

- Build a small production-like feature: Create an AI feature such as "turn messy customer notes into a clean CRM summary." The output should be structured: summary, sentiment, next action, urgency, and confidence.
- Store prompts as versioned YAML: Put prompts in /prompts. Each file should include version, owner, description, model settings, system prompt, few-shot examples, and expected output schema.
- Define the response contract: Use Pydantic to validate the output. A prompt that returns beautiful prose but breaks the schema should fail the release gate.

### Phase 2: Build the Golden Test Set (Day 2-4)

- Hand-write realistic examples: Create 75-100 messy notes with expected structured outputs. Include spelling mistakes, vague requests, emotional customers, missing context, and mixed-intent notes.
- Label edge cases clearly: Add fields like difficulty, risk_area, and why_this_case_exists. These notes make your dataset feel intentionally designed instead of randomly generated.
- Version the dataset: Store it in JSONL with stable IDs. When you update the dataset, write a changelog. This shows that the eval bar is managed too, not treated as a one-time file.

### Phase 3: Build the Regression Runner (Day 4-7)

- Run baseline and candidate prompts: For every test case, call the production prompt and the changed prompt. Store raw outputs, parsed outputs, latency, token counts, and model errors.
- Score multiple dimensions: Measure schema validity, field-level correctness, summary relevance, next-action usefulness, safety issues, latency, and cost. Do not collapse everything into one vague score too early.
- Compare run-over-run: Identify cases that passed before but fail now, cases that improved, categories that regressed, and cost/latency changes. This diff is the core value of the project.
- Add thresholds: Create warning and blocking thresholds. Example: block if schema validity drops by more than 2%, safety failures increase, or average cost rises by more than 20%.

### Phase 4: Build Reports and PR Comments (Day 7-9)

- Generate a release report: Include a scorecard, regression table, examples of changed outputs, cost delta, latency delta, and recommended release decision.
- Add side-by-side output diffs: For every failed case, show input, baseline output, candidate output, expected output, and the scoring explanation.
- Post a PR comment: The GitHub Action should post a short summary: pass/warn/fail, top regressions, metric deltas, and a link to the full report artifact.

### Phase 5: Wire into CI/CD (Day 9-11)

- Trigger only when prompts change: Configure GitHub Actions to run when files under /prompts or /evals change. Keep the workflow efficient.
- Block risky merges: If the result is critical, exit non-zero so the PR cannot merge. If it is warning-only, allow merge but leave a visible warning.
- Package the runner: Add a Dockerfile so the same runner works locally and in CI. Expose environment variables for API keys, thresholds, and model choice.

### Phase 6: Polish for Portfolio (Day 11-12)

- Create a demo PR: Intentionally change a prompt so it gets more verbose, more expensive, or less accurate. Show the safety gate catching it.
- Write your README like team documentation: Include setup, how to add test cases, how to adjust thresholds, and what decisions you made around LLM-as-judge scoring.

## Interview talking point

> Say that the dataset is the real product here. The CI runner is useful, but the human-curated edge cases are what make the eval meaningful.

## Running it

```bash
pip install -r requirements-dev.txt
uvicorn app.main:app --reload   # POST /summarize {"note": "..."}
pytest -q
ruff check .
```

The feature under test is a CRM note summarizer: `POST /summarize` turns a
messy customer note into a structured `NoteSummary` (summary, sentiment,
next_action, urgency, confidence). Prompts are versioned YAML files in
`/prompts` (`crm_summary_v1` is the production baseline, `crm_summary_v2` is
a verbose candidate used to exercise the regression runner). Generation
defaults to a deterministic, keyless rule-based stub
(`app/generation/summarizer.py`) so the whole pipeline runs offline; set
`GENERATION_MODEL` and implement `_generate_llm` to call a real provider.

The golden test set (`data/golden_test_set.jsonl`, 75 hand-written cases,
changelog in `data/CHANGELOG.md`) and the regression runner
(`app/eval/runner.py`, `app/eval/comparison.py`, `app/eval/thresholds.py`)
run both prompt versions over every case, score schema validity, field
correctness, summary relevance, next-action usefulness, safety issues,
latency, and cost, and turn a run-over-run comparison into a pass/warn/block
gate decision.

### Running the release gate

```bash
python gate.py --baseline crm_summary_v1 --candidate crm_summary_v2 --out reports/
```

This runs the full regression suite for both prompts and writes two files
to `reports/`:

- `release_report.md` — the full reviewer artifact: scorecard, run-over-run
  deltas, newly-failing/newly-passing cases, regressed/improved categories,
  and a side-by-side diff (input, baseline output, candidate output,
  expected output, and why it failed) for every case that fails on the
  candidate prompt.
- `pr_comment.md` — a short summary (pass/warn/block, metric deltas, top
  regressions, and a link to the full report if `--report-url` is passed)
  suitable for posting as a PR comment.

The command exits `1` when the gate decision is `block` (so a CI job can
fail the PR) and `0` for `pass` or `warn` (so warnings surface without
blocking the merge). Thresholds come from `app/core/config.py` /
`.env` (`SCHEMA_VALIDITY_DROP_BLOCK_PCT`, `COST_INCREASE_BLOCK_PCT`,
`LATENCY_INCREASE_WARN_PCT`), or can be overridden per-run via
`evaluate_gate(...)` kwargs.

### CI/CD wiring

`.github/workflows/prompt-release-gate.yml` runs the gate on every pull
request that touches `prompts/`, `data/`, or `app/eval/` in this project:
it runs `gate.py`, uploads `reports/` as a build artifact, and posts (or
updates) a PR comment with the short summary. If the gate decision is
`block`, the job fails and the PR cannot merge; a `warn` decision still
passes the job but the comment surfaces the warning. The same `gate.py`
entry point runs unchanged locally, in CI, or via
`docker compose --profile gate run gate-runner` (the `Dockerfile` bundles
`gate.py` alongside the API); model choice, prompt names, and thresholds
are all environment variables, never hardcoded.

## Status

In progress — Phases 1-5 done (feature + versioned prompts + response
contract, golden test set, regression runner with scoring/comparison/gate
thresholds, release reports + PR comments, CI/CD wiring). Phase 6
(portfolio polish) remains. See root `ROADMAP.md`.
