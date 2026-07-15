# P11: AI Trace Explorer for LLM Workflows

**Topic:** LLMOps, Observability, Tracing, Debugging, Evals

## What you're building

An observability tool for multi-step LLM workflows. It records every prompt, model response, tool call, retrieved context, validation result, latency, cost, and error, then displays the full execution trace so engineers can debug failures quickly.

## Why this project lands interviews

> When a workflow breaks, you need traces, not guesses. This build helps you explain how to debug retrieval, prompts, tools, validation, and generation step by step.

## Tech stack

| Component | Tool / Library |
|-----------|----------------|
| Language | Python 3.11+ |
| Workflow | Custom pipeline or LangGraph |
| Tracing | OpenTelemetry + custom spans |
| Storage | PostgreSQL + JSON blobs |
| LLM Provider | OpenAI / Anthropic / local |
| UI | Streamlit or React |
| Metrics | Prometheus optional |
| Containerization | Docker Compose |

## Build phases

### Phase 1: Build a Multi-Step AI Workflow (Day 1-3)

- Choose a workflow: Example: intake a support ticket, classify it, retrieve relevant docs, draft a response, validate the response, and create an internal note.
- Make every step typed: Use Pydantic models for each step's input and output. Tracing is much easier when step boundaries are clean.
- Add controlled failure cases: Include bad retrieval, malformed JSON, low-confidence classification, and failed validation examples.

### Phase 2: Instrument the Workflow (Day 3-6)

- Create a trace ID per run: Every workflow execution gets a unique trace ID and a list of spans.
- Wrap each step in a tracing decorator: Capture step name, input, output, prompt, model, token usage, latency, cost, status, and errors.
- Capture artifacts: Store retrieved chunks, tool arguments, validation failures, and retry attempts as structured artifacts.

### Phase 3: Add Failure Classification (Day 6-8)

- Define failure categories: Retrieval miss, prompt failure, schema failure, tool error, hallucination, unsupported citation, timeout, and policy violation.
- Classify failed runs: Use rules first, then an LLM judge for nuanced cases. Store both category and evidence.
- Add root-cause hints: Suggest likely fixes: adjust chunking, add eval case, tighten schema, change prompt, or add retry.

### Phase 4: Build the Trace Explorer UI (Day 8-11)

- Show a timeline: Display each step in order with status, latency, cost, and short summary.
- Add expandable details: Clicking a step reveals input, output, prompt, raw response, and artifacts.
- Add diff views: Compare successful and failed runs of the same workflow to spot where behavior diverged.

### Phase 5: Build Metrics and Feedback Loop (Day 11-13)

- Aggregate reliability metrics: Track failure rate by step, average cost per workflow, P95 latency, retry rate, and most common failure category.
- Turn failures into eval cases: Let a user mark a trace as a regression and export it into your eval dataset.
- Add alerts: Trigger Slack alerts when a step's failure rate rises above threshold.

### Phase 6: Polish for Portfolio (Day 13-14)

- Demo a failure diagnosis: Run a workflow that produces a bad answer, open the trace, identify the broken step, and export it to evals.
- Write the narrative: Frame it as "debugging infrastructure for AI workflows," which is much stronger than calling it a dashboard.

## Interview talking point

> A trace should not only say that the final answer was bad. It should show the exact intermediate decision that made it bad.

## Status

Planned. Scaffold pending — see root `ROADMAP.md`.
