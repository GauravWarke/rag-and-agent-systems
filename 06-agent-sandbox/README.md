# P6: Permissioned Tool-Using Agent Sandbox

**Topic:** Agents, Tool Use, Security, Human-in-the-Loop, Observability

## What you're building

A controlled agent environment where an LLM can use tools like file search, calculators, API calls, and database queries - but every tool has permissions, rate limits, audit logs, and human approval for sensitive actions.

## Why this project lands interviews

> Instead of a flashy agent demo, this one focuses on permissions, approvals, tool logs, and clear failure handling. Those are the parts teams worry about.

## Tech stack

| Component | Tool / Library |
|-----------|----------------|
| Language | Python 3.11+ |
| Orchestration | LangGraph |
| Tool Schemas | Pydantic |
| API | FastAPI |
| Queue | Redis + Celery |
| Storage | PostgreSQL |
| UI | Streamlit or React |
| Observability | OpenTelemetry |
| Containerization | Docker Compose |

## Build phases

### Phase 1: Design the Agent and Tool Model (Day 1-3)

- Define the agent role: Build a "workspace assistant" that can answer questions, inspect files, summarize data, call safe APIs, and prepare actions for approval.
- Create a tool registry: Every tool has name, description, input schema, output schema, allowed roles, rate limit, risk level, and whether approval is required.
- Build safe starter tools: Add calculator, file reader over a sandbox folder, web-search stub or mock search, CSV query tool, and ticket creation mock API.

### Phase 2: Build Permission Checks (Day 3-5)

- Add user and role permissions: Users have roles like viewer, analyst, operator, and admin. Tools check permissions before execution.
- Add risk levels: Low-risk tools execute immediately. Medium-risk tools require confirmation. High-risk tools require human approval before execution.
- Block invalid tool inputs: Validate every tool call with Pydantic. Never let raw model text become a command without validation.

### Phase 3: Build the LangGraph Workflow (Day 5-8)

- Create graph nodes: Intake, plan, tool selection, permission check, tool execution, result reflection, approval wait, final response.
- Add conditional routing: If permission fails, return a safe explanation. If approval is needed, pause the task. If a tool fails, let the agent retry with a safer alternative.
- Store task state: Persist every step so a paused task can resume after human approval.

### Phase 4: Build Human Approval (Day 8-10)

- Create an approval queue: Show proposed action, tool name, arguments, risk level, model reasoning summary, and expected effect.
- Add approve / reject / modify: A human can approve as-is, edit the tool arguments, reject, or ask the agent to re-plan.
- Log decisions: Store who approved, what changed, and why. This keeps the agent auditable.

### Phase 5: Build Observability (Day 10-12)

- Trace every decision: Capture prompts, chosen tools, permission decisions, tool outputs, retries, approval events, latency, and cost.
- Build a trace viewer: Show the workflow as a timeline. Clicking a step reveals inputs, outputs, and decision reasons.
- Add safety analytics: Track tool usage, blocked attempts, approval rate, rejected actions, and most common failure reasons.

### Phase 6: Polish for Portfolio (Day 12-14)

- Demo a safe and unsafe task: Show the agent completing a low-risk analysis, then attempting a sensitive action that gets routed to approval.
- Write the architecture narrative: Focus on permission boundaries, audit logs, and human-in-the-loop design. Those details make the project feel production-minded.

## Interview talking point

> The key phrase is "the model proposes, the system disposes." The LLM suggests actions, but deterministic permission checks decide what happens.

## Status

In progress — Phases 1-5 implemented, plus part of Phase 6:

- **Phase 1 — Agent and tool model:** a tool registry (`app/tools/registry.py`) where every
  tool declares its name, description, JSON input/output schema, allowed roles, rate limit,
  risk level, and whether it requires approval. Five starter tools: `calculator` (safe `ast`-based
  arithmetic, no `eval`), `file_reader` (sandboxed to `sandbox_files/`, path traversal blocked),
  `web_search` (offline stub over a small mock index), `csv_query` (medium-risk lookup over an
  embedded customer dataset), and `ticket_create` (high-risk mock write API).
- **Phase 2 — Permission checks:** four roles (`viewer`, `analyst`, `operator`, `admin`) resolved
  server-side from `user_id` — a caller can never assert its own role. Low-risk tools execute
  immediately once the role check passes; medium-risk tools return `needs_confirmation` until
  resubmitted with `confirmed=true`; high-risk tools always return `needs_approval` until a human
  approves out of band. Every tool call's arguments are validated against the tool's Pydantic
  model before the handler ever runs (`app/tools/executor.py`).
- **Phase 3 — Agent workflow graph:** a small explicit state machine (`app/agent/graph.py`) —
  intake, plan, tool_selection, permission_check, tool_execution, result_reflection,
  approval_wait, final_response — implemented in-process rather than pulling in LangGraph, Redis,
  or Postgres, matching this repo's offline-runnable-by-default convention. An offline `StubPlanner`
  routes natural-language requests to a tool with no API key required (`OpenAIPlanner` is available
  behind `OPENAI_API_KEY`). Denied requests end immediately with a safe explanation; medium/high-risk
  requests pause the task (`awaiting_confirmation` / `awaiting_approval`) with the pending tool call
  persisted so `POST /v1/agent/tasks/{id}/resume` can approve, reject, or run it with edited
  arguments later. If a tool fails and declares a `fallback_tool`, the workflow retries once with
  that safer alternative before giving up.

- **Phase 4 — Human approval:** `GET /v1/agent/approvals` (`app/agent/approvals.py`) turns every
  paused task into a compact review item — tool name, arguments, risk level, a one-line model
  reasoning summary pulled from the `plan` step, and the tool's declared expected effect.
  `POST /v1/agent/tasks/{id}/resume` now accepts four decisions: `approve` (run as proposed),
  `modify` (run with reviewer-edited `modified_arguments`, required by the request schema),
  `reject` (end the task), and `replan` (discard the pending action and ask the planner to
  propose a new one, which is routed through selection/permission/execution again — it may
  complete, fail, or pause once more). Every decision is written to a structured, queryable
  audit log (`app/agent/decisions.py`, `GET /v1/agent/decisions?task_id=...`) recording who
  decided, the original vs. modified arguments, the reason, and the outcome — separate from the
  free-text step already appended to the task's trace.
- **Phase 5 — Observability:** `GET /v1/agent/tasks/{id}/trace`
  (`app/observability/tracing.py`) renders a task's step log as an ordered timeline of spans,
  each carrying latency and a flat per-risk-level stub cost estimate for tool-execution steps
  (this repo has no live billing integration, so cost is directional, not exact provider
  pricing) plus the task's linked decision-log entries and running totals. `GET /v1/agent/safety`
  (`app/observability/safety.py`) rolls every task and decision seen so far up into fleet-wide
  safety analytics: per-tool usage counts, how many attempts the permission layer blocked
  outright (denied before a human ever saw them), the human approval rate and rejection count
  on paused tasks, and the most common failure reasons.
- **Phase 6 — Portfolio polish (partial):** `python demo.py` (`app/demo.py`) runs a scripted,
  offline walkthrough of two tasks end to end — a low-risk analyst calculator query that
  auto-completes, and a high-risk operator "create a ticket" request that the permission layer
  routes to `awaiting_approval` instead of executing — and prints each one's full step timeline.

Remaining: the Phase 6 architecture narrative (permission boundaries, audit logs, human-in-the-
loop design as the portfolio write-up).

Run tests: `pip install -r requirements-dev.txt && ruff check . && pytest -q`
Run the demo: `python demo.py`
