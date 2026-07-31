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

### Demo: the gate catching a bad prompt change

`prompts/crm_summary_v2.yaml` is a deliberately-regressed candidate: it
asks the model for a longer, more thorough summary, which raises token
count (and therefore cost) without improving accuracy. Running the gate
against it reproduces exactly the "bad PR" scenario the safety gate
exists to catch:

```bash
python gate.py --baseline crm_summary_v1 --candidate crm_summary_v2 --out reports/
```

```
Wrote reports/release_report.md and reports/pr_comment.md
Gate decision: block
  - average cost rose 21.40%, exceeding the 20.00% block threshold
```

The command exits `1`, so a CI job running this on a pull request that
changed `prompts/crm_summary_v2.yaml` would fail the check and block the
merge. `reports/pr_comment.md` holds the short summary a bot would post
on the PR; `reports/release_report.md` holds the full scorecard, deltas,
and a side-by-side diff for every case that fails on the candidate. This
exact scenario is asserted in
`tests/test_gate_cli.py::test_gate_cli_blocks_on_regressed_candidate` so
the demo can't silently regress. `reports/` is git-ignored (it's a build
artifact, not source) — regenerate it locally with the command above.

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

## Team documentation

### How to add a test case

1. Append a line to `data/golden_test_set.jsonl` with a stable, unused
   `id` (next free `cNNN`), the raw `note` text, a `category`, a
   `difficulty` (`easy`/`medium`/`hard`), a `risk_area`
   (`billing`/`product`/`product_bug`/`churn`/`safety`/`compliance`/`none`),
   `why_this_case_exists`, and an `expected` block (`sentiment`, `urgency`,
   `next_action_keywords`, `summary_keywords`) — see
   `app/eval/dataset.py::GoldenCase` for the schema.
2. Add an entry to `data/CHANGELOG.md` describing what was added or
   changed and why, under a new version heading. The dataset is a managed
   artifact, not a one-off fixture — every edit gets a changelog line.
3. Never reuse or renumber an existing `id`; if a case is fully replaced
   rather than tweaked, retire the old id in the changelog and add a new
   one instead. Existing tests and past reports may reference IDs.
4. Run `python gate.py --baseline crm_summary_v1 --candidate crm_summary_v1
   --out /tmp/gate-check` to sanity-check the new case parses and scores
   before relying on it for a real prompt comparison.

### How to adjust thresholds

Thresholds live in `app/core/config.py` (`Settings`) and are read from
environment variables / `.env`, never hardcoded in the gate logic itself
(`app/eval/thresholds.py::evaluate_gate`):

| Env var | Default | Effect |
|---|---|---|
| `SCHEMA_VALIDITY_DROP_BLOCK_PCT` | `2.0` | Block if schema-valid-output rate drops more than this many points. |
| `COST_INCREASE_BLOCK_PCT` | `20.0` | Block if average per-case cost rises more than this percent. |
| `LATENCY_INCREASE_WARN_PCT` | `20.0` | Warn (does not block) if average latency rises more than this percent. |

A safety-failure increase of any size always blocks — that threshold is
intentionally not configurable. `evaluate_gate(...)` also accepts these as
keyword overrides for one-off local experiments without touching env
config. Prefer widening a threshold only with a written reason (e.g. in
the PR description), since these numbers are the actual release policy.

### Decisions around LLM-as-judge scoring

V1 deliberately does **not** use an LLM judge. `app/eval/scoring.py` scores
every dimension with rule-based checks instead: exact-match on
`sentiment`/`urgency`, keyword containment for summary relevance and
next-action usefulness, and regex detection for unredacted PII
(SSN/credit-card-shaped strings) as the safety check. Reasons:

- **Determinism.** The regression runner's whole value proposition is a
  stable pass/fail signal in CI. An LLM judge adds run-to-run variance
  that would produce flaky gate decisions — exactly the failure mode a
  release gate must not have.
- **No extra keyless-offline dependency.** The project runs fully offline
  by default (`app/generation/summarizer.py` is a deterministic stub); a
  judge model would require an API key or a second local model just to
  run tests and CI.
- **Cost and latency.** Judging 75+ cases per prompt version, on every
  prompt-touching PR, roughly doubles LLM spend and CI wall time for
  marginal signal on a narrow, well-specified schema where exact/keyword
  matching is already a good proxy.

This is a V1 tradeoff, not a permanent one: `summary_relevance` and
`next_action_useful` are the two dimensions where keyword containment is
the weakest proxy (a correct summary can miss the exact keyword; a
verbose one can include it without being useful — see the v2 demo above).
The natural extension is an optional LLM-judge pass behind a
`JUDGE_MODEL` env var, used for those two dimensions only, sampled rather
than run on every case, with the rule-based score kept as the offline
fallback so CI never depends on a live model call.

## Status

Done — all 6 phases complete (feature + versioned prompts + response
contract, golden test set, regression runner with scoring/comparison/gate
thresholds, release reports + PR comments, CI/CD wiring, portfolio
polish). See root `ROADMAP.md`.
