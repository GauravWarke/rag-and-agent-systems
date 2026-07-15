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

## Status

Planned. Scaffold pending — see root `ROADMAP.md`.
