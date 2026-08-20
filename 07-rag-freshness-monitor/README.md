# P7: RAG Freshness and Drift Monitor

**Topic:** RAG, Data Quality, Monitoring, Knowledge Drift

## What you're building

A monitoring system that watches a RAG knowledge base for stale documents, changed source content, retrieval drift, missing coverage, and outdated answers. It tells the team when the index needs rebuilding or when answers are becoming less trustworthy.

## Why this project lands interviews

> RAG does not end after indexing. This build covers the maintenance work: stale sources, retrieval drift, answer drift, and re-index triggers.

## Tech stack

| Component | Tool / Library |
|-----------|----------------|
| Language | Python 3.11+ |
| Source Watcher | Git diff / filesystem watcher |
| Embeddings | OpenAI or sentence-transformers |
| Vector Store | Qdrant / ChromaDB |
| Scheduler | Cron / Celery beat |
| Eval Runner | Custom RAG evals |
| Storage | SQLite or PostgreSQL |
| Dashboard | Streamlit |
| Containerization | Docker |

## Build phases

### Phase 1: Build a Baseline RAG Index (Day 1-3)

- Create a small knowledge base: Use internal-doc-style Markdown files: policies, product pages, troubleshooting docs, and changelogs.
- Index documents with metadata: Store document version, last modified date, source path, section heading, chunk hash, and embedding version.
- Save an index manifest: The manifest records what was indexed, when, with which embedding model, and with which chunking strategy.

### Phase 2: Detect Source-Level Freshness Issues (Day 3-5)

- Track content changes: Compare current document hashes to the manifest. Detect added, removed, and modified sections.
- Score semantic change: A one-word typo should not trigger panic. Compute semantic similarity between old and new sections to estimate how meaningful the change is.
- Prioritize re-indexing: Flag high-impact changes first: pricing, policy, API behavior, troubleshooting steps, and security instructions.

### Phase 3: Detect Retrieval Drift (Day 5-8)

- Build a probe question set: Create 50 recurring questions tied to known source sections.
- Run probes against old and new indexes: Compare which chunks are retrieved and whether the top result changes after document updates.
- Flag suspicious changes: If a known question no longer retrieves the expected section, mark it as retrieval drift.

### Phase 4: Detect Answer Drift (Day 8-10)

- Generate answers for probe questions: Run the same questions through the RAG pipeline over time.
- Compare answers semantically: Use LLM-as-judge to identify whether the answer meaning changed, whether the change was expected, and whether citations still support the answer.
- Track stale answer risk: If source docs changed but generated answers did not, the system may be serving stale knowledge. Flag this clearly.

### Phase 5: Build Alerts and Dashboard (Day 10-12)

- Build freshness scorecards: Show docs changed, chunks stale, probes drifting, answer drift, and re-index recommendations.
- Add alerts: Send Slack notifications when high-risk docs changed without re-indexing, or when probe questions fail.
- Add one-click rebuild command: From the dashboard, trigger re-indexing for affected docs and rerun probe tests.

### Phase 6: Polish for Portfolio (Day 12-14)

- Demo a stale doc scenario: Change a policy document, show the system detecting risk, rebuild the index, and show probes returning to healthy.
- Write the narrative: Frame it as "monitoring for knowledge freshness in RAG systems." Most candidates do not have this lifecycle angle.

## Interview talking point

> Explain that not all document changes are equal. A production system should prioritize re-indexing based on user impact instead of file modification time alone.

## Quickstart

