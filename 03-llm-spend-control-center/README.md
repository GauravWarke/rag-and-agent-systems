# P3: LLM Spend Control Center

**Topic:** LLMOps, Cost Optimization, Model Routing, Budget Monitoring

## What you're building

A routing and budgeting layer that sits in front of LLM calls, tracks usage by team or feature, chooses cost-effective models when appropriate, and warns or blocks usage when budgets are at risk.

## Why this project lands interviews

> Quality matters, but so does the bill. This build lets you talk about routing, budgets, latency, and the tradeoff between cost and answer quality.

## Tech stack

| Component | Tool / Library |
|-----------|----------------|
| Language | Python 3.11+ |
| API Gateway | FastAPI |
| Storage | PostgreSQL |
| Cache / Counters | Redis |
| Providers | OpenAI, Anthropic, Ollama |
| Classifier | scikit-learn or small LLM |
| Dashboard | Streamlit or Grafana |
| Worker | Celery / RQ |
| Containerization | Docker Compose |

## Build phases

### Phase 1: Build the Unified Request Gateway (Day 1-3)

- Define a standard request format: Accept chat-style input, team ID, feature name, priority, and optional model preference. Normalize all provider responses into one response schema.
- Create a model registry: Store model name, provider, quality tier, input cost, output cost, latency estimate, max context length, and supported features like vision or tool calling.
- Build provider adapters: Implement one adapter per provider. Each adapter should return output text, token counts, latency, cost, and provider metadata.

### Phase 2: Build Cost Tracking and Budgets (Day 3-5)

- Log every request: Store timestamp, team ID, feature, model used, input/output tokens, latency, status, and cost. Make this audit trail queryable.
- Add budget policies: Each team or feature gets daily and monthly limits. Track spend against those limits in real time.
- Create warning and block behavior: At 80% budget, send warning alerts. At 100%, block low-priority requests or require override. Return clear errors instead of silently failing.

### Phase 3: Build Request Complexity Routing (Day 5-8)

- Define routing tiers: Tier 1 is extraction and formatting. Tier 2 is summarization and classification. Tier 3 is reasoning-heavy or high-risk work.
- Build a lightweight classifier: Use features like prompt length, instruction verbs, required output format, context size, and risk tags. A simple model is fine; the architecture matters more than perfect ML.
- Map tiers to models: Route simple work to cheaper models, moderate work to mid-tier models, and risky work to high-quality models. Store this mapping in YAML or database config.
- Add override rules: Some features should always use a stronger model because correctness matters more than cost. Make those rules explicit.

### Phase 4: Add Quality Checks and Escalation (Day 8-10)

- Sample responses for verification: For a percentage of requests routed to cheaper models, asynchronously compare output quality against a stronger model.
- Detect bad routing decisions: If the cheap model fails a quality check, mark the request as a routing miss. Store the prompt, chosen model, better model, and reason.
- Add auto-escalation for high-risk requests: If confidence is low or the request is tagged high-priority, rerun with a stronger model before returning the final answer.

### Phase 5: Build the Cost Dashboard (Day 10-12)

- Show spend by team and feature: Include daily cost, monthly projection, top expensive prompts, and cost by model.
- Show savings estimates: Compare actual routed spend with "everything sent to the strongest model." This gives you the main metric for the case study.
- Add routing quality metrics: Show escalation rate, verifier pass rate, latency by model, and error rate by provider.

### Phase 6: Polish for Portfolio (Day 12-14)

- Run a simulated workload: Send 1,000 mixed prompts through the gateway and produce a cost savings report.
- Write the case study: Start with: "Reduced simulated LLM spend by X% while maintaining Y% verification pass rate." Then show the routing design and budget enforcement flow.

## Interview talking point

> Explain that budgets should be enforced before the provider call, but final cost is only known after the response. That small detail shows real systems thinking.

## Status

In progress — Phases 1-3 complete:

- **Phase 1 — Unified Request Gateway:** `POST /v1/chat` accepts a
  standard chat-style request (messages, team ID, feature, priority,
  optional model) and returns one normalized response shape regardless
  of provider. Model registry (`data/model_registry.yaml`) holds
  pricing/tier/capability metadata per model. Adapters implemented for
  `stub` (offline, deterministic, default), `openai`, `anthropic`, and
  `ollama` — the real-provider adapters need an API key/local server and
  aren't exercised by the offline test suite.
- **Phase 2 — Cost Tracking and Budgets:** every request is logged
  (`app/usage/store.py`) with team/feature/model/tokens/latency/cost and
  is queryable via `GET /v1/usage/summary`. Per-team and per-feature
  daily/monthly budget policies (`data/budget_policies.yaml`) are
  enforced before the provider call — 80%+ usage returns a warning,
  100%+ blocks unless the request is `priority: high` or sets
  `override_budget_block`.
- **Phase 3 — Request Complexity Routing:** a rule-based classifier
  (`app/routing/classifier.py`) scores prompt length, instruction verbs,
  and risk tags into tiers 1-3, mapped to the cheapest *available*
  model per tier in the registry. Feature-level overrides
  (`data/routing_overrides.yaml`) force a tier regardless of the
  classifier's read — e.g. `legal-review` always gets a tier-3 model.

Phases 4-6 (quality-check escalation, cost dashboard, portfolio polish)
are not yet built — see root `ROADMAP.md`.
