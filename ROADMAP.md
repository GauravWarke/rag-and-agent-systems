# ROADMAP — RAG & Agent Systems

Live status of the five projects in this repo. Ticked boxes are built; unticked are queued.
An automated GitHub Actions workflow works down this list daily, runs the tests, and opens a PR.

Legend: `- [ ]` todo · `- [x]` done.

---

## 1. Support Knowledge Copilot with Verified Citations

*Topic: RAG, Hybrid Retrieval, Citation Verification, Retrieval Evaluation*  
Folder: `01-support-knowledge-copilot/`

- [x] **Scaffold** — create `01-support-knowledge-copilot/` app skeleton: FastAPI app entry, `requirements.txt`, `config.py`, `.env.example`, `README.md`, `tests/` dir, and a `Dockerfile`. Wire a `/health` endpoint and a smoke test.
- [x] **Hardening** — security headers + per-IP rate limiting on `/ask` (`secure` §3A / `infra-setup` domain 6), with unit tests.
- [x] **Access control** — enforce `access_level` metadata filtering during retrieval so restricted chunks never reach unauthorized answers (audit finding, `secure`).
- [x] **Phase 1: Define the Knowledge Assistant Scope** — Pick a realistic document set: Use a small but believable support corpus: product FAQs, troubleshooting guides, onboarding docs, API docs, release notes, and policy pages. The corpus should have overlapping information so retrieval is not too easy.
- [x] **Phase 1: Define the Knowledge Assistant Scope** — Define the assistant contract: Input is a user question. Output is an answer, source citations, confidence score, and a short "what I could not verify" section. This contract matters because production RAG systems need to be honest about uncertainty.
- [x] **Phase 1: Define the Knowledge Assistant Scope** — Create metadata rules: Every document should include source name, section heading, last updated date, document type, and access level. Store this metadata from the beginning so you can filter retrieval later.
- [x] **Phase 2: Build Ingestion and Chunking** — Normalize documents into clean text: Write loaders for Markdown, HTML, text files, and PDFs. Preserve headings and page numbers wherever possible. Store both raw and cleaned versions so you can debug indexing issues.
- [x] **Phase 2: Build Ingestion and Chunking** — Implement multiple chunking strategies: Start with recursive heading-based chunking, then add fixed-size chunking with overlap. Track which strategy produced each chunk so you can compare performance later.
- [x] **Phase 2: Build Ingestion and Chunking** — Generate embeddings and indexes: Embed every chunk and store it in the vector database. Build a BM25 index over the same chunk IDs. Both indexes should point to the same metadata so the fusion layer is clean.
- [x] **Phase 2: Build Ingestion and Chunking** — Add a re-index command: Build a CLI command like python ingest.py --source docs/ --rebuild. This keeps it closer to how a teammate would use the tool.
- [x] **Phase 3: Build Hybrid Retrieval** — Implement dense retrieval: Embed the user question and retrieve the top-k closest chunks by cosine similarity. Store the raw similarity score for debugging.
- [x] **Phase 3: Build Hybrid Retrieval** — Implement sparse retrieval: Run BM25 over the same question and retrieve keyword-relevant chunks. This is especially useful for exact phrases, API names, SKUs, and error codes.
- [x] **Phase 3: Build Hybrid Retrieval** — Fuse results with RRF: Use Reciprocal Rank Fusion to merge dense and sparse result lists. Make the weights configurable so you can show how retrieval changes under different settings.
- [x] **Phase 3: Build Hybrid Retrieval** — Add a reranking pass: Rerank the top 20 fused chunks using a small cross-encoder or LLM-as-reranker. Keep the top 5 chunks for generation.
- [x] **Phase 4: Build Grounded Answer Generation** — Design the answer prompt: Tell the model to answer only from provided context, cite claims using chunk IDs, and say when the answer is not available. Keep the prompt simple and strict.
- [x] **Phase 4: Build Grounded Answer Generation** — Verify citations after generation: Parse citations from the answer and check whether each cited chunk supports the claim. Use an LLM-as-judge or rule-based claim extraction for V1.
- [x] **Phase 4: Build Grounded Answer Generation** — Create confidence scoring: Combine retrieval score, citation support rate, answer completeness, and "no-answer" detection into a single confidence score. Return the breakdown along with the final number.
- [x] **Phase 4: Build Grounded Answer Generation** — Handle missing knowledge gracefully: If retrieval confidence is low, return a helpful "I could not find this in the docs" response with the closest matching sections. A real user can act on that response.
- [x] **Phase 5: Build the Evaluation Suite and Dashboard** — Create a golden Q&A set: Write 50-75 questions by hand. Include simple lookups, multi-doc questions, ambiguous questions, outdated-document traps, and questions that have no answer in the corpus.
- [x] **Phase 5: Build the Evaluation Suite and Dashboard** — Measure retrieval and answer quality separately: Track whether the right chunks were retrieved, whether the answer is correct, whether citations are valid, and whether the system correctly refused when the answer was missing.
- [x] **Phase 5: Build the Evaluation Suite and Dashboard** — Build the dashboard: Show the question, answer, retrieved chunks, citation verdicts, and confidence breakdown. Add a toggle to compare dense-only vs. hybrid retrieval.
- [x] **Phase 5: Build the Evaluation Suite and Dashboard** — Add an eval command: Create python eval.py --strategy hybrid and generate a Markdown or HTML report with metrics. This report is the artifact reviewers will open first.
- [x] **Phase 6: Polish for Portfolio** — Record a short walkthrough: Show ingestion, a good answer with verified citations, a failed citation being caught, and a no-answer case handled correctly.
- [x] **Phase 6: Polish for Portfolio** — Write the case study: Start with a measurable result like: "Hybrid retrieval improved correct-source retrieval from 72% to 88% on a 60-question eval set." Then explain the architecture and tradeoffs.

