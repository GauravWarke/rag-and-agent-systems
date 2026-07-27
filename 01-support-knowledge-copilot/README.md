# P1: Support Knowledge Copilot with Verified Citations

**Topic:** RAG, Hybrid Retrieval, Citation Verification, Retrieval Evaluation

## What you're building

A support knowledge assistant that answers employee or customer support questions using internal documentation, retrieves evidence from multiple sources, generates grounded answers with citations, and verifies whether every citation supports the claim it is attached to.

## Why this project lands interviews

> A basic RAG demo is easy. This version gives you concrete things to discuss: chunking choices, hybrid retrieval, citation checks, no-answer handling, and eval numbers.

## Tech stack

| Component | Tool / Library |
|-----------|----------------|
| Language | Python 3.11+ |
| API | FastAPI |
| Embeddings | OpenAI text-embedding-3-small or bge-small |
| Vector Store | Qdrant or ChromaDB |
| Sparse Search | BM25 via rank_bm25 |
| LLM | GPT-4o-mini / Claude Haiku / local Llama |
| Evals | RAGAS, DeepEval, or custom metrics |
| UI | Streamlit |
| Containerization | Docker Compose |

## Build phases

### Phase 1: Define the Knowledge Assistant Scope (Day 1-2)

- Pick a realistic document set: Use a small but believable support corpus: product FAQs, troubleshooting guides, onboarding docs, API docs, release notes, and policy pages. The corpus should have overlapping information so retrieval is not too easy.
- Define the assistant contract: Input is a user question. Output is an answer, source citations, confidence score, and a short "what I could not verify" section. This contract matters because production RAG systems need to be honest about uncertainty.
- Create metadata rules: Every document should include source name, section heading, last updated date, document type, and access level. Store this metadata from the beginning so you can filter retrieval later.

### Phase 2: Build Ingestion and Chunking (Day 2-4)

- Normalize documents into clean text: Write loaders for Markdown, HTML, text files, and PDFs. Preserve headings and page numbers wherever possible. Store both raw and cleaned versions so you can debug indexing issues.
- Implement multiple chunking strategies: Start with recursive heading-based chunking, then add fixed-size chunking with overlap. Track which strategy produced each chunk so you can compare performance later.
- Generate embeddings and indexes: Embed every chunk and store it in the vector database. Build a BM25 index over the same chunk IDs. Both indexes should point to the same metadata so the fusion layer is clean.
- Add a re-index command: Build a CLI command like python ingest.py --source docs/ --rebuild. This keeps it closer to how a teammate would use the tool.

### Phase 3: Build Hybrid Retrieval (Day 4-6)

- Implement dense retrieval: Embed the user question and retrieve the top-k closest chunks by cosine similarity. Store the raw similarity score for debugging.
- Implement sparse retrieval: Run BM25 over the same question and retrieve keyword-relevant chunks. This is especially useful for exact phrases, API names, SKUs, and error codes.
- Fuse results with RRF: Use Reciprocal Rank Fusion to merge dense and sparse result lists. Make the weights configurable so you can show how retrieval changes under different settings.
- Add a reranking pass: Rerank the top 20 fused chunks using a small cross-encoder or LLM-as-reranker. Keep the top 5 chunks for generation.

### Phase 4: Build Grounded Answer Generation (Day 6-8)

- Design the answer prompt: Tell the model to answer only from provided context, cite claims using chunk IDs, and say when the answer is not available. Keep the prompt simple and strict.
- Verify citations after generation: Parse citations from the answer and check whether each cited chunk supports the claim. Use an LLM-as-judge or rule-based claim extraction for V1.
- Create confidence scoring: Combine retrieval score, citation support rate, answer completeness, and "no-answer" detection into a single confidence score. Return the breakdown along with the final number.
- Handle missing knowledge gracefully: If retrieval confidence is low, return a helpful "I could not find this in the docs" response with the closest matching sections. A real user can act on that response.

### Phase 5: Build the Evaluation Suite and Dashboard (Day 8-11)

- Create a golden Q&A set: Write 50-75 questions by hand. Include simple lookups, multi-doc questions, ambiguous questions, outdated-document traps, and questions that have no answer in the corpus.
- Measure retrieval and answer quality separately: Track whether the right chunks were retrieved, whether the answer is correct, whether citations are valid, and whether the system correctly refused when the answer was missing.
- Build the dashboard: Show the question, answer, retrieved chunks, citation verdicts, and confidence breakdown. Add a toggle to compare dense-only vs. hybrid retrieval.
- Add an eval command: Create python eval.py --strategy hybrid and generate a Markdown or HTML report with metrics. This report is the artifact reviewers will open first.

### Phase 6: Polish for Portfolio (Day 11-12)

- Record a short walkthrough: Show ingestion, a good answer with verified citations, a failed citation being caught, and a no-answer case handled correctly.
- Write the case study: Start with a measurable result like: "Hybrid retrieval improved correct-source retrieval from 72% to 88% on a 60-question eval set." Then explain the architecture and tradeoffs.

## Re-index CLI

Rebuild the retrieval index from a directory of documents (Markdown, HTML, text, or PDF):

```bash
python ingest.py --source data/sample_docs --rebuild
```

`--strategy heading|fixed` picks the chunking strategy (default `heading`), and `--out`
sets the output directory (default `storage/index`, gitignored). The command writes
`manifest.json` (chunk count and per-document counts) and `chunks.jsonl` (one chunk per
line) to `--out`, and refuses to overwrite an existing index unless `--rebuild` is passed.

## Eval CLI

Run the golden Q&A set through the retrieval + generation pipeline and score
retrieval, answer correctness, citation validity, and refusal behavior
separately:

```bash
python eval.py --strategy hybrid
```

`--strategy hybrid|dense|sparse` picks which retrieval strategy to score
(default `hybrid`), and `--out` sets the report directory (default
`reports/`, gitignored). The command writes `eval_<strategy>.md` (an
aggregate scorecard plus a per-question pass/fail table) and `dashboard.html`
(a single static file with a strategy toggle showing each question, answer,
retrieved sources, citation verdicts, and confidence breakdown — comparing
`--strategy` against the dense-only baseline).

## Interview talking point

> Explain why you kept dense and sparse indexes over the same chunk IDs. It shows you understand that semantic search and keyword search solve different failure modes.

## Status

Active flagship — Phases 1-5 complete (scope, ingestion, hybrid retrieval,
grounded generation, eval suite + dashboard). Phase 6 (portfolio polish)
remains. See root `ROADMAP.md`.
