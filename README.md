# RAG & Agent Systems

> Five AI applications built the way a team would actually ship them with citations you can verify, permissions on tools, and honest answers when the system doesn't know.

I'm a Computer Engineering grad finishing a Master of Business Analytics, aiming at AI engineering roles. The gap I kept hitting in tutorials: plenty show you how to *call* a model, almost none show you how to *run* one. So I set a harder brief , build the systems that sit around the model, the way an internal team would.

A RAG demo is a weekend. A RAG system you'd let customers touch is a different problem: hybrid retrieval so exact error codes still match, verified citations so answers can be defended, drift monitoring so stale docs get caught, human approval before an agent does anything risky, and graceful "I couldn't find that" handling.

## The projects

| # | Project | What it demonstrates |
|---|---------|----------------------|
| 1 | [Support Knowledge Copilot](./01-support-knowledge-copilot) | RAG · hybrid retrieval (dense + BM25 + RRF) · citation verification · retrieval evals |
| 2 | [RAG Freshness & Drift Monitor](./07-rag-freshness-monitor) | Data quality · knowledge drift · index monitoring |
| 3 | [Permissioned Agent Sandbox](./06-agent-sandbox) | Agents · tool use · human-in-the-loop · audit logging |
| 4 | [Natural Language to API Assistant](./08-nl-to-api-assistant) | Tool calling · OpenAPI planning · dry-runs and confirmation |
| 5 | [Multimodal Document Reviewer](./09-multimodal-doc-reviewer) | Multimodal · OCR with vision fallback · structured extraction |

Each folder is a standalone service with its own README, tests, Dockerfile, and architecture note.

## How I built this (and why I'm telling you)

These projects are **built by an automated pipeline I designed**, not typed line by line. A GitHub Actions workflow runs daily: it reads `ROADMAP.md`, picks up the next chunk of work, implements it with Claude, then runs `ruff` and `pytest` as an independent CI gate. Tests fail, nothing merges. Tests pass, it opens a PR and merges it.

I'm putting that up front because I think it's the most interesting thing here. The specs, architecture decisions, roadmap and quality gates are mine — the typing is automated. Working *with* agents and building guardrails so their output is trustworthy is the job now, and this repo is me practising that on five real systems instead of talking about it.

The pipeline: [`.github/workflows/claude-builder.yml`](./.github/workflows/claude-builder.yml)

## Running any of them

Everything runs offline with no API keys — embeddings and LLM calls fall back to deterministic stubs, so `pytest` passes on a clean clone. Add real provider keys in `.env` for full behaviour.

```bash
cd 01-support-knowledge-copilot
python -m venv .venv && .venv\Scripts\activate     # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
uvicorn app.main:app --reload                       # http://127.0.0.1:8000/docs
```

Try `POST /ask` with `{"question": "What does error 429 mean?"}` — you'll get an answer with citations, a confidence breakdown, and the retrieved chunks.

## Stack

Python 3.11 · FastAPI · Pydantic v2 · pytest + ruff · Docker · GitHub Actions

## Progress

[`ROADMAP.md`](./ROADMAP.md) is the live status and updates itself as the builder works through the list.

---
