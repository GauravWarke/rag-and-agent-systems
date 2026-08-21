# Walkthrough — RAG Freshness and Drift Monitor (P7)

A recorded screen-capture isn't practical in this environment, so this is a
transcript walkthrough: the exact requests run against this repo (via
FastAPI's `TestClient`, equivalent to the `curl` commands in the README) and
the real output they produced, in the order a reviewer would want to see
them. Every response below came from the actual `stub` (keyless, offline)
pipeline — nothing is hand-edited. This is the "demo a stale doc scenario"
walkthrough referenced in `ROADMAP.md` Phase 6.

## 1. Healthy baseline

Build the index and record probe/answer baselines against the corpus as it
stands today:

```
POST /v1/index/build   -> 8 chunks across policies.md, product.md, troubleshooting.md, changelog.md
POST /v1/probes/run    -> 20/20 probes matched their expected chunk (match_rate: 1.0)
POST /v1/answers/run   -> 20 grounded, citation-tagged answers recorded as the baseline
GET  /v1/scorecard
```

```json
{
  "generated_at": "2026-08-21T00:35:14.284893+00:00",
  "manifest_available": true,
  "docs_changed": 0,
  "chunks_needing_reindex": 0,
  "probes_total": 20,
  "probes_drifting": 0,
  "answer_drift_checked": 20,
  "answer_drift_changed": 0,
  "stale_answer_risks": 0,
  "recommendations": []
}
```

Everything is green: no doc changes, no drift, no stale-answer risk.

## 2. Change a policy document

`data/docs/policies.md`'s "Refund Policy" section is edited in place — a
real, meaningful content change, not a typo:

```diff
- Customers can request a refund within 30 days of purchase if the product
- has not been activated. Approved refunds are processed within 5 business
- days back to the original payment method.
+ Customers can request a refund within 45 days of purchase if the product
+ has not been activated. Approved refunds are processed within 3 business
+ days back to the original payment method, and expedited refunds are
+ available for Enterprise customers.
```

No re-index has happened yet — the corpus on disk and the saved manifest
now disagree.

## 3. The system detects the risk

```
POST /v1/freshness/scan
```

```json
{
  "diff": {
    "modified": [
      {
        "chunk_id": "policies::refund-policy",
        "section_heading": "Refund Policy",
        "change_type": "modified",
        "semantic_change_score": 0.14218355308156194
      }
    ]
  },
  "prioritized": [
    {
      "priority": "high",
      "reasons": [
        "matched keyword 'refund'",
        "matched keyword 'policy'",
        "semantic change score 0.142"
      ]
    }
  ]
}
```

`app/freshness/priority.py` flags this `high` priority on keyword impact
(`refund`, `policy`) even though the semantic change score (0.142) alone is
modest — a pricing/policy change should never wait behind low-priority
queue items just because the wording only changed a little.

```
GET /v1/scorecard
```

```json
{
  "docs_changed": 1,
  "chunks_needing_reindex": 1,
  "probes_drifting": 0,
  "answer_drift_changed": 0,
  "stale_answer_risks": 2
}
```

`stale_answer_risks: 2` is the interesting number: probes `p01` and `p02`
both ground on `policies::refund-policy`, so both are now flagged as
serving a stale answer — the source changed but nobody has re-run the
answer generator against it yet. Retrieval itself hasn't drifted
(`probes_drifting: 0`, `answer_drift_changed: 0`) because nothing has
re-run against the new corpus — this is exactly the risk `detect_stale_answer_risk`
exists to catch: a *silent* staleness that plain drift checks would miss.

```
POST /v1/alerts/check
```

```json
{
  "triggered": [
    "1 high-priority doc change(s) need re-indexing (docs changed without a rebuild).",
    "2 probe answer(s) may be stale (source changed but the answer did not)."
  ],
  "channel": "log",
  "delivered": true
}
```

With no `SLACK_WEBHOOK_URL` configured, `NullAlertClient` records the alert
locally (`channel: "log"`) instead of posting to Slack — same alert
content either way, see `app/alerts/client.py`.

## 4. One-click rebuild

```
POST /v1/rebuild
```

This re-indexes the corpus from disk, re-runs the probe and answer
baselines against the fresh index, recomputes the scorecard, and dispatches
any alerts it trips — all in one call. The returned manifest now carries
the updated refund-policy chunk hash and text.

## 5. Probes return to healthy

```
POST /v1/probes/drift
```

```json
{
  "drifted": []
}
```

```
GET /v1/scorecard
```

```json
{
  "docs_changed": 0,
  "chunks_needing_reindex": 0,
  "probes_drifting": 0,
  "answer_drift_changed": 0,
  "stale_answer_risks": 0,
  "recommendations": []
}
```

Back to fully green: the rebuild re-established the baseline against the
edited corpus, so there is nothing left to flag. The retrieved chunk for
`p01`/`p02` never actually changed (`policies::refund-policy` is still the
best match either way) — what changed was the *content of that chunk*,
which is exactly the gap between retrieval drift and staleness that this
project's Phase 4 (`detect_stale_answer_risk`) exists to close.