```bash
cd 07-rag-freshness-monitor
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

```bash
curl -X POST localhost:8000/v1/index/build      # build & save the manifest from data/docs
curl localhost:8000/v1/index/manifest           # inspect what was indexed
curl -X POST localhost:8000/v1/freshness/scan   # diff the corpus against the manifest, with priority
curl -X POST localhost:8000/v1/probes/run       # run the probe set, saved as the drift baseline
curl -X POST localhost:8000/v1/probes/drift     # re-run probes and compare to that baseline
curl -X POST localhost:8000/v1/answers/run      # generate answers for the probe set, saved as the answer baseline
curl -X POST localhost:8000/v1/answers/drift    # re-run answers and compare meaning to that baseline
curl -X POST localhost:8000/v1/answers/stale-risk  # flag probes whose source changed but answer didn't
curl localhost:8000/v1/scorecard                # roll everything up into one dashboard summary
curl -X POST localhost:8000/v1/alerts/check     # recompute the scorecard and dispatch any alerts it trips
curl -X POST localhost:8000/v1/rebuild          # one-click: re-index, re-run probes/answers, alert
```

Everything runs offline by default: embeddings use a deterministic hashed
bag-of-words stub (`app/indexing/embeddings.py`, `EMBEDDING_MODEL=stub`) so
the full pipeline — indexing, freshness diffing, probe drift, answer
generation, answer drift, and alerting — works with no API keys or webhook.
Set `OPENAI_API_KEY` to swap in the real answer generator and judge, and
`SLACK_WEBHOOK_URL` to swap in real Slack alerts.

## Status

In progress — Phases 1-5 of 6 implemented:

- **Phase 1 — Baseline RAG Index:** A small Markdown corpus lives in
  `data/docs/` (policies, product, troubleshooting, changelog — 16 sections
  total), with per-file `doc_type` and `last_modified` metadata in
  `data/docs_meta.json`. `app/indexing/chunker.py` splits each file into
  heading-based sections with a stable `<doc-stem>::<heading-slug>` chunk
  ID and a content hash. `app/indexing/manifest.py` builds an
  `IndexManifest` (created-at timestamp, embedding model/version, chunking
  strategy, and every chunk) and saves/loads it as JSON.
- **Phase 2 — Source-Level Freshness Issues:** `app/freshness/diff.py`
  compares a fresh scan of `data/docs/` to the saved manifest and reports
  added, removed, and modified sections by chunk hash, plus a 0-1 semantic
  change score (cosine distance over the stub embedder) so a one-word edit
  doesn't read the same as a rewritten section. `app/freshness/priority.py`
  ranks changes as `critical` / `high` / `medium` / `low` using impact
  keywords (security, pricing, policy, API, troubleshooting, ...) and
  demotes changes below the semantic-change threshold to `low` even if a
  keyword matched.
- **Phase 3 — Retrieval Drift:** `data/probes.json` holds 20 recurring
  questions tied to known chunk IDs across all 16 sections.
  `app/drift/retriever.py` is a minimal top-1 cosine retriever over the
  stub embedder, and `app/drift/probes.py` runs the probe set
  (`run_probes`) and compares two runs (`compare_runs`) to flag probes
  whose top retrieved chunk changed, or that stopped matching their
  expected section.
- **Phase 4 — Answer Drift:** `app/answers/generator.py` generates a
  grounded, citation-tagged answer per probe (`StubAnswerGenerator` is a
  deterministic offline extractive generator; `OpenAIAnswerGenerator` is
  the real-model path behind `OPENAI_API_KEY`). `app/answers/judge.py` is
  an LLM-as-judge that compares two answers for the same probe and
  decides whether the meaning changed and whether the citation still
  supports the answer (`StubAnswerJudgeClient` uses cosine similarity
  over the stub embedder offline; `OpenAIAnswerJudgeClient` is the real
  path). `app/answers/drift.py` compares two answer runs
  (`compare_answer_runs`) and cross-references a freshness diff against
  answer drift to flag stale-answer risk (`detect_stale_answer_risk`):
  probes whose grounding chunk changed but whose answer did not.
- **Phase 5 — Alerts and Dashboard:** `app/dashboard/scorecard.py` rolls up
  docs changed, chunks needing re-index, probes drifting, answer drift, and
  stale-answer risk into one `FreshnessScorecard`, built from whichever
  snapshots are available so it degrades gracefully before the full
  pipeline has been run. `app/alerts/rules.py` turns a scorecard into
  plain-English alert messages (high-priority doc changes needing
  re-index, drifting probes, stale-answer risk), and
  `app/alerts/dispatch.py` sends them through `app/alerts/client.py`:
  `NullAlertClient` records alerts locally by default, and
  `SlackAlertClient` posts to a real incoming webhook behind
  `SLACK_WEBHOOK_URL`. `POST /v1/rebuild` is the one-click rebuild: it
  re-indexes the corpus, re-runs the probe and answer baselines against
  the fresh index, recomputes the scorecard, and dispatches any alerts it
  trips — all in one call.
- **API:** `POST /v1/index/build`, `GET /v1/index/manifest`,
  `POST /v1/freshness/scan`, `POST /v1/probes/run`,
  `POST /v1/probes/drift`, `POST /v1/answers/run`,
  `POST /v1/answers/drift`, `POST /v1/answers/stale-risk`,
  `GET /v1/scorecard`, `POST /v1/alerts/check`, and `POST /v1/rebuild`,
  all behind a per-client rate limiter (`app/core/rate_limit.py`).

Remaining: Phase 6 (portfolio polish — demo recording and case-study
narrative) — see root `ROADMAP.md`.
