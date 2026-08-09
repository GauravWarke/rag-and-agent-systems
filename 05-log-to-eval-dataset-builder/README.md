# P5: Production Log-to-Eval Dataset Builder

**Topic:** Evals, Data Flywheel, LLMOps, Human Review

## What you're building

A pipeline that mines production-like LLM logs, finds useful examples, converts them into evaluation cases, labels them with expected behavior or rubrics, and sends uncertain cases to a human review queue.

## Why this project lands interviews

> The hard part of evals is often the dataset. Here you build a pipeline that turns real interactions into test cases, with review steps so the dataset does not rot.

## Tech stack

| Component | Tool / Library |
|-----------|----------------|
| Language | Python 3.11+ |
| Log Store | PostgreSQL or DuckDB |
| Embeddings | sentence-transformers / OpenAI embeddings |
| Clustering | HDBSCAN or scikit-learn |
| Labeling | LLM-as-judge + custom rubrics |
| Review UI | Streamlit |
| Scheduler | Celery beat or cron |
| Eval Format | JSONL |
| Containerization | Docker Compose |

## Build phases

### Phase 1: Design the Log Schema (Day 1-2)

- Define the unified log format: Capture prompt, system prompt, response, model, feature name, latency, token counts, user feedback, retry count, error status, and timestamp.
- Add privacy controls: Build redaction rules for emails, phone numbers, secrets, and names. Store both redaction status and redaction method.
- Seed synthetic logs: Create 1,000 simulated logs across a few features. Include good responses, bad responses, user retries, malformed outputs, and safety edge cases.

### Phase 2: Sample and Classify Interactions (Day 2-5)

- Build sampling modes: Implement random sampling, failure-biased sampling, and diversity sampling. Failure-biased sampling should over-select logs with negative feedback, retries, or errors.
- Cluster prompts: Embed prompts and cluster them to discover common categories. Give each cluster a human-readable label using representative examples.
- Identify high-value candidates: Prioritize unusual prompts, low-quality outputs, high-impact features, edge cases, and clusters with poor eval coverage.

### Phase 3: Auto-Generate Eval Labels (Day 5-8)

- Decide eval type per example: Some examples need a golden answer. Others need a rubric. Some need expected refusal. Pick the label type based on the interaction.
- Generate labels with confidence: Use a strong model to propose expected behavior, key assertions, forbidden assertions, and scoring rubric. Run multiple passes for important examples.
- Deduplicate aggressively: Compare against existing eval cases and skip near-duplicates. Track why each candidate was accepted or rejected.

### Phase 4: Build Human Review (Day 8-10)

- Create a review queue: Low-confidence labels go to reviewers. Show the original interaction, proposed labels, similar existing cases, and quick approve/edit/reject actions.
- Track reviewer edits: Store what changed and why. Use this to improve labeling prompts and measure auto-label quality.
- Add dataset status: Every eval case should be draft, approved, rejected, or deprecated. This prevents messy datasets.

### Phase 5: Connect to an Eval Runner (Day 10-12)

- Export approved cases to JSONL: Keep the output format simple: input, expected behavior, rubric, tags, difficulty, source cluster, and date added.
- Run nightly evals: Execute the growing dataset against a model endpoint and compare performance to the previous run.
- Track dataset health: Show total cases, cases by category, cases by difficulty, freshness, auto-labeled percentage, and human-reviewed percentage.

### Phase 6: Polish for Portfolio (Day 12-14)

- Show the flywheel: Demo logs entering the system, candidates being selected, labels being generated, humans approving, and the eval dataset growing.
- Use dataset numbers: Example: "Generated 300 approved eval cases across 12 categories from 5,000 simulated production logs, with 82% auto-label acceptance after review."

## Interview talking point

> Explain that a good eval set should not mirror traffic perfectly. It should over-represent risk, failures, and edge cases because those are where regressions hurt.

## Running locally

```bash
pip install -r requirements-dev.txt
cp .env.example .env  # optional: only needed to enable OPENAI_API_KEY label generation
uvicorn app.main:app --reload
```

Then seed some synthetic logs and explore:

```bash
curl -s -X POST localhost:8000/v1/logs/seed -H 'content-type: application/json' -d '{"n": 1000, "seed": 42}'
curl -s localhost:8000/v1/clusters
curl -s localhost:8000/v1/candidates
```

Everything runs offline by default (deterministic hashed-embedding stub, heuristic label
client). Set `OPENAI_API_KEY` in `.env` to switch label generation to a real model.

## Status

Phases 1-3 implemented (log schema + redaction + synthetic seeding, sampling + clustering +
candidate scoring, auto-label generation + dedup). Phases 4-6 (human review queue, eval
runner integration, portfolio polish) are still pending — see root `ROADMAP.md`.
