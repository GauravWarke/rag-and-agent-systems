# P4: AI Output Policy Guardrail Service

**Topic:** Guardrails, Safety, Compliance, Structured Validation

## What you're building

A standalone guardrail service that reviews LLM outputs before users see them. It checks for policy violations, unsupported claims, PII leakage, unsafe instructions, schema errors, and brand-tone issues, then either approves, rewrites, blocks, or routes the output for review.

## Why this project lands interviews

> Teams need AI outputs they can defend. This build gives you a practical safety layer with policies, structured checks, review queues, and audit logs.

## Tech stack

| Component | Tool / Library |
|-----------|----------------|
| Language | Python 3.11+ |
| API | FastAPI |
| Rules Engine | Custom YAML policy rules |
| Validation | Pydantic + regex + classifiers |
| LLM Judge | GPT-4o-mini / Claude Haiku |
| PII Detection | Presidio or custom detectors |
| Storage | PostgreSQL |
| UI | Streamlit |
| Containerization | Docker |

## Build phases

### Phase 1: Define Policies and Decision Types (Day 1-2)

- Create policy categories: Start with PII leakage, unsupported factual claims, toxic language, unsafe instructions, medical/legal/financial overconfidence, schema mismatch, and brand voice violations.
- Define decision outcomes: The guardrail can approve, approve with warning, rewrite, block, or send to human review. Keep these outcomes simple and explainable.
- Build policy files: Store policies in YAML with rule name, severity, examples, detection strategy, and recommended action. This keeps the service auditable.

### Phase 2: Build Deterministic Validators (Day 2-5)

- Add schema validation: If an AI feature expects JSON, validate it before anything else. Bad format is the easiest failure to catch and the most common to ignore.
- Add PII detection: Detect emails, phone numbers, addresses, API keys, credit card-like strings, and named entities. Allow per-feature configuration because not all PII is always forbidden.
- Add forbidden content checks: Use regex and keyword rules for obvious policy violations. Deterministic checks should catch cheap, clear failures before using an LLM judge.

### Phase 3: Build LLM-Based Policy Review (Day 5-7)

- Create judge prompts per policy: The judge receives the original prompt, candidate output, policy text, and examples. It returns structured findings with severity and evidence.
- Require evidence for every finding: The judge should cite the exact output span that triggered the issue. This keeps the decision reviewable.
- Add confidence and disagreement: Run two judge passes for high-risk outputs. If judges disagree, route to human review instead of pretending certainty.

### Phase 4: Build Rewrite and Block Flows (Day 7-10)

- Implement safe rewrites: For fixable issues, rewrite only the problematic parts while preserving the useful answer. Examples: remove PII, soften overconfident claims, add uncertainty, or repair JSON.
- Block non-fixable outputs: For serious safety issues, return a structured block response with reason codes. Do not expose internal policy text unnecessarily.
- Log every decision: Store input hash, output hash, policy version, findings, action taken, latency, and final output. Auditability is the point.

### Phase 5: Build the Review Dashboard (Day 10-12)

- Create an audit queue: Human reviewers can inspect blocked or uncertain decisions, approve rewrites, override false positives, and leave notes.
- Track policy performance: Show block rate, rewrite rate, false-positive rate, average latency, and most common violation types.
- Add policy version comparison: When a policy changes, show how decisions would differ on historical examples. This prevents policy updates from causing chaos.

### Phase 6: Polish for Portfolio (Day 12-14)

- Demo multiple outcomes: Show an approved output, a rewritten output, a blocked output, and a human-review case.
- Write the narrative: Position it as "a policy enforcement layer for LLM outputs," not a moderation toy. Put audit logs and decision transparency near the top.

## Interview talking point

> Emphasize that not every guardrail should be an LLM call. Cheap deterministic checks reduce latency, cost, and false explanations.

## Status

Complete — all six phases implemented:

- **Phase 1 — Policies and Decision Types:** Policies are defined declaratively in
  `data/policies.yaml` (rule name, category, severity, examples, detection
  strategy, recommended action) covering PII leakage, unsupported factual
  claims, toxic language, unsafe instructions, medical/legal/financial
  overconfidence, schema mismatch, and brand voice. Decisions are one of
  `approve`, `approve_with_warning`, `rewrite`, `block`, or `human_review`
  (`app/core/models.py`).
