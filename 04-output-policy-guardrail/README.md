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

Planned. Scaffold pending — see root `ROADMAP.md`.
