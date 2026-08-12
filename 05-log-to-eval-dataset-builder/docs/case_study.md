# Case Study — Production Log-to-Eval Dataset Builder

## Headline result

Running the real flywheel — seed, cluster, score, label, dedupe, human
review, export, eval — over 3,000 simulated production logs (see
`docs/case_study_batch.py`), the pipeline turned a 437-log candidate pool
(top high-value candidates plus a diversity sample) into **62 approved
eval cases across 3 eval types and 8 topic clusters, with 87.1%
auto-labeled and 12.9% cleared through human review**, after the dedup
pass rejected 85.8% of generated labels as near-duplicates of cases
already in the dataset.

| Metric | Value |
|---|---|
| Logs seeded | 3,000 |
| Clusters discovered | 8 |
| Candidate pool (high-value + diversity sample, deduped) | 437 |
| Labels generated | 437 |
| Rejected as near-duplicates | 375 (85.8%) |
| Accepted into the dataset (novel) | 62 |
| Auto-approved (confidence ≥ 0.75) | 54 (87.1%) |
| Queued for human review, then cleared | 8 (12.9%) |
| Approved cases exported to JSONL | 62 |
| Eval-type mix | 49 `expected_refusal` · 8 `rubric` · 5 `golden_answer` |
| First eval run pass rate | 79.0% (49/62) |

Regenerate this with `python docs/case_study_batch.py` from inside
`05-log-to-eval-dataset-builder/`.

## Reading the result honestly

85.8% is a strikingly high duplicate-rejection rate, and it's worth
explaining rather than hiding. `identify_candidates` (`app/sampling/
candidates.py`) scores safety edge cases (+5), errors (+4), and malformed
output (+3) far above a typical interaction, so the top of the candidate
pool skews heavily toward the `safety` category. The synthetic log
generator (`app/logs/synthetic.py`) draws from a small, deliberately
repetitive template pool — 8 issue templates × 5 customer names × 4
features — so once a handful of safety-flagged cases are labeled, most
later safety interactions really are near-duplicates by prompt embedding,
not false positives. That's the dedup layer (`app/labels/dedupe.py`,
cosine similarity ≥ 0.92 against every already-accepted case) doing
exactly its job: keeping the dataset from bloating with 40 versions of the
same refusal test just because 40 customers hit the same templated safety
prompt. The eval-type mix (49 refusal / 8 rubric / 5 golden) is the
direct, honest consequence of that scoring — this run over-represents risk
by design (`identify_candidates` prioritizes it explicitly), and the 200-
log diversity sample mixed into the candidate pool is what pulled in the
`golden_answer` and additional `rubric` cases at all.

## Architecture

```
production logs → LogStore (redacted on ingest)
        │
        ▼
sampling (random / failure_biased / diversity) ──┐
clustering (k-means over prompt embeddings) ──────┤
candidate scoring (unusualness, risk, coverage) ──┘
        │  high-value log_ids
        ▼
label generation (eval-type per log; 2 passes for safety cases)
        │
        ▼
dedup vs. every accepted case (cosine similarity ≥ threshold)
        │  novel ──────────────► confidence ≥ 0.75? ─── yes ──► approved
        │                                    │
        │                                    no
        │                                    ▼
        │                          human review queue ──► approve / edit / reject
        ▼
rejected_duplicate (logged with which case it duplicates)
        │
        ▼
export JSONL → eval runner (scores by eval_type, diffs vs. previous run) → dataset health
```

## Tradeoffs and decisions

- **Score for risk, not representativeness.** `identify_candidates`
  intentionally over-weights safety flags, errors, and malformed output —
  a good eval set should not mirror traffic, it should over-sample the
  interactions most likely to expose a regression. The tradeoff, visible
  in the eval-type mix above, is that a pure high-value selection skews
  toward one eval type; mixing in a diversity sample (as this run does) is
  the deliberate counterweight.
- **Dedup before confidence-gating, not after.** A candidate is checked
  for near-duplication first; only a genuinely novel case is then routed
  by confidence to auto-approval or human review. This keeps the review
  queue from ever seeing redundant work.
- **Two-pass labeling only for important cases.** `generate_label`
  (`app/labels/generator.py`) spends a second labeling pass on high-value
  logs and discounts confidence when the two passes disagree on eval
  type — a cheap calibration signal without doubling cost on every log.
- **Every reviewer action is diffed and logged, not just approved/
  rejected.** `POST /v1/review/decide` with `action: edit` stores the
  field-level diff and the reviewer's reason (`app/review/decisions.py`),
  so auto-label quality can be measured later from what humans actually
  changed, not just from self-reported confidence.

## What would change at production scale

The 85.8% duplicate rate is partly an artifact of the synthetic
template pool being smaller than real production traffic's actual
diversity — a real deployment would see this rate fall as genuinely
distinct prompts accumulate. The clearer lever is candidate-pool
composition: this run mixed a fixed 200-log diversity sample into the
high-value pool by hand; a production version would make that ratio (and
the per-category caps on how many safety/error cases get labeled before
diminishing returns set in) a tuned, monitored parameter rather than a
one-off script constant. The other natural next step is swapping
`StubLabelClient` for `OpenAILabelClient` (already wired behind
`OPENAI_API_KEY`) and re-running this same batch to see how much the
eval-type decisions and confidence scores shift with a real model doing
the labeling instead of the deterministic heuristic.
