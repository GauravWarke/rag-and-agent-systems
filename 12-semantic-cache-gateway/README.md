# P12: Semantic Cache Gateway for LLM APIs

**Topic:** LLMOps, Cost Reduction, Latency Optimization, Embeddings

## What you're building

A drop-in gateway that detects semantically similar LLM requests, serves cached responses when safe, and tracks cost and latency savings. It supports exact cache keys, semantic similarity, TTLs, and feature-specific cache policies.

## Why this project lands interviews

> Repeated LLM calls waste money and slow apps down. A semantic cache gives you a clear infrastructure project with cost, latency, and correctness tradeoffs.

## Tech stack

| Component | Tool / Library |
|-----------|----------------|
| Language | Python 3.11+ |
| Proxy | FastAPI |
| Embeddings | OpenAI embeddings or sentence-transformers |
| Cache Store | Redis + vector search or Qdrant |
| Provider Layer | OpenAI / Anthropic / Ollama |
| Metrics | Prometheus |
| Dashboard | Grafana or Streamlit |
| Load Testing | Locust or k6 |
| Containerization | Docker Compose |

## Build phases

### Phase 1: Build the Proxy Contract (Day 1-3)

- Mirror a chat completion API: Accept model, messages, temperature, max tokens, and metadata. Return the provider-style response plus cache metadata.
- Normalize requests: Hash system prompt, model, temperature, tool settings, and feature name. Two prompts are only cache-compatible if these settings match.
- Forward cache misses: If no cache hit exists, call the provider, store the response, and return it.

### Phase 2: Build Semantic Matching (Day 3-5)

- Embed user intent: Create embeddings for the user message or normalized prompt. Store embedding with response metadata.
- Query nearest neighbors: If similarity is above threshold, return cached response. Start conservative around 0.95.
- Store debug info: Save original prompt, matched prompt, similarity score, cache decision, and response ID.

### Phase 3: Build Cache Policies (Day 5-8)

- Add TTLs by feature: Stable FAQs can have long TTLs. Time-sensitive or user-specific requests should have short TTLs or caching disabled.
- Add policy tags: Support tags like user_specific, current_events, legal_sensitive, and creative. Use tags to change threshold and TTL.
- Add invalidation endpoints: Invalidate by model, system prompt hash, feature, user, tag, or time range.

### Phase 4: Add Safety Checks (Day 8-10)

- Prevent cross-user leakage: Never serve cached responses across users for personal or private contexts unless explicitly allowed.
- Add semantic hit validation: For borderline matches, use a lightweight judge to confirm that the cached answer still fits the new prompt.
- Track near misses: Log prompts just below threshold. These help tune cache policies.

### Phase 5: Build Metrics and Load Test (Day 10-12)

- Export metrics: Track hit rate, semantic hit rate, exact hit rate, average latency saved, cost saved, and wrong-hit reports.
- Build a dashboard: Show real-time hit rate, latency comparison, cost savings, cache size, and threshold tradeoffs.
- Run a workload simulation: Send 2,000 requests with repeated and paraphrased questions. Measure savings and false-hit rate.

### Phase 6: Polish for Portfolio (Day 12-14)

- Demo instant responses: Show a miss, an exact hit, a semantic hit, and an intentionally blocked unsafe cache hit.
- Use ROI: Example headline: "Reduced simulated LLM cost by 41% and P95 latency by 68% with conservative semantic caching."

## Interview talking point

> The hard part is not caching. The hard part is deciding when two requests are "similar enough" without returning a wrong answer.

## Status

Planned. Scaffold pending — see root `ROADMAP.md`.