## 2. RAG Freshness and Drift Monitor

*Topic: RAG, Data Quality, Monitoring, Knowledge Drift*  
Folder: `07-rag-freshness-monitor/`

- [x] **Scaffold** — create `07-rag-freshness-monitor/` app skeleton: FastAPI app entry, `requirements.txt`, `config.py`, `.env.example`, `README.md`, `tests/` dir, and a `Dockerfile`. Wire a `/health` endpoint and a smoke test.
- [x] **Phase 1: Build a Baseline RAG Index** — Create a small knowledge base: Use internal-doc-style Markdown files: policies, product pages, troubleshooting docs, and changelogs.
- [x] **Phase 1: Build a Baseline RAG Index** — Index documents with metadata: Store document version, last modified date, source path, section heading, chunk hash, and embedding version.
- [x] **Phase 1: Build a Baseline RAG Index** — Save an index manifest: The manifest records what was indexed, when, with which embedding model, and with which chunking strategy.
- [x] **Phase 2: Detect Source-Level Freshness Issues** — Track content changes: Compare current document hashes to the manifest. Detect added, removed, and modified sections.
- [x] **Phase 2: Detect Source-Level Freshness Issues** — Score semantic change: A one-word typo should not trigger panic. Compute semantic similarity between old and new sections to estimate how meaningful the change is.
- [x] **Phase 2: Detect Source-Level Freshness Issues** — Prioritize re-indexing: Flag high-impact changes first: pricing, policy, API behavior, troubleshooting steps, and security instructions.
- [x] **Phase 3: Detect Retrieval Drift** — Build a probe question set: Create 50 recurring questions tied to known source sections.
- [x] **Phase 3: Detect Retrieval Drift** — Run probes against old and new indexes: Compare which chunks are retrieved and whether the top result changes after document updates.
- [x] **Phase 3: Detect Retrieval Drift** — Flag suspicious changes: If a known question no longer retrieves the expected section, mark it as retrieval drift.
- [x] **Phase 4: Detect Answer Drift** — Generate answers for probe questions: Run the same questions through the RAG pipeline over time.
- [x] **Phase 4: Detect Answer Drift** — Compare answers semantically: Use LLM-as-judge to identify whether the answer meaning changed, whether the change was expected, and whether citations still support the answer.
- [x] **Phase 4: Detect Answer Drift** — Track stale answer risk: If source docs changed but generated answers did not, the system may be serving stale knowledge. Flag this clearly.
- [x] **Phase 5: Build Alerts and Dashboard** — Build freshness scorecards: Show docs changed, chunks stale, probes drifting, answer drift, and re-index recommendations.
- [x] **Phase 5: Build Alerts and Dashboard** — Add alerts: Send Slack notifications when high-risk docs changed without re-indexing, or when probe questions fail.
- [x] **Phase 5: Build Alerts and Dashboard** — Add one-click rebuild command: From the dashboard, trigger re-indexing for affected docs and rerun probe tests.
- [ ] **Phase 6: Polish for Portfolio** — Demo a stale doc scenario: Change a policy document, show the system detecting risk, rebuild the index, and show probes returning to healthy.
- [ ] **Phase 6: Polish for Portfolio** — Write the narrative: Frame it as "monitoring for knowledge freshness in RAG systems." Most candidates do not have this lifecycle angle.

## 3. Permissioned Tool-Using Agent Sandbox

*Topic: Agents, Tool Use, Security, Human-in-the-Loop, Observability*  
Folder: `06-agent-sandbox/`

