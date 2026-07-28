# Walkthrough — Support Knowledge Copilot (P1)

A recorded screen-capture isn't practical in this environment, so this is a
transcript walkthrough: the exact commands run against this repo and the
real output they produced, in the order a reviewer would want to see them.
Every response below came from the actual `stub` (keyless, offline)
pipeline — nothing is hand-edited.

## 1. Ingestion

```bash
$ python ingest.py --source data/sample_docs --rebuild
Indexed 7 chunks from data/sample_docs (heading strategy) -> storage/index/manifest.json
```

`storage/index/manifest.json`:

```json
{
  "source_dir": "data/sample_docs",
  "chunking_strategy": "heading",
  "chunk_count": 7,
  "documents": { "api": 2, "faq": 3, "troubleshooting": 2 }
}
```

Each chunk carries `source_name`, `section_heading`, `last_updated`, `doc_type`,
and `access_level` from ingestion (see `app/core/models.py::ChunkMetadata`),
so retrieval and the eval report can break results down by source later.

## 2. A good answer with verified citations

Request:

```json
POST /ask
{"question": "How do I reset my password?"}
```

Response (trimmed to the fields that matter):

```json
{
  "answer": "Resetting your password\nTo reset your password, open Settings, choose Security, and click \"Reset password\".\nA reset link is emailed to your registered address and expires after 30 minutes. [faq::heading::0] ...",
  "citations": [
    {
      "chunk_id": "faq::heading::0",
      "claim": "Resetting your password\nTo reset your password, open Settings, choose Security, and click \"Reset password\".\nA reset link is emailed to your registered address and expires after 30 minutes.",
      "supported": true,
      "evidence_span": "Resetting your password\nTo reset your password, open Settings, choose Security, and click \"Reset password\"..."
    }
  ],
  "confidence": {
    "retrieval_score": 0.3333,
    "citation_support_rate": 1.0,
    "answer_completeness": 1.0,
    "no_answer_detected": false,
    "final": 0.6667
  },
  "could_not_verify": []
}
```

Every claim in the answer is tagged with the chunk ID it came from
(`[faq::heading::0]`), and the citation verifier independently confirms each
claim is backed by that chunk's text (`supported: true`) before the
response is returned.

## 3. A failed citation being caught

The stub generator only ever cites the chunk each claim was extracted from,
so it never produces an unsupported citation on its own — the interesting
part to demonstrate is the verifier itself catching a hallucinated claim
that a less careful generator (or a future LLM-based one) might produce.
Calling `app.generation.citation_verifier.verify_citations` directly with a
claim that the cited chunk does **not** support:

```python
from app.generation.citation_verifier import verify_citations

# faq::heading::0's actual text only covers Settings > Security > "Reset
# password", nothing about SMS codes.
hallucinated_claim = (
    "Password resets also require a 6-digit SMS verification code "
    "sent to your phone."
)
citations = verify_citations([(hallucinated_claim, retrieved_faq_chunk)])
```

Output:

```
claim:     Password resets also require a 6-digit SMS verification code sent to your phone.
chunk_id:  faq::heading::0
supported: False
evidence:  Resetting your password
           To reset your password, open Settings, choose Security, and click "Reset password".
           A reset link is emailed to your registered address a...
```

`supported: False` — the lexical-overlap check (`SUPPORT_THRESHOLD = 0.5` in
`citation_verifier.py`) correctly flags the claim because the cited chunk
never mentions SMS codes. In `_generate_stub`, any citation the verifier
marks unsupported is added to `could_not_verify` and lowers
`citation_support_rate` in the confidence breakdown instead of being
presented to the user as fact.

## 4. A no-answer case handled correctly

Request:

```json
POST /ask
{"question": "How do I set up single sign-on (SSO) for my team?"}
```

Response:

```json
{
  "answer": "I could not find this in the docs. Here are the closest matching sections I found.",
  "citations": [],
  "confidence": {
    "retrieval_score": 0.0,
    "citation_support_rate": 0.0,
    "answer_completeness": 0.0,
    "no_answer_detected": true,
    "final": 0.0
  },
  "could_not_verify": ["How do I set up single sign-on (SSO) for my team?"]
}
```

SSO isn't covered anywhere in the sample corpus. Because the best
`rerank_score` across retrieved chunks falls below
`settings.min_retrieval_score` (0.15), the pipeline refuses to guess and
returns the honest "I could not find this in the docs" response
(`app/generation/answer.py::_no_answer_response`) along with the closest
chunks it did retrieve, rather than fabricating an answer.

## 5. Eval report

```bash
$ python eval.py --strategy hybrid
Wrote reports/eval_hybrid.md (34 cases, answer_correct_rate=64%)
Wrote reports/dashboard.html (strategies: hybrid, dense)
```

`reports/eval_hybrid.md` scores retrieval hit rate, answer correctness,
citation validity, and refusal correctness separately across all 34 golden
questions (simple lookups, multi-doc, ambiguous, outdated-doc traps, and
no-answer cases), and `reports/dashboard.html` renders the same run with a
strategy toggle to compare hybrid against dense-only retrieval. Both are
gitignored build artifacts — regenerate them locally with the command above.
