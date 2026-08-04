# Case Study — LLM Spend Control Center

## Headline result

Running `python simulate_workload.py --requests 1000 --seed 42` — 1,000
synthetic requests spread across 5 teams and 11 features, sent through the
gateway's offline `stub` provider (no API keys required) — **reduced
simulated LLM spend by 46.2% ($0.2147 actual vs. $0.3989 if every request
had gone to the strongest available model) while maintaining a 100.0%
verification pass rate** on the cheap-model responses that were sampled for
quality checking.

| Metric (1,000 requests, seed 42) | Value |
|---|---|
| Actual cost | $0.2147 |
| Hypothetical cost (all requests → `stub-strong`) | $0.3989 |
| Savings | 46.2% |
| Routed to tier 1 (cheapest) | 417 |
| Routed to tier 2 | 339 |
| Routed to tier 3 (strongest) | 244 |
| Auto-escalated (high priority or low confidence) | 88 (8.8%) |
| Verifier pass rate on sampled responses | 100.0% |
| Requests blocked by budget enforcement | 0 |

Re-run the script (same seed, same command) to regenerate these exact
numbers — the workload generator and the gateway's cost/routing logic are
fully deterministic; only the *count* of quality checks sampled varies
slightly between runs, because the verifier's own sampling uses an
unseeded `random.random()` (see `app/main.py`).

## Reading the result honestly

The 46% figure is driven almost entirely by how the synthetic workload is
shaped: roughly half the requests are short, mechanical asks (extraction,
formatting) that the complexity classifier correctly routes to the
cheapest tier, while only 24% carry the length or risk tags that justify
the strongest model. A workload that skewed more reasoning-heavy — more
`legal-review` / `medical-advice` / `financial-planning` traffic — would
show a smaller gap, because those features are pinned to tier 3 by
`data/routing_overrides.yaml` regardless of what the classifier reads.
That's the intended behavior, not a limitation: the savings number is a
property of the traffic mix, and the routing/override design is what lets
an operator trade cost for correctness deliberately per feature rather
than uniformly.

The verifier's 100% pass rate on this run is a product of the `stub`
provider being deterministic — the "cheap" and "reference" models return
structurally similar, template-based output for the same prompt, so the
lexical-overlap judge (`app/quality/judge.py`) almost always agrees they
match. This is expected for the offline stub and is the reason the
project treats provider adapters as swappable: pointed at real models
behind `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`, the same verifier would see
genuine quality variance between a cheap and a strong model, and the
pass rate would become a meaningful signal rather than a smoke test.

## Architecture

```
client → POST /v1/chat
            │
            ▼
   budget check (block/warn before the provider call — the gateway only
            │    knows spend *so far*, not this request's own cost yet)
            ▼
   complexity classifier ── forced-tier override? ──┐
            │                                       ▼
            └──────────────────────────→ tier 1 / 2 / 3 → cheapest available model
            │
            ▼
   provider adapter (stub / openai / anthropic / ollama) → normalized response
            │
            ├─→ usage log (team, feature, model, tokens, cost, latency)
            │
            └─→ background quality sample (20% of sub-tier-3 responses) ──┐
                                                                            ▼
                                              replay against strongest model,
                                              lexical-overlap judge, log routing
                                              miss if similarity is low ──→ feeds
                                              per-feature escalation on future requests
```

See the root `README.md` **Status** section for the per-phase implementation
notes (gateway contract, budget enforcement, routing tiers, quality
verification, dashboard endpoints).

## Tradeoffs and decisions

- **Budgets enforced before the call, cost known after.** The gateway
  checks prior spend against the policy limit before dispatching to a
  provider, then logs the request's *own* cost only once the response
  comes back — a request can never be blocked on its own not-yet-known
  cost, only on spend already incurred. `priority: high` and
  `override_budget_block` are the two escape hatches once a budget is
  blocked.
- **Rule-based complexity classifier over an ML model.** Prompt length,
  instruction verbs, and risk tags are enough to make routing decisions
  explainable and testable without training data — the point of this
  project is the routing/budget architecture, not classifier accuracy.
- **Feature-level tier overrides win over the classifier.** `legal-review`,
  `medical-advice`, and `security-incident` always get the strongest model
  regardless of how short or simple the individual request looks, because
  for those features correctness risk outweighs the cost savings.
- **Quality verification runs in a background task, not inline.** Sampling
  20% of cheap-model responses for a strong-model comparison would add
  real latency if it blocked the response; instead it runs after the
  answer is already returned, and its findings only affect *future*
  requests for that feature via the escalation-on-recent-miss-rate rule.
- **Offline `stub` provider by default.** Every number in this case study
  is reproducible with no API keys and no network access — swapping in
  `openai` / `anthropic` / `ollama` adapters is a config change
  (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, `OLLAMA_ENABLED`), not a code
  change.

## What would change at production scale

With real provider traffic, the quality verifier would need a genuine
LLM-as-judge instead of the lexical-overlap stand-in, since paraphrased
answers that are still correct would otherwise look like mismatches. The
budget tracker would also need to move off in-memory storage (Redis or
Postgres, per the original tech-stack sketch) so limits are enforced
consistently across multiple gateway processes rather than per-worker.