- [ ] **Scaffold** — create `06-agent-sandbox/` app skeleton: FastAPI app entry, `requirements.txt`, `config.py`, `.env.example`, `README.md`, `tests/` dir, and a `Dockerfile`. Wire a `/health` endpoint and a smoke test.
- [ ] **Phase 1: Design the Agent and Tool Model** — Define the agent role: Build a "workspace assistant" that can answer questions, inspect files, summarize data, call safe APIs, and prepare actions for approval.
- [ ] **Phase 1: Design the Agent and Tool Model** — Create a tool registry: Every tool has name, description, input schema, output schema, allowed roles, rate limit, risk level, and whether approval is required.
- [ ] **Phase 1: Design the Agent and Tool Model** — Build safe starter tools: Add calculator, file reader over a sandbox folder, web-search stub or mock search, CSV query tool, and ticket creation mock API.
- [ ] **Phase 2: Build Permission Checks** — Add user and role permissions: Users have roles like viewer, analyst, operator, and admin. Tools check permissions before execution.
- [ ] **Phase 2: Build Permission Checks** — Add risk levels: Low-risk tools execute immediately. Medium-risk tools require confirmation. High-risk tools require human approval before execution.
- [ ] **Phase 2: Build Permission Checks** — Block invalid tool inputs: Validate every tool call with Pydantic. Never let raw model text become a command without validation.
- [ ] **Phase 3: Build the LangGraph Workflow** — Create graph nodes: Intake, plan, tool selection, permission check, tool execution, result reflection, approval wait, final response.
- [ ] **Phase 3: Build the LangGraph Workflow** — Add conditional routing: If permission fails, return a safe explanation. If approval is needed, pause the task. If a tool fails, let the agent retry with a safer alternative.
- [ ] **Phase 3: Build the LangGraph Workflow** — Store task state: Persist every step so a paused task can resume after human approval.
- [ ] **Phase 4: Build Human Approval** — Create an approval queue: Show proposed action, tool name, arguments, risk level, model reasoning summary, and expected effect.
- [ ] **Phase 4: Build Human Approval** — Add approve / reject / modify: A human can approve as-is, edit the tool arguments, reject, or ask the agent to re-plan.
- [ ] **Phase 4: Build Human Approval** — Log decisions: Store who approved, what changed, and why. This keeps the agent auditable.
- [ ] **Phase 5: Build Observability** — Trace every decision: Capture prompts, chosen tools, permission decisions, tool outputs, retries, approval events, latency, and cost.
- [ ] **Phase 5: Build Observability** — Build a trace viewer: Show the workflow as a timeline. Clicking a step reveals inputs, outputs, and decision reasons.
- [ ] **Phase 5: Build Observability** — Add safety analytics: Track tool usage, blocked attempts, approval rate, rejected actions, and most common failure reasons.
- [ ] **Phase 6: Polish for Portfolio** — Demo a safe and unsafe task: Show the agent completing a low-risk analysis, then attempting a sensitive action that gets routed to approval.
- [ ] **Phase 6: Polish for Portfolio** — Write the architecture narrative: Focus on permission boundaries, audit logs, and human-in-the-loop design. Those details make the project feel production-minded.

## 4. Natural Language to API Assistant

*Topic: Tool Calling, Guardrails, OpenAPI, Workflow Automation*  
Folder: `08-nl-to-api-assistant/`

- [ ] **Scaffold** — create `08-nl-to-api-assistant/` app skeleton: FastAPI app entry, `requirements.txt`, `config.py`, `.env.example`, `README.md`, `tests/` dir, and a `Dockerfile`. Wire a `/health` endpoint and a smoke test.
- [ ] **Phase 1: Build the Mock Business API** — Create a realistic domain: Use a mock SaaS admin system with customers, subscriptions, invoices, tickets, and refunds.
- [ ] **Phase 1: Build the Mock Business API** — Expose OpenAPI docs: Build endpoints for read actions and write actions. Examples: get customer, list invoices, create ticket, update plan, issue refund.
- [ ] **Phase 1: Build the Mock Business API** — Add permission metadata: Mark each endpoint as read-only, low-risk write, or high-risk write. Include required roles.
- [ ] **Phase 2: Build Schema-Aware Planning** — Parse the OpenAPI schema: Extract endpoint names, descriptions, parameters, request bodies, response schemas, and risk tags.
- [ ] **Phase 2: Build Schema-Aware Planning** — Select relevant endpoints: Given a user request, retrieve candidate endpoints from the schema using embeddings or keyword search.
- [ ] **Phase 2: Build Schema-Aware Planning** — Generate a call plan: The LLM outputs a structured plan: endpoint, method, parameters, reason, expected result, and whether confirmation is required.
- [ ] **Phase 3: Build Validation and Dry Runs** — Validate parameters: Use JSON Schema and Pydantic before any API call. Reject missing, ambiguous, or invalid fields.
- [ ] **Phase 3: Build Validation and Dry Runs** — Add dry-run mode: For write actions, show what would happen without changing data. The assistant should explain the planned action in plain English.
- [ ] **Phase 3: Build Validation and Dry Runs** — Ask for confirmation: High-risk actions require explicit approval. Store the pending plan and resume only after confirmation.
- [ ] **Phase 4: Execute Multi-Step Workflows** — Support chained calls: Example: find customer by email, fetch subscription, check invoice status, then create a support ticket.
- [ ] **Phase 4: Execute Multi-Step Workflows** — Pass outputs between steps: Store intermediate results in a typed workflow state. Do not rely on unstructured memory.
- [ ] **Phase 4: Execute Multi-Step Workflows** — Handle failures gracefully: If an API call fails or returns multiple matches, ask a clarifying question instead of guessing.
- [ ] **Phase 5: Build Logs, UI, and Tests** — Log every plan and call: Capture user request, selected endpoints, parameters, validation result, approval status, API response, and final answer.
- [ ] **Phase 5: Build Logs, UI, and Tests** — Build a workflow UI: Show the user request, planned calls, dry-run preview, approval button, and final result.
- [ ] **Phase 5: Build Logs, UI, and Tests** — Create a golden workflow test suite: Write 40-50 natural language requests with expected endpoint plans. Include ambiguous and unsafe requests.
- [ ] **Phase 6: Polish for Portfolio** — Demo a full workflow: Show a read-only request, a multi-step workflow, and a high-risk write that requires approval.
- [ ] **Phase 6: Polish for Portfolio** — Write the narrative: Lead with "safe tool use over real API contracts." That phrase maps closely to the work many AI platform teams are doing.

