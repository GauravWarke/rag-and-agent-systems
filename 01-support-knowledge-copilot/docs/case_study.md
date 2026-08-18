# Case Study — Support Knowledge Copilot with Verified Citations

## Headline result

On the 34-question golden eval set (`python eval.py --strategy <name>`, stub
embedder + extractive generator, no API keys), **sparse (BM25) retrieval
never correctly refused a question that had no answer in the corpus (0/6
"no_answer" cases)**, because keyword overlap always surfaces a
plausible-looking chunk even when nothing actually supports an answer.
Adding a dense-similarity signal — as both the dense-only and hybrid
configurations do — recovered correct refusals on 2/6 of those cases (33%),
by combining low cosine similarity with the confidence gate to trigger the
"I could not find this in the docs" response instead of a false answer.

The same eval set also shows the opposite tradeoff: sparse retrieval
correctly identified intent on all 6 "ambiguous" short-form questions
(`"I can't log in."`, `"The upload failed."`) — 100% vs. hybrid's 50% and
dense's 67% — because exact keyword matches on the (short) query are enough
to find the right document even with almost no semantic signal.

| Metric (34 cases) | Sparse | Dense | Hybrid |
|---|---|---|---|
| Retrieval hit rate | 100% | 100% | 100% |
| Answer correct rate | 64% | 64% | 64% |
| Citation valid rate | 100% | 100% | 100% |
| Refusal correct rate (all 34) | 82% | 82% | 79% |
| No-answer refusals correct (of 6) | 0/6 | 2/6 | 2/6 |
| Ambiguous refusals correct (of 6) | 6/6 | 4/6 | 3/6 |

Run `python eval.py --strategy hybrid` (or `dense` / `sparse`) to regenerate
these numbers from `reports/eval_<strategy>.md`.

## Reading the result honestly

The demo corpus is deliberately small (9 chunks across 4 short documents,
plus a 2-chunk restricted policy doc excluded from this eval's default
`internal` access level — see "Access control" below), so raw retrieval hit
rate and answer correctness are saturated at the same value across all three
strategies — there just isn't enough corpus depth for retrieval strategy to
matter for finding *a* relevant chunk. What the
strategy choice actually changes is the **failure mode on edge-case
questions**: sparse retrieval is overconfident (it always finds *something*
to cite, so it never refuses), while dense retrieval is more willing to say
"I don't know" but occasionally misses the intent of a short ambiguous
query. This is the real argument for hybrid retrieval in production: neither
signal alone is well-calibrated, and RRF fusion plus a confidence gate lets
you tune where the system sits on the answer-vs-refuse tradeoff, rather than
being stuck with whichever failure mode one retriever happens to have.

## Architecture

```
client → FastAPI /ask
            │
            ▼
   HybridRetriever ── dense (embeddings, cosine) ─┐
            │        └ sparse (BM25) ─────────────┤→ RRF fuse → top-20 → rerank → top-5
            ▼
   grounded generator (extractive V1 / LLM later)
            │  → citation verification (lexical overlap V1 / LLM-judge later)
            ▼
   AskResponse (answer + citations + confidence + could_not_verify)
```

See [`architecture.md`](architecture.md) for the full component table and
metadata rules, and [`walkthrough.md`](walkthrough.md) for a transcript of
ingestion, a verified-citation answer, a caught bad citation, and a
correctly refused no-answer case.

## Tradeoffs and decisions

- **Dense and sparse indexes over the same chunk IDs.** This is the
  headline design decision: it keeps RRF fusion clean (both retrievers rank
  the same identifiers) and makes it possible to isolate which retriever is
  responsible for a given failure, as the table above does.
- **Confidence gating over a single "top hit" cutoff.** Refusal quality
  depends on combining retrieval score, citation support, and answer
  completeness rather than trusting any single signal — sparse's 0/6
  no-answer result is exactly what happens when retrieval score alone
  (BM25 always returns *a* top hit) is allowed to imply relevance.
- **Extractive V1 generator, no API key required.** The pipeline is fully
  offline-runnable by default so the eval numbers above are reproducible
  without provisioning credentials; swapping in an LLM generator and
  LLM-as-judge citation verifier is a drop-in upgrade behind
  `OPENAI_API_KEY` / `ANTHROPIC_API_KEY`.
- **Small demo corpus, by design.** It's large enough to require real
  chunking and fusion logic, but small enough that retrieval hit rate
  saturates — which is itself the finding above: strategy choice shows up
  in refusal calibration long before it shows up in raw hit rate.
- **Access control (audit finding).** `AskRequest.access_level` is enforced
  in `HybridRetriever._allowed_ids` and applied to the dense and sparse
  candidate pools *before* ranking, not filtered out of the response after
  the fact — a restricted chunk (`policy.md`, tagged `restricted`) can never
  be scored, cited, or leaked into `could_not_verify` for a caller whose
  clearance doesn't cover it. See `walkthrough.md` §2.5 for a transcript.

## What would change at production scale

With a larger, messier corpus (thousands of documents, real duplication and
staleness), hit rate would stop saturating and the dense/sparse/hybrid gap
on retrieval accuracy would likely reopen. The next investment would be a
real reranker (cross-encoder or LLM-as-reranker, both already stubbed behind
the same interface) and an LLM-as-judge citation verifier, since the
lexical-overlap verifier used here is a reasonable V1 but will miss
paraphrased unsupported claims.
