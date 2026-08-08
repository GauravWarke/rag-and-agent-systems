# Case Study — AI Output Policy Guardrail Service

## Headline result

On a 20-request mixed batch (clean answers, PII leaks, toxic language, unsafe
instructions, overconfident medical/legal/financial claims, brand-voice
violations, and malformed JSON — see `docs/case_study_batch.py`), running
through the real `ReviewEngine` pipeline with the offline `StubJudgeClient`,
**deterministic validators resolved enough policy categories upfront to skip
23.9% of the LLM judge calls (43 of a possible 180)** that a judge-only
guardrail would have made, while still producing the same final decisions:
4 rewrites, 3 blocks, 2 warnings, and 11 clean approvals.

| Metric (20 requests) | Value |
|---|---|
| Policies eligible for LLM judge review | 7 (`unsupported_factual_claims`, `toxic_language`, `unsafe_instructions`, `medical_overconfidence`, `legal_overconfidence`, `financial_overconfidence`, `brand_voice_violation`) |
| Worst-case judge calls (no deterministic pre-filter, incl. dual-pass for high/critical severity) | 180 |
| Actual judge calls made | 137 |
| Judge calls saved | 43 (23.9%) |
| Decisions | 11 approve · 2 approve_with_warning · 4 rewrite · 3 block |

Regenerate this with `python docs/case_study_batch.py` from inside
`04-output-policy-guardrail/`.

## Reading the result honestly

The saving comes entirely from two `detection_strategy: both` policies —
`toxic_language` and `unsafe_instructions` — whose deterministic checks
(`app/validators/forbidden.py`) run first and, on a hit, add that policy's
`category` to `skip_categories` so `PolicyJudge.review()` never calls the
judge for it (`app/review/engine.py`, `app/judge/review.py`). Both are
high/critical severity, so every skipped category saves a *dual-pass* judge
call (2 calls, not 1) — the batch above has 4 requests where forbidden-term
matching alone caught toxic or unsafe output, worth 4 × up to 4 skipped
calls. The other 5 llm-judge-only policies (factual accuracy, three flavors
of overconfidence, brand voice) have no deterministic pre-filter at all in
this V1, so they're judged on every request regardless of outcome — that's
the ceiling on how much more this specific design could save without adding
new deterministic rules for those categories.

## Architecture

```
client → POST /v1/review
            │
            ▼
   schema validator ──┐
   PII validator ──────┤  (deterministic, cheap, run first)
   forbidden-term check┘
            │  resolved_categories
            ▼
   PolicyJudge (skips resolved_categories; dual-pass for high/critical severity;
                disagreement between passes -> human_review, not a guess)
            │
            ▼
   aggregate → resolve_output (redact / repair / withhold) → AuditLog
            │
            ▼
   ReviewResponse (decision + findings + final_output + reason_codes)
```

`GET /v1/audit/queue` and `POST /v1/audit/{id}/review` let a human clear
blocked/human-review entries; `GET /v1/audit/metrics` tracks block/rewrite/
approve/human-review rate and false-positive rate (an `approve` review
action on a flagged entry); `POST /v1/policies/compare` replays labeled
examples against a candidate policy YAML to preview how an edit would
change historical decisions before it ships.

## Tradeoffs and decisions

- **Deterministic-first, judge-only-when-needed.** The core design bet:
  cheap regex/rule checks catch the clear, high-confidence violations
  (an email address, a forbidden phrase) so the slower, costlier, and
  less-explainable LLM judge only runs where judgment is actually required
  (is this claim unsupported? is this tone off-brand?). The 23.9% figure
  above is the direct, measurable payoff of that split.
- **Dual-pass judging with disagreement routed to `human_review`, not a
  coin flip.** High/critical-severity findings are too consequential to
  trust a single LLM call. Two independent passes that disagree return
  `human_review` instead of the guardrail pretending to be certain
  (`app/judge/review.py::_disagreement_finding`).
- **Rewrite preserves the useful answer; block never leaks the policy
  text.** A fixable issue (PII, malformed JSON, an overconfident phrase)
  is repaired in place rather than discarded; a genuinely unsafe output
  is replaced with a generic message plus stable `reason_codes`
  (`app/rewrite/block.py`), so internal policy descriptions never reach
  the end user.
- **Everything is logged, and policy changes are replayable before they
  ship.** Every decision — approve, rewrite, block — is written to the
  audit log with hashed input/output and the policy set's content-derived
  version, and `POST /v1/policies/compare` lets a policy author see which
  historical examples would flip decisions under a candidate policy edit,
  against a throwaway engine/log pair that never touches the real trail.

## What would change at production scale

The 23.9% judge-call saving would likely grow with more deterministic
coverage — e.g. a lightweight classifier or expanded term list for
overconfidence and brand-voice categories, which currently have no
pre-filter at all. The other clear next investment is swapping
`StubJudgeClient` for a real model (`OpenAIJudgeClient` is already wired
behind `OPENAI_API_KEY`) and re-running calibration against hand-labeled
examples, since the stub's keyword-trigger heuristic is a reasonable
offline V1 but won't catch violations that don't happen to contain one of
its trigger phrases.