## 5. Multimodal Document Intake Reviewer

*Topic: Multimodal AI, OCR, Structured Extraction, Human-in-the-Loop*  
Folder: `09-multimodal-doc-reviewer/`

- [ ] **Scaffold** — create `09-multimodal-doc-reviewer/` app skeleton: FastAPI app entry, `requirements.txt`, `config.py`, `.env.example`, `README.md`, `tests/` dir, and a `Dockerfile`. Wire a `/health` endpoint and a smoke test.
- [ ] **Phase 1: Build Document Upload and Preprocessing** — Accept multiple formats: Support PDFs, PNGs, JPEGs, and TIFFs. Store the original file and a normalized page image for each page.
- [ ] **Phase 1: Build Document Upload and Preprocessing** — Detect document type: Classify documents like invoice, reimbursement receipt, insurance claim, onboarding form, or contract summary.
- [ ] **Phase 1: Build Document Upload and Preprocessing** — Preprocess images: Add rotation correction, contrast enhancement, noise removal, and resolution checks. Track preprocessing steps in metadata.
- [ ] **Phase 2: Build OCR and Vision Fallback** — Run OCR first: Extract text with Tesseract or EasyOCR. Store text by page and line if possible.
- [ ] **Phase 2: Build OCR and Vision Fallback** — Estimate OCR confidence: Use OCR confidence scores, text density, and format sanity checks to decide whether OCR is usable.
- [ ] **Phase 2: Build OCR and Vision Fallback** — Use vision fallback: If OCR confidence is low, send the page image to a vision-capable model and ask it to preserve layout.
- [ ] **Phase 3: Extract Structured Data** — Define schemas by document type: For invoices, extract vendor, invoice number, dates, line items, tax, and total. For forms, extract applicant details and required fields.
- [ ] **Phase 3: Extract Structured Data** — Use structured output: The LLM should return data that validates against Pydantic. Include field-level source references where each value came from.
- [ ] **Phase 3: Extract Structured Data** — Handle long documents: Process by page or section and merge outputs. If two pages disagree, flag the conflict instead of hiding it.
- [ ] **Phase 4: Validate and Route** — Add type validation: Dates parse, totals are numbers, required fields exist, and enums are valid.
- [ ] **Phase 4: Validate and Route** — Add business rules: Invoice totals must equal line items plus tax. Claim dates must be within policy windows. Vendor names must match known vendors.
- [ ] **Phase 4: Validate and Route** — Route by confidence: High confidence goes auto-approved. Medium and low confidence go to review with reasons.
- [ ] **Phase 5: Build Human Review and Analytics** — Create side-by-side review: Show the document image and extracted fields. Clicking a field highlights its source area or page.
- [ ] **Phase 5: Build Human Review and Analytics** — Let reviewers correct fields: Store original value, corrected value, reviewer, and correction reason.
- [ ] **Phase 5: Build Human Review and Analytics** — Track accuracy by field: Show which fields fail most often, average review time, and auto-approval rate.
- [ ] **Phase 6: Polish for Portfolio** — Demo a messy document: Use a slightly rotated scan or screenshot where OCR is imperfect. Show extraction, validation, review, and correction.
- [ ] **Phase 6: Polish for Portfolio** — Use operational metrics: Example: "Auto-approved 64% of sample documents while routing low-confidence fields to review."
