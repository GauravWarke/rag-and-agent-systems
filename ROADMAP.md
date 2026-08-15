# ROADMAP

Single source of truth for the scheduled builder. It reads this file top-to-bottom, finds the **first unchecked `- [ ]` item**, implements exactly that one item, checks it off, and opens a PR.

Convention: each item is scoped to be completable in one run. Keep items in order; do not skip. Project 1 (Support Knowledge Copilot) is the active flagship and is ordered first.

Legend: `- [ ]` todo · `- [x]` done · **(P#)** project number.

---

## P1: Support Knowledge Copilot with Verified Citations

*Topic: RAG, Hybrid Retrieval, Citation Verification, Retrieval Evaluation*  
Folder: `01-support-knowledge-copilot/`

- [x] **(P1) Scaffold** — create `01-support-knowledge-copilot/` app skeleton: FastAPI app entry, `requirements.txt`, `config.py`, `.env.example`, `README.md`, `tests/` dir, and a `Dockerfile`. Wire a `/health` endpoint and a smoke test.
- [x] **(P1) Phase 1: Define the Knowledge Assistant Scope** — Pick a realistic document set: Use a small but believable support corpus: product FAQs, troubleshooting guides, onboarding docs, API docs, release notes, and policy pages. The corpus should have overlapping information so retrieval is not too easy.
- [x] **(P1) Phase 1: Define the Knowledge Assistant Scope** — Define the assistant contract: Input is a user question. Output is an answer, source citations, confidence score, and a short "what I could not verify" section. This contract matters because production RAG systems need to be honest about uncertainty.
- [x] **(P1) Phase 1: Define the Knowledge Assistant Scope** — Create metadata rules: Every document should include source name, section heading, last updated date, document type, and access level. Store this metadata from the beginning so you can filter retrieval later.
- [x] **(P1) Phase 2: Build Ingestion and Chunking** — Normalize documents into clean text: Write loaders for Markdown, HTML, text files, and PDFs. Preserve headings and page numbers wherever possible. Store both raw and cleaned versions so you can debug indexing issues.
- [x] **(P1) Phase 2: Build Ingestion and Chunking** — Implement multiple chunking strategies: Start with recursive heading-based chunking, then add fixed-size chunking with overlap. Track which strategy produced each chunk so you can compare performance later.
- [x] **(P1) Phase 2: Build Ingestion and Chunking** — Generate embeddings and indexes: Embed every chunk and store it in the vector database. Build a BM25 index over the same chunk IDs. Both indexes should point to the same metadata so the fusion layer is clean.
- [x] **(P1) Phase 2: Build Ingestion and Chunking** — Add a re-index command: Build a CLI command like python ingest.py --source docs/ --rebuild. This keeps it closer to how a teammate would use the tool.
- [x] **(P1) Phase 3: Build Hybrid Retrieval** — Implement dense retrieval: Embed the user question and retrieve the top-k closest chunks by cosine similarity. Store the raw similarity score for debugging.
- [x] **(P1) Phase 3: Build Hybrid Retrieval** — Implement sparse retrieval: Run BM25 over the same question and retrieve keyword-relevant chunks. This is especially useful for exact phrases, API names, SKUs, and error codes.
- [x] **(P1) Phase 3: Build Hybrid Retrieval** — Fuse results with RRF: Use Reciprocal Rank Fusion to merge dense and sparse result lists. Make the weights configurable so you can show how retrieval changes under different settings.
- [x] **(P1) Phase 3: Build Hybrid Retrieval** — Add a reranking pass: Rerank the top 20 fused chunks using a small cross-encoder or LLM-as-reranker. Keep the top 5 chunks for generation.
- [x] **(P1) Phase 4: Build Grounded Answer Generation** — Design the answer prompt: Tell the model to answer only from provided context, cite claims using chunk IDs, and say when the answer is not available. Keep the prompt simple and strict.
- [x] **(P1) Phase 4: Build Grounded Answer Generation** — Verify citations after generation: Parse citations from the answer and check whether each cited chunk supports the claim. Use an LLM-as-judge or rule-based claim extraction for V1.
- [x] **(P1) Phase 4: Build Grounded Answer Generation** — Create confidence scoring: Combine retrieval score, citation support rate, answer completeness, and "no-answer" detection into a single confidence score. Return the breakdown along with the final number.
- [x] **(P1) Phase 4: Build Grounded Answer Generation** — Handle missing knowledge gracefully: If retrieval confidence is low, return a helpful "I could not find this in the docs" response with the closest matching sections. A real user can act on that response.
- [x] **(P1) Phase 5: Build the Evaluation Suite and Dashboard** — Create a golden Q&A set: Write 50-75 questions by hand. Include simple lookups, multi-doc questions, ambiguous questions, outdated-document traps, and questions that have no answer in the corpus.
- [x] **(P1) Phase 5: Build the Evaluation Suite and Dashboard** — Measure retrieval and answer quality separately: Track whether the right chunks were retrieved, whether the answer is correct, whether citations are valid, and whether the system correctly refused when the answer was missing.
- [x] **(P1) Phase 5: Build the Evaluation Suite and Dashboard** — Build the dashboard: Show the question, answer, retrieved chunks, citation verdicts, and confidence breakdown. Add a toggle to compare dense-only vs. hybrid retrieval.
- [x] **(P1) Phase 5: Build the Evaluation Suite and Dashboard** — Add an eval command: Create python eval.py --strategy hybrid and generate a Markdown or HTML report with metrics. This report is the artifact reviewers will open first.
- [x] **(P1) Phase 6: Polish for Portfolio** — Record a short walkthrough: Show ingestion, a good answer with verified citations, a failed citation being caught, and a no-answer case handled correctly.
- [x] **(P1) Phase 6: Polish for Portfolio** — Write the case study: Start with a measurable result like: "Hybrid retrieval improved correct-source retrieval from 72% to 88% on a 60-question eval set." Then explain the architecture and tradeoffs.

## P2: Prompt Release Safety Gate

*Topic: LLMOps, PromptOps, CI/CD, Regression Testing, Evals*  
Folder: `02-prompt-release-safety-gate/`

- [x] **(P2) Scaffold** — create `02-prompt-release-safety-gate/` app skeleton: FastAPI app entry, `requirements.txt`, `config.py`, `.env.example`, `README.md`, `tests/` dir, and a `Dockerfile`. Wire a `/health` endpoint and a smoke test.
- [x] **(P2) Phase 1: Pick the AI Feature Under Test** — Build a small production-like feature: Create an AI feature such as "turn messy customer notes into a clean CRM summary." The output should be structured: summary, sentiment, next action, urgency, and confidence.
- [x] **(P2) Phase 1: Pick the AI Feature Under Test** — Store prompts as versioned YAML: Put prompts in /prompts. Each file should include version, owner, description, model settings, system prompt, few-shot examples, and expected output schema.
- [x] **(P2) Phase 1: Pick the AI Feature Under Test** — Define the response contract: Use Pydantic to validate the output. A prompt that returns beautiful prose but breaks the schema should fail the release gate.
- [x] **(P2) Phase 2: Build the Golden Test Set** — Hand-write realistic examples: Create 75-100 messy notes with expected structured outputs. Include spelling mistakes, vague requests, emotional customers, missing context, and mixed-intent notes.
- [x] **(P2) Phase 2: Build the Golden Test Set** — Label edge cases clearly: Add fields like difficulty, risk_area, and why_this_case_exists. These notes make your dataset feel intentionally designed instead of randomly generated.
- [x] **(P2) Phase 2: Build the Golden Test Set** — Version the dataset: Store it in JSONL with stable IDs. When you update the dataset, write a changelog. This shows that the eval bar is managed too, not treated as a one-time file.
- [x] **(P2) Phase 3: Build the Regression Runner** — Run baseline and candidate prompts: For every test case, call the production prompt and the changed prompt. Store raw outputs, parsed outputs, latency, token counts, and model errors.
- [x] **(P2) Phase 3: Build the Regression Runner** — Score multiple dimensions: Measure schema validity, field-level correctness, summary relevance, next-action usefulness, safety issues, latency, and cost. Do not collapse everything into one vague score too early.
- [x] **(P2) Phase 3: Build the Regression Runner** — Compare run-over-run: Identify cases that passed before but fail now, cases that improved, categories that regressed, and cost/latency changes. This diff is the core value of the project.
- [x] **(P2) Phase 3: Build the Regression Runner** — Add thresholds: Create warning and blocking thresholds. Example: block if schema validity drops by more than 2%, safety failures increase, or average cost rises by more than 20%.
- [x] **(P2) Phase 4: Build Reports and PR Comments** — Generate a release report: Include a scorecard, regression table, examples of changed outputs, cost delta, latency delta, and recommended release decision.
- [x] **(P2) Phase 4: Build Reports and PR Comments** — Add side-by-side output diffs: For every failed case, show input, baseline output, candidate output, expected output, and the scoring explanation.
- [x] **(P2) Phase 4: Build Reports and PR Comments** — Post a PR comment: The GitHub Action should post a short summary: pass/warn/fail, top regressions, metric deltas, and a link to the full report artifact.
- [x] **(P2) Phase 5: Wire into CI/CD** — Trigger only when prompts change: Configure GitHub Actions to run when files under /prompts or /evals change. Keep the workflow efficient.
- [x] **(P2) Phase 5: Wire into CI/CD** — Block risky merges: If the result is critical, exit non-zero so the PR cannot merge. If it is warning-only, allow merge but leave a visible warning.
- [x] **(P2) Phase 5: Wire into CI/CD** — Package the runner: Add a Dockerfile so the same runner works locally and in CI. Expose environment variables for API keys, thresholds, and model choice.
- [x] **(P2) Phase 6: Polish for Portfolio** — Create a demo PR: Intentionally change a prompt so it gets more verbose, more expensive, or less accurate. Show the safety gate catching it.
- [x] **(P2) Phase 6: Polish for Portfolio** — Write your README like team documentation: Include setup, how to add test cases, how to adjust thresholds, and what decisions you made around LLM-as-judge scoring.

## P3: LLM Spend Control Center

*Topic: LLMOps, Cost Optimization, Model Routing, Budget Monitoring*  
Folder: `03-llm-spend-control-center/`

- [x] **(P3) Scaffold** — create `03-llm-spend-control-center/` app skeleton: FastAPI app entry, `requirements.txt`, `config.py`, `.env.example`, `README.md`, `tests/` dir, and a `Dockerfile`. Wire a `/health` endpoint and a smoke test.
- [x] **(P3) Phase 1: Build the Unified Request Gateway** — Define a standard request format: Accept chat-style input, team ID, feature name, priority, and optional model preference. Normalize all provider responses into one response schema.
- [x] **(P3) Phase 1: Build the Unified Request Gateway** — Create a model registry: Store model name, provider, quality tier, input cost, output cost, latency estimate, max context length, and supported features like vision or tool calling.
- [x] **(P3) Phase 1: Build the Unified Request Gateway** — Build provider adapters: Implement one adapter per provider. Each adapter should return output text, token counts, latency, cost, and provider metadata.
- [x] **(P3) Phase 2: Build Cost Tracking and Budgets** — Log every request: Store timestamp, team ID, feature, model used, input/output tokens, latency, status, and cost. Make this audit trail queryable.
- [x] **(P3) Phase 2: Build Cost Tracking and Budgets** — Add budget policies: Each team or feature gets daily and monthly limits. Track spend against those limits in real time.
- [x] **(P3) Phase 2: Build Cost Tracking and Budgets** — Create warning and block behavior: At 80% budget, send warning alerts. At 100%, block low-priority requests or require override. Return clear errors instead of silently failing.
- [x] **(P3) Phase 3: Build Request Complexity Routing** — Define routing tiers: Tier 1 is extraction and formatting. Tier 2 is summarization and classification. Tier 3 is reasoning-heavy or high-risk work.
- [x] **(P3) Phase 3: Build Request Complexity Routing** — Build a lightweight classifier: Use features like prompt length, instruction verbs, required output format, context size, and risk tags. A simple model is fine; the architecture matters more than perfect ML.
- [x] **(P3) Phase 3: Build Request Complexity Routing** — Map tiers to models: Route simple work to cheaper models, moderate work to mid-tier models, and risky work to high-quality models. Store this mapping in YAML or database config.
- [x] **(P3) Phase 3: Build Request Complexity Routing** — Add override rules: Some features should always use a stronger model because correctness matters more than cost. Make those rules explicit.
- [x] **(P3) Phase 4: Add Quality Checks and Escalation** — Sample responses for verification: For a percentage of requests routed to cheaper models, asynchronously compare output quality against a stronger model.
- [x] **(P3) Phase 4: Add Quality Checks and Escalation** — Detect bad routing decisions: If the cheap model fails a quality check, mark the request as a routing miss. Store the prompt, chosen model, better model, and reason.
- [x] **(P3) Phase 4: Add Quality Checks and Escalation** — Add auto-escalation for high-risk requests: If confidence is low or the request is tagged high-priority, rerun with a stronger model before returning the final answer.
- [x] **(P3) Phase 5: Build the Cost Dashboard** — Show spend by team and feature: Include daily cost, monthly projection, top expensive prompts, and cost by model.
- [x] **(P3) Phase 5: Build the Cost Dashboard** — Show savings estimates: Compare actual routed spend with "everything sent to the strongest model." This gives you the main metric for the case study.
- [x] **(P3) Phase 5: Build the Cost Dashboard** — Add routing quality metrics: Show escalation rate, verifier pass rate, latency by model, and error rate by provider.
- [x] **(P3) Phase 6: Polish for Portfolio** — Run a simulated workload: Send 1,000 mixed prompts through the gateway and produce a cost savings report.
- [x] **(P3) Phase 6: Polish for Portfolio** — Write the case study: Start with: "Reduced simulated LLM spend by X% while maintaining Y% verification pass rate." Then show the routing design and budget enforcement flow.

## P4: AI Output Policy Guardrail Service

*Topic: Guardrails, Safety, Compliance, Structured Validation*  
Folder: `04-output-policy-guardrail/`

- [x] **(P4) Scaffold** — create `04-output-policy-guardrail/` app skeleton: FastAPI app entry, `requirements.txt`, `config.py`, `.env.example`, `README.md`, `tests/` dir, and a `Dockerfile`. Wire a `/health` endpoint and a smoke test.
- [x] **(P4) Phase 1: Define Policies and Decision Types** — Create policy categories: Start with PII leakage, unsupported factual claims, toxic language, unsafe instructions, medical/legal/financial overconfidence, schema mismatch, and brand voice violations.
- [x] **(P4) Phase 1: Define Policies and Decision Types** — Define decision outcomes: The guardrail can approve, approve with warning, rewrite, block, or send to human review. Keep these outcomes simple and explainable.
- [x] **(P4) Phase 1: Define Policies and Decision Types** — Build policy files: Store policies in YAML with rule name, severity, examples, detection strategy, and recommended action. This keeps the service auditable.
- [x] **(P4) Phase 2: Build Deterministic Validators** — Add schema validation: If an AI feature expects JSON, validate it before anything else. Bad format is the easiest failure to catch and the most common to ignore.
- [x] **(P4) Phase 2: Build Deterministic Validators** — Add PII detection: Detect emails, phone numbers, addresses, API keys, credit card-like strings, and named entities. Allow per-feature configuration because not all PII is always forbidden.
- [x] **(P4) Phase 2: Build Deterministic Validators** — Add forbidden content checks: Use regex and keyword rules for obvious policy violations. Deterministic checks should catch cheap, clear failures before using an LLM judge.
- [x] **(P4) Phase 3: Build LLM-Based Policy Review** — Create judge prompts per policy: The judge receives the original prompt, candidate output, policy text, and examples. It returns structured findings with severity and evidence.
- [x] **(P4) Phase 3: Build LLM-Based Policy Review** — Require evidence for every finding: The judge should cite the exact output span that triggered the issue. This keeps the decision reviewable.
- [x] **(P4) Phase 3: Build LLM-Based Policy Review** — Add confidence and disagreement: Run two judge passes for high-risk outputs. If judges disagree, route to human review instead of pretending certainty.
- [x] **(P4) Phase 4: Build Rewrite and Block Flows** — Implement safe rewrites: For fixable issues, rewrite only the problematic parts while preserving the useful answer. Examples: remove PII, soften overconfident claims, add uncertainty, or repair JSON.
- [x] **(P4) Phase 4: Build Rewrite and Block Flows** — Block non-fixable outputs: For serious safety issues, return a structured block response with reason codes. Do not expose internal policy text unnecessarily.
- [x] **(P4) Phase 4: Build Rewrite and Block Flows** — Log every decision: Store input hash, output hash, policy version, findings, action taken, latency, and final output. Auditability is the point.
- [x] **(P4) Phase 5: Build the Review Dashboard** — Create an audit queue: Human reviewers can inspect blocked or uncertain decisions, approve rewrites, override false positives, and leave notes.
- [x] **(P4) Phase 5: Build the Review Dashboard** — Track policy performance: Show block rate, rewrite rate, false-positive rate, average latency, and most common violation types.
- [x] **(P4) Phase 5: Build the Review Dashboard** — Add policy version comparison: When a policy changes, show how decisions would differ on historical examples. This prevents policy updates from causing chaos.
- [x] **(P4) Phase 6: Polish for Portfolio** — Demo multiple outcomes: Show an approved output, a rewritten output, a blocked output, and a human-review case.
- [x] **(P4) Phase 6: Polish for Portfolio** — Write the narrative: Position it as "a policy enforcement layer for LLM outputs," not a moderation toy. Put audit logs and decision transparency near the top.

## P5: Production Log-to-Eval Dataset Builder

*Topic: Evals, Data Flywheel, LLMOps, Human Review*  
Folder: `05-log-to-eval-dataset-builder/`

- [x] **(P5) Scaffold** — create `05-log-to-eval-dataset-builder/` app skeleton: FastAPI app entry, `requirements.txt`, `config.py`, `.env.example`, `README.md`, `tests/` dir, and a `Dockerfile`. Wire a `/health` endpoint and a smoke test.
- [x] **(P5) Phase 1: Design the Log Schema** — Define the unified log format: Capture prompt, system prompt, response, model, feature name, latency, token counts, user feedback, retry count, error status, and timestamp.
- [x] **(P5) Phase 1: Design the Log Schema** — Add privacy controls: Build redaction rules for emails, phone numbers, secrets, and names. Store both redaction status and redaction method.
- [x] **(P5) Phase 1: Design the Log Schema** — Seed synthetic logs: Create 1,000 simulated logs across a few features. Include good responses, bad responses, user retries, malformed outputs, and safety edge cases.
- [x] **(P5) Phase 2: Sample and Classify Interactions** — Build sampling modes: Implement random sampling, failure-biased sampling, and diversity sampling. Failure-biased sampling should over-select logs with negative feedback, retries, or errors.
- [x] **(P5) Phase 2: Sample and Classify Interactions** — Cluster prompts: Embed prompts and cluster them to discover common categories. Give each cluster a human-readable label using representative examples.
- [x] **(P5) Phase 2: Sample and Classify Interactions** — Identify high-value candidates: Prioritize unusual prompts, low-quality outputs, high-impact features, edge cases, and clusters with poor eval coverage.
- [x] **(P5) Phase 3: Auto-Generate Eval Labels** — Decide eval type per example: Some examples need a golden answer. Others need a rubric. Some need expected refusal. Pick the label type based on the interaction.
- [x] **(P5) Phase 3: Auto-Generate Eval Labels** — Generate labels with confidence: Use a strong model to propose expected behavior, key assertions, forbidden assertions, and scoring rubric. Run multiple passes for important examples.
- [x] **(P5) Phase 3: Auto-Generate Eval Labels** — Deduplicate aggressively: Compare against existing eval cases and skip near-duplicates. Track why each candidate was accepted or rejected.
- [x] **(P5) Phase 4: Build Human Review** — Create a review queue: Low-confidence labels go to reviewers. Show the original interaction, proposed labels, similar existing cases, and quick approve/edit/reject actions.
- [x] **(P5) Phase 4: Build Human Review** — Track reviewer edits: Store what changed and why. Use this to improve labeling prompts and measure auto-label quality.
- [x] **(P5) Phase 4: Build Human Review** — Add dataset status: Every eval case should be draft, approved, rejected, or deprecated. This prevents messy datasets.
- [x] **(P5) Phase 5: Connect to an Eval Runner** — Export approved cases to JSONL: Keep the output format simple: input, expected behavior, rubric, tags, difficulty, source cluster, and date added.
- [x] **(P5) Phase 5: Connect to an Eval Runner** — Run nightly evals: Execute the growing dataset against a model endpoint and compare performance to the previous run.
- [x] **(P5) Phase 5: Connect to an Eval Runner** — Track dataset health: Show total cases, cases by category, cases by difficulty, freshness, auto-labeled percentage, and human-reviewed percentage.
- [x] **(P5) Phase 6: Polish for Portfolio** — Show the flywheel: Demo logs entering the system, candidates being selected, labels being generated, humans approving, and the eval dataset growing.
- [x] **(P5) Phase 6: Polish for Portfolio** — Use dataset numbers: Example: "Generated 300 approved eval cases across 12 categories from 5,000 simulated production logs, with 82% auto-label acceptance after review."

## P6: Permissioned Tool-Using Agent Sandbox

*Topic: Agents, Tool Use, Security, Human-in-the-Loop, Observability*  
Folder: `06-agent-sandbox/`

- [x] **(P6) Scaffold** — create `06-agent-sandbox/` app skeleton: FastAPI app entry, `requirements.txt`, `config.py`, `.env.example`, `README.md`, `tests/` dir, and a `Dockerfile`. Wire a `/health` endpoint and a smoke test.
- [x] **(P6) Phase 1: Design the Agent and Tool Model** — Define the agent role: Build a "workspace assistant" that can answer questions, inspect files, summarize data, call safe APIs, and prepare actions for approval.
- [x] **(P6) Phase 1: Design the Agent and Tool Model** — Create a tool registry: Every tool has name, description, input schema, output schema, allowed roles, rate limit, risk level, and whether approval is required.
- [x] **(P6) Phase 1: Design the Agent and Tool Model** — Build safe starter tools: Add calculator, file reader over a sandbox folder, web-search stub or mock search, CSV query tool, and ticket creation mock API.
- [x] **(P6) Phase 2: Build Permission Checks** — Add user and role permissions: Users have roles like viewer, analyst, operator, and admin. Tools check permissions before execution.
- [x] **(P6) Phase 2: Build Permission Checks** — Add risk levels: Low-risk tools execute immediately. Medium-risk tools require confirmation. High-risk tools require human approval before execution.
- [x] **(P6) Phase 2: Build Permission Checks** — Block invalid tool inputs: Validate every tool call with Pydantic. Never let raw model text become a command without validation.
- [x] **(P6) Phase 3: Build the LangGraph Workflow** — Create graph nodes: Intake, plan, tool selection, permission check, tool execution, result reflection, approval wait, final response.
- [x] **(P6) Phase 3: Build the LangGraph Workflow** — Add conditional routing: If permission fails, return a safe explanation. If approval is needed, pause the task. If a tool fails, let the agent retry with a safer alternative.
- [x] **(P6) Phase 3: Build the LangGraph Workflow** — Store task state: Persist every step so a paused task can resume after human approval.
- [x] **(P6) Phase 4: Build Human Approval** — Create an approval queue: Show proposed action, tool name, arguments, risk level, model reasoning summary, and expected effect.
- [x] **(P6) Phase 4: Build Human Approval** — Add approve / reject / modify: A human can approve as-is, edit the tool arguments, reject, or ask the agent to re-plan.
- [x] **(P6) Phase 4: Build Human Approval** — Log decisions: Store who approved, what changed, and why. This keeps the agent auditable.
- [x] **(P6) Phase 5: Build Observability** — Trace every decision: Capture prompts, chosen tools, permission decisions, tool outputs, retries, approval events, latency, and cost.
- [x] **(P6) Phase 5: Build Observability** — Build a trace viewer: Show the workflow as a timeline. Clicking a step reveals inputs, outputs, and decision reasons.
- [x] **(P6) Phase 5: Build Observability** — Add safety analytics: Track tool usage, blocked attempts, approval rate, rejected actions, and most common failure reasons.
- [x] **(P6) Phase 6: Polish for Portfolio** — Demo a safe and unsafe task: Show the agent completing a low-risk analysis, then attempting a sensitive action that gets routed to approval.
- [ ] **(P6) Phase 6: Polish for Portfolio** — Write the architecture narrative: Focus on permission boundaries, audit logs, and human-in-the-loop design. Those details make the project feel production-minded.

## P7: RAG Freshness and Drift Monitor

*Topic: RAG, Data Quality, Monitoring, Knowledge Drift*  
Folder: `07-rag-freshness-monitor/`

- [ ] **(P7) Scaffold** — create `07-rag-freshness-monitor/` app skeleton: FastAPI app entry, `requirements.txt`, `config.py`, `.env.example`, `README.md`, `tests/` dir, and a `Dockerfile`. Wire a `/health` endpoint and a smoke test.
- [ ] **(P7) Phase 1: Build a Baseline RAG Index** — Create a small knowledge base: Use internal-doc-style Markdown files: policies, product pages, troubleshooting docs, and changelogs.
- [ ] **(P7) Phase 1: Build a Baseline RAG Index** — Index documents with metadata: Store document version, last modified date, source path, section heading, chunk hash, and embedding version.
- [ ] **(P7) Phase 1: Build a Baseline RAG Index** — Save an index manifest: The manifest records what was indexed, when, with which embedding model, and with which chunking strategy.
- [ ] **(P7) Phase 2: Detect Source-Level Freshness Issues** — Track content changes: Compare current document hashes to the manifest. Detect added, removed, and modified sections.
- [ ] **(P7) Phase 2: Detect Source-Level Freshness Issues** — Score semantic change: A one-word typo should not trigger panic. Compute semantic similarity between old and new sections to estimate how meaningful the change is.
- [ ] **(P7) Phase 2: Detect Source-Level Freshness Issues** — Prioritize re-indexing: Flag high-impact changes first: pricing, policy, API behavior, troubleshooting steps, and security instructions.
- [ ] **(P7) Phase 3: Detect Retrieval Drift** — Build a probe question set: Create 50 recurring questions tied to known source sections.
- [ ] **(P7) Phase 3: Detect Retrieval Drift** — Run probes against old and new indexes: Compare which chunks are retrieved and whether the top result changes after document updates.
- [ ] **(P7) Phase 3: Detect Retrieval Drift** — Flag suspicious changes: If a known question no longer retrieves the expected section, mark it as retrieval drift.
- [ ] **(P7) Phase 4: Detect Answer Drift** — Generate answers for probe questions: Run the same questions through the RAG pipeline over time.
- [ ] **(P7) Phase 4: Detect Answer Drift** — Compare answers semantically: Use LLM-as-judge to identify whether the answer meaning changed, whether the change was expected, and whether citations still support the answer.
- [ ] **(P7) Phase 4: Detect Answer Drift** — Track stale answer risk: If source docs changed but generated answers did not, the system may be serving stale knowledge. Flag this clearly.
- [ ] **(P7) Phase 5: Build Alerts and Dashboard** — Build freshness scorecards: Show docs changed, chunks stale, probes drifting, answer drift, and re-index recommendations.
- [ ] **(P7) Phase 5: Build Alerts and Dashboard** — Add alerts: Send Slack notifications when high-risk docs changed without re-indexing, or when probe questions fail.
- [ ] **(P7) Phase 5: Build Alerts and Dashboard** — Add one-click rebuild command: From the dashboard, trigger re-indexing for affected docs and rerun probe tests.
- [ ] **(P7) Phase 6: Polish for Portfolio** — Demo a stale doc scenario: Change a policy document, show the system detecting risk, rebuild the index, and show probes returning to healthy.
- [ ] **(P7) Phase 6: Polish for Portfolio** — Write the narrative: Frame it as "monitoring for knowledge freshness in RAG systems." Most candidates do not have this lifecycle angle.

## P8: Natural Language to API Assistant

*Topic: Tool Calling, Guardrails, OpenAPI, Workflow Automation*  
Folder: `08-nl-to-api-assistant/`

- [ ] **(P8) Scaffold** — create `08-nl-to-api-assistant/` app skeleton: FastAPI app entry, `requirements.txt`, `config.py`, `.env.example`, `README.md`, `tests/` dir, and a `Dockerfile`. Wire a `/health` endpoint and a smoke test.
- [ ] **(P8) Phase 1: Build the Mock Business API** — Create a realistic domain: Use a mock SaaS admin system with customers, subscriptions, invoices, tickets, and refunds.
- [ ] **(P8) Phase 1: Build the Mock Business API** — Expose OpenAPI docs: Build endpoints for read actions and write actions. Examples: get customer, list invoices, create ticket, update plan, issue refund.
- [ ] **(P8) Phase 1: Build the Mock Business API** — Add permission metadata: Mark each endpoint as read-only, low-risk write, or high-risk write. Include required roles.
- [ ] **(P8) Phase 2: Build Schema-Aware Planning** — Parse the OpenAPI schema: Extract endpoint names, descriptions, parameters, request bodies, response schemas, and risk tags.
- [ ] **(P8) Phase 2: Build Schema-Aware Planning** — Select relevant endpoints: Given a user request, retrieve candidate endpoints from the schema using embeddings or keyword search.
- [ ] **(P8) Phase 2: Build Schema-Aware Planning** — Generate a call plan: The LLM outputs a structured plan: endpoint, method, parameters, reason, expected result, and whether confirmation is required.
- [ ] **(P8) Phase 3: Build Validation and Dry Runs** — Validate parameters: Use JSON Schema and Pydantic before any API call. Reject missing, ambiguous, or invalid fields.
- [ ] **(P8) Phase 3: Build Validation and Dry Runs** — Add dry-run mode: For write actions, show what would happen without changing data. The assistant should explain the planned action in plain English.
- [ ] **(P8) Phase 3: Build Validation and Dry Runs** — Ask for confirmation: High-risk actions require explicit approval. Store the pending plan and resume only after confirmation.
- [ ] **(P8) Phase 4: Execute Multi-Step Workflows** — Support chained calls: Example: find customer by email, fetch subscription, check invoice status, then create a support ticket.
- [ ] **(P8) Phase 4: Execute Multi-Step Workflows** — Pass outputs between steps: Store intermediate results in a typed workflow state. Do not rely on unstructured memory.
- [ ] **(P8) Phase 4: Execute Multi-Step Workflows** — Handle failures gracefully: If an API call fails or returns multiple matches, ask a clarifying question instead of guessing.
- [ ] **(P8) Phase 5: Build Logs, UI, and Tests** — Log every plan and call: Capture user request, selected endpoints, parameters, validation result, approval status, API response, and final answer.
- [ ] **(P8) Phase 5: Build Logs, UI, and Tests** — Build a workflow UI: Show the user request, planned calls, dry-run preview, approval button, and final result.
- [ ] **(P8) Phase 5: Build Logs, UI, and Tests** — Create a golden workflow test suite: Write 40-50 natural language requests with expected endpoint plans. Include ambiguous and unsafe requests.
- [ ] **(P8) Phase 6: Polish for Portfolio** — Demo a full workflow: Show a read-only request, a multi-step workflow, and a high-risk write that requires approval.
- [ ] **(P8) Phase 6: Polish for Portfolio** — Write the narrative: Lead with "safe tool use over real API contracts." That phrase maps closely to the work many AI platform teams are doing.

## P9: Multimodal Document Intake Reviewer

*Topic: Multimodal AI, OCR, Structured Extraction, Human-in-the-Loop*  
Folder: `09-multimodal-doc-reviewer/`

- [ ] **(P9) Scaffold** — create `09-multimodal-doc-reviewer/` app skeleton: FastAPI app entry, `requirements.txt`, `config.py`, `.env.example`, `README.md`, `tests/` dir, and a `Dockerfile`. Wire a `/health` endpoint and a smoke test.
- [ ] **(P9) Phase 1: Build Document Upload and Preprocessing** — Accept multiple formats: Support PDFs, PNGs, JPEGs, and TIFFs. Store the original file and a normalized page image for each page.
- [ ] **(P9) Phase 1: Build Document Upload and Preprocessing** — Detect document type: Classify documents like invoice, reimbursement receipt, insurance claim, onboarding form, or contract summary.
- [ ] **(P9) Phase 1: Build Document Upload and Preprocessing** — Preprocess images: Add rotation correction, contrast enhancement, noise removal, and resolution checks. Track preprocessing steps in metadata.
- [ ] **(P9) Phase 2: Build OCR and Vision Fallback** — Run OCR first: Extract text with Tesseract or EasyOCR. Store text by page and line if possible.
- [ ] **(P9) Phase 2: Build OCR and Vision Fallback** — Estimate OCR confidence: Use OCR confidence scores, text density, and format sanity checks to decide whether OCR is usable.
- [ ] **(P9) Phase 2: Build OCR and Vision Fallback** — Use vision fallback: If OCR confidence is low, send the page image to a vision-capable model and ask it to preserve layout.
- [ ] **(P9) Phase 3: Extract Structured Data** — Define schemas by document type: For invoices, extract vendor, invoice number, dates, line items, tax, and total. For forms, extract applicant details and required fields.
- [ ] **(P9) Phase 3: Extract Structured Data** — Use structured output: The LLM should return data that validates against Pydantic. Include field-level source references where each value came from.
- [ ] **(P9) Phase 3: Extract Structured Data** — Handle long documents: Process by page or section and merge outputs. If two pages disagree, flag the conflict instead of hiding it.
- [ ] **(P9) Phase 4: Validate and Route** — Add type validation: Dates parse, totals are numbers, required fields exist, and enums are valid.
- [ ] **(P9) Phase 4: Validate and Route** — Add business rules: Invoice totals must equal line items plus tax. Claim dates must be within policy windows. Vendor names must match known vendors.
- [ ] **(P9) Phase 4: Validate and Route** — Route by confidence: High confidence goes auto-approved. Medium and low confidence go to review with reasons.
- [ ] **(P9) Phase 5: Build Human Review and Analytics** — Create side-by-side review: Show the document image and extracted fields. Clicking a field highlights its source area or page.
- [ ] **(P9) Phase 5: Build Human Review and Analytics** — Let reviewers correct fields: Store original value, corrected value, reviewer, and correction reason.
- [ ] **(P9) Phase 5: Build Human Review and Analytics** — Track accuracy by field: Show which fields fail most often, average review time, and auto-approval rate.
- [ ] **(P9) Phase 6: Polish for Portfolio** — Demo a messy document: Use a slightly rotated scan or screenshot where OCR is imperfect. Show extraction, validation, review, and correction.
- [ ] **(P9) Phase 6: Polish for Portfolio** — Use operational metrics: Example: "Auto-approved 64% of sample documents while routing low-confidence fields to review."

## P10: Fine-Tune vs RAG Decision Lab

*Topic: MLOps, Fine-Tuning, RAG, Benchmarking, Model Selection*  
Folder: `10-finetune-vs-rag-lab/`

- [ ] **(P10) Scaffold** — create `10-finetune-vs-rag-lab/` app skeleton: FastAPI app entry, `requirements.txt`, `config.py`, `.env.example`, `README.md`, `tests/` dir, and a `Dockerfile`. Wire a `/health` endpoint and a smoke test.
- [ ] **(P10) Phase 1: Choose a Narrow Domain Task** — Pick a measurable task: Good examples: support macro selection, policy clause classification, bug report severity prediction, or domain-specific email rewrite.
- [ ] **(P10) Phase 1: Choose a Narrow Domain Task** — Build a dataset: Create 500-1,500 examples with instruction, input, expected output, category, and difficulty. Clean duplicates and formatting issues.
- [ ] **(P10) Phase 1: Choose a Narrow Domain Task** — Create a benchmark: Hold out 100 examples as a fixed test set. Add 30 hard edge cases by hand.
- [ ] **(P10) Phase 2: Build the Prompt-Only Baseline** — Write a strong prompt: Include task instructions, output schema, and a few examples.
- [ ] **(P10) Phase 2: Build the Prompt-Only Baseline** — Run baseline evals: Measure accuracy, quality score, schema validity, latency, and cost.
- [ ] **(P10) Phase 2: Build the Prompt-Only Baseline** — Store outputs: Keep raw outputs so you can compare where each approach succeeds or fails.
- [ ] **(P10) Phase 3: Build the RAG Variant** — Create a small knowledge base: Add policies, examples, guidelines, or domain references that can help the task.
- [ ] **(P10) Phase 3: Build the RAG Variant** — Retrieve context for each input: Use embeddings and metadata filters to find the most relevant reference examples.
- [ ] **(P10) Phase 3: Build the RAG Variant** — Evaluate the RAG version: Compare quality to the prompt-only baseline. Track retrieval failures separately from generation failures.
- [ ] **(P10) Phase 4: Build the LoRA Fine-Tuned Variant** — Prepare training data: Format data for instruction tuning. Split train/validation/test cleanly.
- [ ] **(P10) Phase 4: Build the LoRA Fine-Tuned Variant** — Fine-tune with LoRA: Start with modest settings: rank 8 or 16, low learning rate, early stopping, and validation tracking.
- [ ] **(P10) Phase 4: Build the LoRA Fine-Tuned Variant** — Track experiments: Log hyperparameters, training curves, validation metrics, GPU memory, and selected checkpoint.
- [ ] **(P10) Phase 5: Compare All Three Approaches** — Run the same benchmark: Evaluate prompt-only, RAG, and fine-tuned model on the same test set.
- [ ] **(P10) Phase 5: Compare All Three Approaches** — Compare beyond accuracy: Include latency, cost, setup complexity, update difficulty, failure modes, and operational risk.
- [ ] **(P10) Phase 5: Compare All Three Approaches** — Write a recommendation: For example: "RAG wins when knowledge changes often; LoRA wins when style and label consistency matter most."
- [ ] **(P10) Phase 6: Polish for Portfolio** — Build a comparison dashboard: Show side-by-side outputs and metrics for all three approaches.
- [ ] **(P10) Phase 6: Polish for Portfolio** — Write the decision memo: Make it read like an internal architecture decision record. Reviewers notice judgment, not only implementation.

## P11: AI Trace Explorer for LLM Workflows

*Topic: LLMOps, Observability, Tracing, Debugging, Evals*  
Folder: `11-ai-trace-explorer/`

- [ ] **(P11) Scaffold** — create `11-ai-trace-explorer/` app skeleton: FastAPI app entry, `requirements.txt`, `config.py`, `.env.example`, `README.md`, `tests/` dir, and a `Dockerfile`. Wire a `/health` endpoint and a smoke test.
- [ ] **(P11) Phase 1: Build a Multi-Step AI Workflow** — Choose a workflow: Example: intake a support ticket, classify it, retrieve relevant docs, draft a response, validate the response, and create an internal note.
- [ ] **(P11) Phase 1: Build a Multi-Step AI Workflow** — Make every step typed: Use Pydantic models for each step's input and output. Tracing is much easier when step boundaries are clean.
- [ ] **(P11) Phase 1: Build a Multi-Step AI Workflow** — Add controlled failure cases: Include bad retrieval, malformed JSON, low-confidence classification, and failed validation examples.
- [ ] **(P11) Phase 2: Instrument the Workflow** — Create a trace ID per run: Every workflow execution gets a unique trace ID and a list of spans.
- [ ] **(P11) Phase 2: Instrument the Workflow** — Wrap each step in a tracing decorator: Capture step name, input, output, prompt, model, token usage, latency, cost, status, and errors.
- [ ] **(P11) Phase 2: Instrument the Workflow** — Capture artifacts: Store retrieved chunks, tool arguments, validation failures, and retry attempts as structured artifacts.
- [ ] **(P11) Phase 3: Add Failure Classification** — Define failure categories: Retrieval miss, prompt failure, schema failure, tool error, hallucination, unsupported citation, timeout, and policy violation.
- [ ] **(P11) Phase 3: Add Failure Classification** — Classify failed runs: Use rules first, then an LLM judge for nuanced cases. Store both category and evidence.
- [ ] **(P11) Phase 3: Add Failure Classification** — Add root-cause hints: Suggest likely fixes: adjust chunking, add eval case, tighten schema, change prompt, or add retry.
- [ ] **(P11) Phase 4: Build the Trace Explorer UI** — Show a timeline: Display each step in order with status, latency, cost, and short summary.
- [ ] **(P11) Phase 4: Build the Trace Explorer UI** — Add expandable details: Clicking a step reveals input, output, prompt, raw response, and artifacts.
- [ ] **(P11) Phase 4: Build the Trace Explorer UI** — Add diff views: Compare successful and failed runs of the same workflow to spot where behavior diverged.
- [ ] **(P11) Phase 5: Build Metrics and Feedback Loop** — Aggregate reliability metrics: Track failure rate by step, average cost per workflow, P95 latency, retry rate, and most common failure category.
- [ ] **(P11) Phase 5: Build Metrics and Feedback Loop** — Turn failures into eval cases: Let a user mark a trace as a regression and export it into your eval dataset.
- [ ] **(P11) Phase 5: Build Metrics and Feedback Loop** — Add alerts: Trigger Slack alerts when a step's failure rate rises above threshold.
- [ ] **(P11) Phase 6: Polish for Portfolio** — Demo a failure diagnosis: Run a workflow that produces a bad answer, open the trace, identify the broken step, and export it to evals.
- [ ] **(P11) Phase 6: Polish for Portfolio** — Write the narrative: Frame it as "debugging infrastructure for AI workflows," which is much stronger than calling it a dashboard.

## P12: Semantic Cache Gateway for LLM APIs

*Topic: LLMOps, Cost Reduction, Latency Optimization, Embeddings*  
Folder: `12-semantic-cache-gateway/`

- [ ] **(P12) Scaffold** — create `12-semantic-cache-gateway/` app skeleton: FastAPI app entry, `requirements.txt`, `config.py`, `.env.example`, `README.md`, `tests/` dir, and a `Dockerfile`. Wire a `/health` endpoint and a smoke test.
- [ ] **(P12) Phase 1: Build the Proxy Contract** — Mirror a chat completion API: Accept model, messages, temperature, max tokens, and metadata. Return the provider-style response plus cache metadata.
- [ ] **(P12) Phase 1: Build the Proxy Contract** — Normalize requests: Hash system prompt, model, temperature, tool settings, and feature name. Two prompts are only cache-compatible if these settings match.
- [ ] **(P12) Phase 1: Build the Proxy Contract** — Forward cache misses: If no cache hit exists, call the provider, store the response, and return it.
- [ ] **(P12) Phase 2: Build Semantic Matching** — Embed user intent: Create embeddings for the user message or normalized prompt. Store embedding with response metadata.
- [ ] **(P12) Phase 2: Build Semantic Matching** — Query nearest neighbors: If similarity is above threshold, return cached response. Start conservative around 0.95.
- [ ] **(P12) Phase 2: Build Semantic Matching** — Store debug info: Save original prompt, matched prompt, similarity score, cache decision, and response ID.
- [ ] **(P12) Phase 3: Build Cache Policies** — Add TTLs by feature: Stable FAQs can have long TTLs. Time-sensitive or user-specific requests should have short TTLs or caching disabled.
- [ ] **(P12) Phase 3: Build Cache Policies** — Add policy tags: Support tags like user_specific, current_events, legal_sensitive, and creative. Use tags to change threshold and TTL.
- [ ] **(P12) Phase 3: Build Cache Policies** — Add invalidation endpoints: Invalidate by model, system prompt hash, feature, user, tag, or time range.
- [ ] **(P12) Phase 4: Add Safety Checks** — Prevent cross-user leakage: Never serve cached responses across users for personal or private contexts unless explicitly allowed.
- [ ] **(P12) Phase 4: Add Safety Checks** — Add semantic hit validation: For borderline matches, use a lightweight judge to confirm that the cached answer still fits the new prompt.
- [ ] **(P12) Phase 4: Add Safety Checks** — Track near misses: Log prompts just below threshold. These help tune cache policies.
- [ ] **(P12) Phase 5: Build Metrics and Load Test** — Export metrics: Track hit rate, semantic hit rate, exact hit rate, average latency saved, cost saved, and wrong-hit reports.
- [ ] **(P12) Phase 5: Build Metrics and Load Test** — Build a dashboard: Show real-time hit rate, latency comparison, cost savings, cache size, and threshold tradeoffs.
- [ ] **(P12) Phase 5: Build Metrics and Load Test** — Run a workload simulation: Send 2,000 requests with repeated and paraphrased questions. Measure savings and false-hit rate.
- [ ] **(P12) Phase 6: Polish for Portfolio** — Demo instant responses: Show a miss, an exact hit, a semantic hit, and an intentionally blocked unsafe cache hit.
- [ ] **(P12) Phase 6: Polish for Portfolio** — Use ROI: Example headline: "Reduced simulated LLM cost by 41% and P95 latency by 68% with conservative semantic caching."

## P13: AI Feature Rollout Monitor

*Topic: LLMOps, Feature Flags, Canary Rollouts, Quality Monitoring, Rollback*  
Folder: `13-feature-rollout-monitor/`

- [ ] **(P13) Scaffold** — create `13-feature-rollout-monitor/` app skeleton: FastAPI app entry, `requirements.txt`, `config.py`, `.env.example`, `README.md`, `tests/` dir, and a `Dockerfile`. Wire a `/health` endpoint and a smoke test.
- [ ] **(P13) Phase 1: Build the Flag Evaluation SDK** — Define AI flag schema: Include flag name, baseline config, candidate config, rollout percentage, quality threshold, owner, and rollback rule.
- [ ] **(P13) Phase 1: Build the Flag Evaluation SDK** — Build consistent assignment: Use hashing so the same user or session consistently gets the same variant during rollout.
- [ ] **(P13) Phase 1: Build the Flag Evaluation SDK** — Add safe defaults: If the flag service is down, the SDK returns the baseline config.
- [ ] **(P13) Phase 2: Build Quality Collection** — Log variant outputs: Store which variant served each request, the output, latency, cost, and any user feedback.
- [ ] **(P13) Phase 2: Build Quality Collection** — Score outputs asynchronously: Use an LLM judge or task-specific metric after the response is returned. Do not add latency to the user path.
- [ ] **(P13) Phase 2: Build Quality Collection** — Compare candidate to baseline: Track rolling averages, P10 quality, error rate, and latency for both variants.
- [ ] **(P13) Phase 3: Build Rollout Automation** — Define rollout stages: Example: 1%, 5%, 25%, 50%, 100%. Each stage has minimum sample size and quality requirements.
- [ ] **(P13) Phase 3: Build Rollout Automation** — Auto-advance safely: Move to the next stage only when metrics are healthy and enough samples have been collected.
- [ ] **(P13) Phase 3: Build Rollout Automation** — Pause or rollback automatically: If quality drops, latency spikes, or safety issues appear, pause rollout or set traffic back to 0%.
- [ ] **(P13) Phase 4: Build Dashboard and Controls** — Show active rollouts: Include current percentage, stage, health status, quality trend, and next checkpoint.
- [ ] **(P13) Phase 4: Build Dashboard and Controls** — Add manual controls: Pause, resume, rollback, and promote to 100%. Require a reason for every action.
- [ ] **(P13) Phase 4: Build Dashboard and Controls** — Show audit history: Track who changed rollout settings and why.
- [ ] **(P13) Phase 5: Test with a Demo AI Feature** — Build a small AI feature: Use subject line generation, support summary, or product description rewrite.
- [ ] **(P13) Phase 5: Test with a Demo AI Feature** — Create good and bad variants: The bad variant should fail quality checks clearly so rollback is easy to demo.
- [ ] **(P13) Phase 5: Test with a Demo AI Feature** — Run the rollout simulation: Show the system advancing a good variant and stopping a bad one.
- [ ] **(P13) Phase 6: Polish for Portfolio** — Record the rollout lifecycle: Show flag creation, staged rollout, quality monitoring, automatic pause, and rollback alert.
- [ ] **(P13) Phase 6: Polish for Portfolio** — Write the narrative: Use the phrase "quality-aware feature flags for AI systems." It communicates the project quickly.

## P14: Evaluation-as-a-Service Platform

*Topic: Evals, LLM-as-Judge, Quality Gates, Judge Calibration*  
Folder: `14-eval-as-a-service/`

- [ ] **(P14) Scaffold** — create `14-eval-as-a-service/` app skeleton: FastAPI app entry, `requirements.txt`, `config.py`, `.env.example`, `README.md`, `tests/` dir, and a `Dockerfile`. Wire a `/health` endpoint and a smoke test.
- [ ] **(P14) Phase 1: Design the Eval API** — Define evaluation requests: Input includes prompt, model output, optional reference answer, rubric, task type, and metadata.
- [ ] **(P14) Phase 1: Design the Eval API** — Define score output: Return overall score, dimension scores, pass/fail, explanation, evidence spans, judge confidence, and policy warnings.
- [ ] **(P14) Phase 1: Design the Eval API** — Support reusable rubrics: Store rubrics for summarization, classification, RAG faithfulness, tone, completeness, and safety.
- [ ] **(P14) Phase 2: Build Judge-Based Scoring** — Write dimension-specific judge prompts: Each rubric dimension should have clear scoring rules and examples.
- [ ] **(P14) Phase 2: Build Judge-Based Scoring** — Enforce structured results: Use Pydantic so every score has the same shape. Invalid judge output should retry or fail cleanly.
- [ ] **(P14) Phase 2: Build Judge-Based Scoring** — Add evidence requirements: The judge must explain what part of the output caused each score.
- [ ] **(P14) Phase 3: Calibrate the Judge** — Build a calibration set: Create 50 examples with human scores. Include excellent, mediocre, and bad outputs.
- [ ] **(P14) Phase 3: Calibrate the Judge** — Compare judge to human labels: Measure agreement, average score difference, and where the judge is too harsh or too generous.
- [ ] **(P14) Phase 3: Calibrate the Judge** — Tune prompts and thresholds: Adjust rubrics and pass/fail thresholds based on calibration results.
- [ ] **(P14) Phase 4: Build Batch Evals and Quality Gates** — Add batch endpoint: Accept a list of outputs and run evals asynchronously.
- [ ] **(P14) Phase 4: Build Batch Evals and Quality Gates** — Generate run reports: Show score distributions, failed cases, dimension-level weakness, and examples of judge reasoning.
- [ ] **(P14) Phase 4: Build Batch Evals and Quality Gates** — Add release gates: A CI job can call the eval service and fail if pass rate, safety score, or faithfulness score drops below threshold.
- [ ] **(P14) Phase 5: Build Dashboard and Analytics** — Create a run explorer: Compare eval runs over time and drill into failed examples.
- [ ] **(P14) Phase 5: Build Dashboard and Analytics** — Track judge drift: If judge model or rubric changes, rerun calibration examples and compare scores.
- [ ] **(P14) Phase 5: Build Dashboard and Analytics** — Add metric health: Show score variance, disagreement between judges, and human override rate.
- [ ] **(P14) Phase 6: Polish for Portfolio** — Demo it across two features: Score a RAG answer and a summarization output using different rubrics.
- [ ] **(P14) Phase 6: Polish for Portfolio** — Write the case study: Position it as "shared evaluation infrastructure for AI platform teams." Start with calibration results.

## P15: Local LLM Deployment Kit

*Topic: MLOps, Inference, Local Models, Quantization, Performance Testing*  
Folder: `15-local-llm-deploy-kit/`

- [ ] **(P15) Scaffold** — create `15-local-llm-deploy-kit/` app skeleton: FastAPI app entry, `requirements.txt`, `config.py`, `.env.example`, `README.md`, `tests/` dir, and a `Dockerfile`. Wire a `/health` endpoint and a smoke test.
- [ ] **(P15) Phase 1: Pick Models and Serving Path** — Choose a target task: Pick something measurable like summarization, classification, extraction, or support reply drafting.
- [ ] **(P15) Phase 1: Pick Models and Serving Path** — Select two or three model variants: Compare a small model, a medium model, and a quantized model. Document expected tradeoffs.
- [ ] **(P15) Phase 1: Pick Models and Serving Path** — Set up serving: Use Ollama for simplicity or vLLM for higher-throughput serving. Expose a chat completion endpoint.
- [ ] **(P15) Phase 2: Build the Benchmark Harness** — Create a request dataset: Use 100-200 prompts with realistic input lengths and expected output lengths.
- [ ] **(P15) Phase 2: Build the Benchmark Harness** — Measure performance: Track tokens per second, time to first token, P50/P95 latency, throughput, memory usage, and error rate.
- [ ] **(P15) Phase 2: Build the Benchmark Harness** — Test concurrency: Run benchmarks at 1, 5, 10, and 25 concurrent users.
- [ ] **(P15) Phase 3: Build Quality Evaluation** — Score outputs: Use task-specific metrics and LLM-as-judge against reference answers.
- [ ] **(P15) Phase 3: Build Quality Evaluation** — Compare against a cloud baseline: Run the same prompts against a hosted model and compare quality, cost estimate, and latency.
- [ ] **(P15) Phase 3: Build Quality Evaluation** — Identify acceptable use cases: Some tasks may work well locally; others may need stronger hosted models. Document this honestly.
- [ ] **(P15) Phase 4: Add Monitoring and Rollback** — Export metrics: Latency, throughput, token rate, GPU memory, queue depth, errors, and model version.
- [ ] **(P15) Phase 4: Add Monitoring and Rollback** — Build Grafana dashboards: Show live inference health and historical benchmark results.
- [ ] **(P15) Phase 4: Add Monitoring and Rollback** — Add model rollback: Support switching active model versions through config. Log every switch.
- [ ] **(P15) Phase 5: Package the Deployment Kit** — Write Docker Compose files: Include server, metrics, dashboard, and optional benchmark runner.
- [ ] **(P15) Phase 5: Package the Deployment Kit** — Add config files: Let users set model path, quantization, max context length, batching settings, and concurrency limits.
- [ ] **(P15) Phase 5: Package the Deployment Kit** — Create setup scripts: Make it easy to pull a model, start the server, run a benchmark, and generate a report.
- [ ] **(P15) Phase 6: Polish for Portfolio** — Publish benchmark results: Include a table comparing models by quality, latency, throughput, memory, and cost estimate.
- [ ] **(P15) Phase 6: Polish for Portfolio** — Write the deployment memo: Frame it as an internal recommendation: which model should be used for which workload, and why.
