# Architecture — Support Knowledge Copilot (P1)

## Assistant contract (Phase 1)
- **Input:** a user question.
- **Output:** an answer, source citations (by chunk ID), a confidence breakdown,
  and an explicit "what I could not verify" section.
- **Principle:** the system must be honest about uncertainty. Low retrieval
  confidence returns a helpful "I could not find this in the docs" response.

## Data flow
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

## Metadata rules (Phase 1, step 3)
Every chunk stores: `source_name`, `section_heading`, `last_updated`,
`doc_type`, `access_level`. Stored from ingestion so retrieval can be
filtered by clearance (`HybridRetriever._allowed_ids`, enforced on both the
dense and sparse candidate pools before ranking — see the "Access control"
section of the README).

## Component choices
| Component | Choice | Why |
|-----------|--------|-----|
| API | FastAPI | async-friendly, standard for AI services |
| Dense | stub hashing-embedder (default) | runs offline/keyless; swap to `text-embedding-3-small` or `bge-small` |
| Sparse | BM25 via `rank_bm25` | catches exact matches: error codes, API names, SKUs |
| Fusion | Reciprocal Rank Fusion | merges dense + sparse over shared chunk IDs |
| Rerank | stub token-overlap reranker (default) | rescores top-20 fused chunks; swap to a cross-encoder or LLM-as-reranker |
| Container | Docker Compose | reproducible local + CI |

## Tradeoffs / decisions
- **Dense + sparse over the same chunk IDs** keeps fusion clean and lets us
  compare failure modes (semantic vs. keyword). This is the headline design
  decision to discuss in interviews.
- **Extractive V1 generator** ships a runnable, testable pipeline with no API
  key; the LLM generator and LLM-as-judge citation verifier are drop-in upgrades.

## What still needs manual setup
- Provide `OPENAI_API_KEY` / `ANTHROPIC_API_KEY` in `.env` to enable real
  embeddings + LLM generation.
- Choose and provision a persistent vector store (Chroma/Qdrant) for larger corpora.
