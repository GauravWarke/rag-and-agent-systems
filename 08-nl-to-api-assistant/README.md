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

Planned. Scaffold pending — see root `ROADMAP.md`.