- **Phase 2 — Deterministic Validators:** `app/validators/schema.py` checks
  candidate JSON output against an expected `{field: type}` shape.
  `app/validators/pii.py` detects emails, phone numbers, addresses, API
  keys, Luhn-validated credit-card numbers, and a naive name heuristic,
  with per-request `allowed_pii_types` overrides. `app/validators/forbidden.py`
  runs keyword/regex rules from `data/forbidden_terms.yaml`. These run
  first and can make the LLM judge unnecessary for a given category.
- **Phase 3 — LLM-Based Policy Review:** `app/judge/` builds one prompt per
  policy (`prompts.py`), requires every finding to cite an exact
  substring of the output as evidence (verified, not just trusted, for
  real LLM responses), and runs a second independent judge pass for
  high/critical-severity policies — a disagreement between passes routes
  the finding to `human_review` instead of a confident block. Defaults to
  a deterministic, keyless `StubJudgeClient`; set `OPENAI_API_KEY` to use
  a real judge model.
- **Phase 4 — Rewrite and Block Flows:** `app/rewrite/rewrite.py` turns a
  `rewrite` decision into a safe `final_output`: PII spans are redacted,
  malformed/incomplete JSON is repaired against `expected_schema` (missing
  or wrong-typed fields get a type-appropriate default), and overconfident
  phrasing is softened — anything outside those three fixable categories
  is left unresolved rather than guessed at. `app/rewrite/block.py` turns a
  `block` decision into a generic message plus stable policy-id reason
  codes, never the policy's internal description. `app/review/resolve.py`
  picks which of those applies per decision, and every decision — approve,
  rewrite, or block — is logged to `app/core/audit.py`'s in-memory
  `AuditLog` with hashed prompt/output, the policy set's content-derived
  `version`, findings, latency, and the final output actually shown.
- **Phase 5 — Review Dashboard:** `GET /v1/audit/queue` lists blocked
  or `human_review` decisions awaiting a human; `POST
  /v1/audit/{request_id}/review` records a reviewer's `approve` /
  `reject` / `approve_rewrite` decision plus an optional note and removes
  the entry from the queue. An `approve` action on a previously blocked
  or human-review entry means the guardrail flagged good output — a
  false positive. `GET /v1/audit/metrics` (`app/core/audit.py`)
  aggregates block/rewrite/approve/human-review rate, the false-positive
  rate among reviewed flagged entries, average latency, and the
  most-triggered policies across every logged decision. `POST
  /v1/policies/compare` (`app/policies/compare.py`) takes a candidate
  policy YAML plus a caller-supplied set of labeled prompt/output
  examples, replays each example through the live policy set and the
  candidate side by side (via a throwaway `ReviewEngine`/`AuditLog` pair
  so nothing touches the real audit trail), and reports which examples'
  decisions would change and which policy ids were added or removed from
  the findings. Examples are supplied by the caller rather than sourced
  from the audit log, since the log only stores prompt/output hashes.
- All of this is wired into `POST /v1/review`
  (`prompt`, `output`, `feature`, optional `expected_schema` /
  `allowed_pii_types`), which runs validators, then the judge for any
  policy category a validator didn't already resolve, and returns one
  aggregated `decision`, the `findings` that produced it, and a
  `final_output` safe to show the caller (or `None` for `block` /
  `human_review`).
- **Phase 6 — Polish for Portfolio:** [`docs/walkthrough.md`](docs/walkthrough.md)
  is a transcript walkthrough (real request/response pairs against the
  live app) covering an approved output, a rewritten output (PII
  redaction), a blocked output routed through the human-review queue,
  and a genuine judge-disagreement `human_review` case.
  [`docs/case_study.md`](docs/case_study.md) is the narrative writeup,
  headlined by a measurable result — deterministic validators skip 23.9%
  of LLM judge calls on a 20-request mixed batch — reproducible via
  `python docs/case_study_batch.py`.

Run tests: `pip install -r requirements-dev.txt && ruff check . && pytest -q`
