# RAG & Agent Systems

> Five AI applications built the way a team would actually ship them: citations you can check, permissions on tools, and a straight answer when the system doesn't know.

I'm doing a Master of Business Analytics, with a Computer Engineering degree behind me. Most of my coursework asks what a model predicts. Sitting in those classes I kept circling a different question: what has to be true before anyone acts on what it says?

That's less about accuracy than about trust. Can I trace this answer back to a source? What happens when the documents underneath go stale? Who signs off before an agent does something expensive? Analytics work lives or dies on whether someone believes the output enough to make a decision with it. AI systems are no different.

So I built the parts that decide that. A RAG demo takes a weekend. A RAG system you'd let a customer touch is a different animal: hybrid retrieval so exact error codes still match, citations checked against their sources, drift monitoring that catches stale docs before a user does, human approval on risky actions, and a clean "I couldn't find that" instead of a confident guess.

## The projects

| # | Project | What it demonstrates |
|---|---------|----------------------|
| 1 | [Support Knowledge Copilot](./01-support-knowledge-copilot) | RAG · hybrid retrieval (dense + BM25 + RRF) · citation verification · retrieval evals |
| 2 | [RAG Freshness & Drift Monitor](./07-rag-freshness-monitor) | Data quality · knowledge drift · index monitoring |
| 3 | [Permissioned Agent Sandbox](./06-agent-sandbox) | Agents · tool use · human-in-the-loop · audit logging |
| 4 | [Natural Language to API Assistant](./08-nl-to-api-assistant) | Tool calling · OpenAPI planning · dry-runs and confirmation |
| 5 | [Multimodal Document Reviewer](./09-multimodal-doc-reviewer) | Multimodal · OCR with vision fallback · structured extraction |

Each folder is a standalone service with its own README, tests, Dockerfile, and architecture note.

## How I built this, and why I'm saying so

The code here is written by an automated pipeline I set up, not typed line by line. A GitHub Actions workflow runs on a schedule. It reads `ROADMAP.md`, builds the next piece with Claude, then runs `ruff` and `pytest` as a gate it cannot skip. Failing tests, nothing merges. Passing tests, it opens a PR and merges itself.

I lead with that because it's the most interesting thing I learned. Deciding what to build, how the pieces fit, and what has to pass before anything ships was the real work. The typing wasn't. Getting something dependable out of a coding agent turns out to be a design problem, and I'd rather show you how I handled it than claim I hand-wrote every file.

The pipeline: [`.github/workflows/claude-builder.yml`](./.github/workflows/claude-builder.yml)

## Running any of them

Everything runs offline without API keys. Embeddings and model calls fall back to deterministic stubs, so `pytest` passes on a fresh clone. Add real provider keys in `.env` when you want full behaviour.

```bash
cd 01-support-knowledge-copilot
python -m venv .venv && .venv\Scripts\activate     # macOS/Linux: source .venv/bin/activate
pip install -r requirements-dev.txt
pytest -q
uvicorn app.main:app --reload                       # http://127.0.0.1:8000/docs
```

Send `POST /ask` a question like `{"question": "What does error 429 mean?"}` and you get back the answer, the chunks it came from, a confidence breakdown, and anything it couldn't verify.

## Stack

Python 3.11 · FastAPI · Pydantic v2 · pytest + ruff · Docker · GitHub Actions

## Progress

[`ROADMAP.md`](./ROADMAP.md) tracks what's done and what's queued. The builder updates it as it goes.

---
