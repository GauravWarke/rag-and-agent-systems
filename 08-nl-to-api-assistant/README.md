# P8: Natural Language to API Assistant

**Topic:** Tool Calling, Guardrails, OpenAPI, Workflow Automation

## What you're building

A natural language interface that turns user requests into safe API calls against a mock business system. It reads an OpenAPI schema, plans the correct endpoint calls, validates parameters, runs dry-runs for risky actions, and asks for confirmation before making changes.

## Why this project lands interviews

> Tool calling is useful only when the model respects the API contract. This build gives you a strong story around schema-aware planning, dry runs, confirmation, and safe execution.

## Tech stack

| Component | Tool / Library |
|-----------|----------------|
| Language | Python 3.11+ |
| API Framework | FastAPI |
| API Schema | OpenAPI / JSON Schema |
| LLM | GPT-4o-mini / Claude Haiku |
| Validation | Pydantic + jsonschema |
| Storage | PostgreSQL or SQLite |
| UI | Streamlit |
| Testing | pytest + VCR-style mocks |
| Containerization | Docker Compose |

## Build phases

### Phase 1: Build the Mock Business API (Day 1-3)

- Create a realistic domain: Use a mock SaaS admin system with customers, subscriptions, invoices, tickets, and refunds.
- Expose OpenAPI docs: Build endpoints for read actions and write actions. Examples: get customer, list invoices, create ticket, update plan, issue refund.
- Add permission metadata: Mark each endpoint as read-only, low-risk write, or high-risk write. Include required roles.

### Phase 2: Build Schema-Aware Planning (Day 3-5)

- Parse the OpenAPI schema: Extract endpoint names, descriptions, parameters, request bodies, response schemas, and risk tags.
- Select relevant endpoints: Given a user request, retrieve candidate endpoints from the schema using embeddings or keyword search.
- Generate a call plan: The LLM outputs a structured plan: endpoint, method, parameters, reason, expected result, and whether confirmation is required.

### Phase 3: Build Validation and Dry Runs (Day 5-8)

- Validate parameters: Use JSON Schema and Pydantic before any API call. Reject missing, ambiguous, or invalid fields.
- Add dry-run mode: For write actions, show what would happen without changing data. The assistant should explain the planned action in plain English.
- Ask for confirmation: High-risk actions require explicit approval. Store the pending plan and resume only after confirmation.

### Phase 4: Execute Multi-Step Workflows (Day 8-10)

- Support chained calls: Example: find customer by email, fetch subscription, check invoice status, then create a support ticket.
- Pass outputs between steps: Store intermediate results in a typed workflow state. Do not rely on unstructured memory.
- Handle failures gracefully: If an API call fails or returns multiple matches, ask a clarifying question instead of guessing.

### Phase 5: Build Logs, UI, and Tests (Day 10-12)

- Log every plan and call: Capture user request, selected endpoints, parameters, validation result, approval status, API response, and final answer.
- Build a workflow UI: Show the user request, planned calls, dry-run preview, approval button, and final result.
- Create a golden workflow test suite: Write 40-50 natural language requests with expected endpoint plans. Include ambiguous and unsafe requests.

### Phase 6: Polish for Portfolio (Day 12-14)

- Demo a full workflow: Show a read-only request, a multi-step workflow, and a high-risk write that requires approval.
- Write the narrative: Lead with "safe tool use over real API contracts." That phrase maps closely to the work many AI platform teams are doing.

## Interview talking point

> Schema-aware tool use is safer than giving the model a vague list of tools. The schema gives the system a contract it can validate.

## Status

All six phases are implemented:

- **Phase 1 — Mock business API:** a small SaaS admin domain (`app/business_api/`) with
  customers, subscriptions, invoices, tickets, and refunds, seeded in-memory. Endpoints cover
  reads (get/list customers, list a customer's subscriptions, list invoices) and writes (create
  a ticket, update a subscription's plan, issue a refund). Every route declares its risk tier and
  required roles as OpenAPI extensions — `x-risk-level` (`read_only` / `low_risk_write` /
  `high_risk_write`) and `x-required-roles` — via `openapi_extra`, so the metadata lives in the
  schema itself rather than a side table.
- **Phase 2 — Schema-aware planning:** `app/planning/schema.py` parses `app.openapi()` into a
  flat list of `EndpointSpec`s (operation id, method, path, parameters, request/response
  schemas, risk tier, required roles). `app/planning/selector.py` narrows that list down to the
  endpoints whose name/summary/description/path share a keyword with the request (no embeddings,
  so this stays offline-runnable by default) — an empty result means no endpoint looked
  relevant, rather than guessing. `app/planning/planner.py`'s offline `StubPlanner` turns the
  request into a structured `CallPlan` (endpoint, parameters extracted by regex/keyword,
  reason, expected result, confidence); `OpenAIPlanner` is available behind `OPENAI_API_KEY`.
- **Phase 3 — Validation and dry runs:** `app/planning/validation.py` checks a plan's parameters
  against the endpoint's JSON Schema before anything executes — missing required fields, unknown
  fields, wrong types, and invalid enum values are all rejected with a specific message.
  `app/planning/workflow.py` then routes by risk tier: read-only calls validate and execute
  immediately; low-risk and high-risk writes get a plain-English dry-run preview first and pause
  (`awaiting_confirmation` / `awaiting_approval`) with the plan persisted, so
  `POST /v1/assistant/workflows/{id}/resume` can approve (execute the stored plan) or reject
  (end the workflow) later. A failed execution (e.g. the approved plan's target record no longer
  exists) is captured as a `failed` status with an `error` field rather than raising.

- **Phase 4 — Multi-step workflows:** `app/planning/chain.py` splits a request that describes
  several actions (anything containing "then") into ordered clauses — `find customer by email
  X, list her subscriptions, list her invoices, then create a support ticket` becomes four
  clauses. Each clause is planned independently against the endpoint catalog; at execution time
  `app/planning/workflow.py`'s `_run_chain` runs them in order, threading each step's result into
  a typed `Workflow.state` dict (e.g. a `list_customers` hit sets `state["customer_id"]`) so
  later steps that don't mention an id explicitly ("list her subscriptions") still resolve one.
  Read-only steps execute immediately; the first write step pauses the whole chain for
  confirmation/approval exactly like a single-call workflow, and `resume` continues from that
  step once approved. If a step's result is a list with more than one match, the chain stops
  with `needs_clarification` instead of guessing which one was meant; if a clause matches no
  endpoint, the chain stops `denied`.
- **Phase 5 — Audit logging:** `app/planning/audit_log.py` emits one structured log record per
  workflow create/resume event — request, selected endpoint(s)/parameters per call, validation
  result, status, result, and error — independent of the in-memory workflow store, via the
  `app.assistant.audit` logger.
- **Phase 5 — Workflow UI:** `GET /v1/assistant/workflows/{id}/view` (`app/planning/view.py`)
  builds a UI read-model from a `Workflow` — the request, one `PlannedCallView` per call (a
  single call or, for a chain, one per step) with its status/result/error, the dry-run preview,
  which of `approve`/`reject` a reviewer can currently take, and the final result — without the
  caller needing to know whether the workflow was a single call or a chain.
- **Phase 5 — Golden workflow test suite:** `data/golden_workflows.jsonl` has 40 natural-language
  requests (read-only, low-risk write, high-risk write, ambiguous/unmatched, missing-required-
  field "unsafe" requests, and multi-step chains) each with its expected endpoint plan and
  workflow status, generated by running every case through the real pipeline and captured as a
  regression net; `tests/test_golden_workflows.py` replays all of them.

- **Phase 6 — Portfolio polish:** `python demo.py` (`app/demo.py`) drives the real FastAPI app
  through three scenarios end to end — a read-only lookup that completes immediately, a
  three-step chain ("find customer by email, then list her subscriptions, then create a support
  ticket") whose first two read steps run immediately and whose final write step pauses for
  confirmation, and a high-risk refund that pauses for human approval — then resumes the paused
  ones and prints each step's full timeline.

All six phases are complete.

Run tests: `pip install -r requirements-dev.txt && ruff check . && pytest -q`
Run the demo: `python demo.py`

## Architecture narrative

**Safe tool use over real API contracts.** The schema is the contract, not a suggestion. Every
endpoint the planner can propose comes from `app.openapi()` — the same schema FastAPI serves at
`/docs` — parsed once into `EndpointSpec`s (`app/planning/schema.py`) that carry each endpoint's
parameters, request/response shapes, and the `x-risk-level` / `x-required-roles` extensions the
business API attaches to itself. Nothing about risk tiering or required parameters lives in a
side config the planner has to be trusted to remember; it lives in the schema the endpoint
already declares, so a new endpoint is safe by construction the moment its route decorator
declares a risk level, not because a prompt was updated to mention it.

**The planner proposes, validation and risk-gating dispose.** Whether the `StubPlanner` (offline,
keyword/regex-based) or `OpenAIPlanner` (behind `OPENAI_API_KEY`) generates it, a `CallPlan` is
just a structured guess — an operation id, parameters, and a reason. `app/planning/validation.py`
checks that guess against the endpoint's JSON Schema before anything runs: missing required
fields, unknown fields, wrong types, and bad enum values are all rejected with a specific
message, and a plan that fails validation never reaches execution regardless of what risk tier
its endpoint has. A plan that passes validation is then routed by `app/planning/workflow.py`
purely on the endpoint's declared risk tier — `read_only` executes immediately, `low_risk_write`
and `high_risk_write` always get a plain-English dry-run preview and pause — so no amount of
planner confidence can skip the gate a write's risk tier requires.

**A pause is a persisted state, not a blocked request.** When a workflow reaches
`awaiting_confirmation` or `awaiting_approval`, the handler returns immediately with the pending
plan (or, for a multi-step request, the pending chain and the typed `state` accumulated so far)
stored on the `Workflow` object. `POST /v1/assistant/workflows/{id}/resume` is the only way
forward from there, and it re-validates nothing blindly: `approve` re-executes the exact stored
plan, `reject` ends the workflow with no execution, and a rejected or approved decision is
appended to the workflow's own step log rather than a side channel, so the full history —
propose, dry-run, wait, decide, execute — is always visible on one object via
`GET /v1/assistant/workflows/{id}` or the UI-shaped `GET /v1/assistant/workflows/{id}/view`.

**Chains carry state instead of trusting memory.** A request like "find customer by email X, then
list her subscriptions, then create a ticket" is split into ordered clauses
(`app/planning/chain.py`) and each clause is planned against the endpoint catalog independently —
the planner never sees the other clauses' output as free text. Instead, each step's result is
parsed into typed updates (e.g. a `list_customers` hit sets `state["customer_id"]`) that later
steps read from explicitly when a clause doesn't repeat the id ("list her subscriptions"). Read
steps execute immediately and write their state forward; the first write step pauses the whole
chain exactly like a single-call workflow. If a step's result is ambiguous — more than one
customer matched an email — the chain stops with `needs_clarification` instead of guessing which
one was meant, and if a clause never resolves to an id the schema requires, it fails validation
rather than sending a call with a fabricated parameter.
