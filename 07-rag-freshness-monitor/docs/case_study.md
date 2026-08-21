# Case Study — RAG Freshness and Drift Monitor

## Headline result

In the stale-doc demo (see [`walkthrough.md`](walkthrough.md)), editing one
policy section produced `stale_answer_risks: 2` **at the exact moment**
`probes_drifting: 0` and `answer_drift_changed: 0` — the two "did anything
change" signals a typical RAG monitor would ship first. Retrieval never
drifted because the same chunk (`policies::refund-policy`) was still the
best match before and after the edit, and answer drift was `0` only because
nobody had re-run the answer generator yet. A monitor that only watched
retrieval drift and answer drift would have reported a clean bill of health
while two probes were one query away from serving an out-of-date refund
window. `detect_stale_answer_risk` (`app/answers/drift.py`) closes that gap
by cross-referencing the freshness diff against the answer baseline
directly, instead of waiting for drift metrics that only fire *after*
someone happens to re-run the pipeline.

| Signal (after the policy edit, before rebuild) | Value |
|---|---|
| Docs changed | 1 |
| Chunks needing re-index | 1 |
| Priority | `high` (keyword: `refund`, `policy`) |
| Semantic change score | 0.142 |
| Probes drifting | 0 |
| Answer drift changed | 0 |
| **Stale answer risks** | **2** |

After `POST /v1/rebuild`, every signal returns to `0` in the same call —
see the full before/after transcript in `walkthrough.md`.

## Reading the result honestly

The demo corpus is small (8 chunks across 4 documents, 20 probes), so this
is a proof of the *mechanism*, not a claim about production-scale drift
rates. What it does demonstrate is the specific failure mode this project
targets: content can change underneath a RAG index without moving the
retrieval ranking at all (the edited chunk was already the top match, and
stayed the top match), so retrieval-drift monitoring alone is not sufficient
signal that answers are still accurate. The semantic-change score (0.142)
is deliberately not the only input to priority — a one-word typo would
score similarly low but shouldn't page anyone, so `prioritize_diff` also
checks impact keywords (pricing, policy, security, API, troubleshooting)
and lets keyword matches override a low semantic score.

## Architecture

```
data/docs/*.md ──▶ chunker ──▶ manifest (chunk hash, embedding version)
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        ▼                            ▼                             ▼
  freshness diff              probe retrieval drift          answer drift
  (hash + semantic             (top-1 chunk before/after)    (LLM-judge / stub
   change vs. manifest)                                       cosine vs. baseline)
        │                            │                             │
        └──────────────┬─────────────┴──────────────┬──────────────┘
                        ▼                            ▼
                 priority ranking            stale-answer risk
                 (impact keywords)        (source changed, answer didn't)
                        │                            │
                        └─────────────┬──────────────┘
                                       ▼
                            freshness scorecard ──▶ alerts (Slack / log)
                                       │
                                POST /v1/rebuild (re-index + re-baseline + re-alert)
```

See `README.md`'s Status section for the full endpoint-to-module map and
`walkthrough.md` for the transcript this diagram is drawn from.

## Tradeoffs and decisions

- **Stale-answer risk as its own signal, not a derived metric.** It would
  be tempting to fold this into the freshness diff or the answer-drift
  report, but it only exists at the intersection of the two — a doc that
  changed *and* an answer that didn't move — so it gets its own function
  (`detect_stale_answer_risk`) and its own field on the scorecard, exactly
  because neither parent signal implies it (demonstrated above).
- **Keyword priority overriding semantic score, not just weighting it.**
  `prioritize_diff` treats "matched a high-impact keyword" as a floor on
  priority rather than one input averaged with the semantic score. A
  refund-window change with a low semantic score (0.142 here) still needs
  to be `high` priority, because the *category* of the change (pricing/
  policy) carries more real-world urgency than how many words moved.
- **One-click rebuild reuses the same baseline-building code as the
  original index build.** `POST /v1/rebuild` calls the identical
  `build_manifest` / `run_probes` / `generate_answers` functions used by
  the individual endpoints, so "rebuild" can never silently diverge from
  what a fresh `/v1/index/build` + `/v1/probes/run` + `/v1/answers/run`
  sequence would produce.
- **Offline-first by design.** The stub embedder, stub answer generator,
  and stub LLM-judge (cosine similarity over the same hashed embedding
  space) make the entire pipeline — including the LLM-as-judge drift
  comparison — reproducible with no API key, which is what makes the
  transcript in `walkthrough.md` exactly reproducible by any reviewer.

## What would change at production scale

With hundreds of documents and a real embedding model, semantic-change
scores would need calibration per document type (a one-sentence pricing
page moves the needle more than a one-sentence FAQ aside), and the keyword
list in `prioritize_diff` would need to grow into a maintained taxonomy
rather than a fixed set. The next real investment is scheduling: this
project builds the detection and one-click rebuild, but a production
deployment would run `/v1/freshness/scan` and `/v1/alerts/check` on a cron
(Celery beat, as noted in the tech stack) rather than on demand.
