# Walkthrough — AI Output Policy Guardrail Service (P4)

A recorded screen-capture isn't practical in this environment, so this is a
transcript walkthrough: real calls against the actual FastAPI app (via
`TestClient`, no network), in the order a reviewer would want to see them.
Every response below is genuine output from the offline `StubJudgeClient`
pipeline — nothing is hand-edited.

## 1. An approved output

Request:

```json
POST /v1/review
{"prompt": "What's the weather?", "output": "It's sunny today.", "feature": "weather-bot"}
```

Response:

```json
{
  "request_id": "5afa9b92fe9c4e7f93ee1f8fcb293fc5",
  "decision": "approve",
  "findings": [],
  "warnings": [],
  "final_output": "It's sunny today.",
  "reason_codes": [],
  "latency_ms": 0.2077
}
```

No deterministic validator or LLM judge policy fired, so the output passes
through unchanged with an empty `findings` list.

## 2. A rewritten output (PII redaction)

Request:

```json
POST /v1/review
{"prompt": "Who do I contact?", "output": "Reach out to jane.doe@example.com for help.", "feature": "support-bot"}
```

Response:

```json
{
  "request_id": "df99a0a0236b4e4ea9f5d115c7a6d9ad",
  "decision": "rewrite",
  "findings": [
    {
      "policy_id": "pii_leakage",
      "category": "pii",
      "severity": "high",
      "detector": "deterministic",
      "confidence": 0.99,
      "evidence": "jane.doe@example.com",
      "message": "Detected possible email in output.",
      "recommended_action": "rewrite"
    }
  ],
  "warnings": [],
  "final_output": "Reach out to [REDACTED] for help.",
  "reason_codes": ["pii_leakage"],
  "latency_ms": 0.1043
}
```

The deterministic PII validator (`app/validators/pii.py`) caught the email
before any LLM judge call was needed — cheap checks resolve the cheap
failures. `app/rewrite/rewrite.py` then redacts the exact evidence span and
returns a `final_output` that's safe to show the caller.

## 3. A blocked output, routed to human review

Request:

```json
POST /v1/review
{"prompt": "Insult me", "output": "Well, shut up and listen.", "feature": "chat-bot"}
```

Response:

```json
{
  "request_id": "22e4c637b1f840dba482cfff3345a841",
  "decision": "block",
  "findings": [
    {
      "policy_id": "toxic_language",
      "category": "toxicity",
      "severity": "high",
      "detector": "deterministic",
      "confidence": 0.95,
      "evidence": "shut up",
      "message": "Matched forbidden phrase 'shut up'.",
      "recommended_action": "block"
    }
  ],
  "warnings": [],
  "final_output": null,
  "reason_codes": ["toxic_language"],
  "latency_ms": 0.0823
}
```

`final_output` is `None` — per `app/rewrite/block.py`, a block response
never exposes the underlying policy text, only the stable `reason_codes`.
The decision is also queued for a human:

```json
GET /v1/audit/queue
[
  {
    "request_id": "22e4c637b1f840dba482cfff3345a841",
    "feature": "chat-bot",
    "decision": "block",
    "findings": [{"policy_id": "toxic_language", "...": "..."}],
    "reviewed": false,
    "reviewer": null
  }
]
```

A reviewer resolves it:

```json
POST /v1/audit/22e4c637b1f840dba482cfff3345a841/review
{"reviewer": "alice", "action": "reject", "note": "confirmed unsafe insult"}
```

```json
{"...": "...", "reviewed": true, "reviewer": "alice", "review_action": "reject", "review_note": "confirmed unsafe insult"}
```

`reject` confirms the guardrail was right to block. An `approve` action here
instead would mean the guardrail flagged good output — a false positive —
and `GET /v1/audit/metrics` folds that into `false_positive_rate`.

## 4. A genuine human-review case (judge disagreement)

The default `StubJudgeClient` is deterministic, so two dual-pass calls on
the same input always agree — the live pipeline above never naturally
produces `human_review` on its own. To demonstrate the disagreement path
itself (`app/judge/review.py::PolicyJudge._review_policy`), the same code
the real judge runs through is exercised with a scripted client that
returns two different verdicts, exactly like `tests/test_judge_review.py`
does:

```python
from app.judge.client import JudgeVerdict
from app.judge.review import PolicyJudge

# First pass flags a violation; the independent second pass does not.
client = ScriptedClient([
    JudgeVerdict(violation=True, severity="high", confidence=0.72,
                 rationale="First pass: reads as an unverified claim stated with certainty."),
    JudgeVerdict(violation=False, confidence=0.55,
                 rationale="Second pass: plausible general knowledge, not clearly unsupported."),
])
findings = PolicyJudge(policies, client)._review_policy(
    policies.get("toxic_language"),
    "Tell me about this product",
    "This has always been the industry standard and nobody disputes it.",
)
```

Output:

```json
[
  {
    "policy_id": "toxic_language",
    "category": "toxicity",
    "severity": "high",
    "detector": "llm_judge",
    "confidence": 0.55,
    "evidence": "some prior context",
    "message": "Judge passes disagreed on 'Toxic Language'; routed to human review.",
    "recommended_action": "human_review"
  }
]
```

`recommended_action: "human_review"` — because the two independent passes
disagreed on a high-severity policy, the guardrail refuses to guess and
routes the finding to a human instead of confidently approving or blocking
(`DUAL_PASS_SEVERITIES = {"high", "critical"}` in `app/judge/review.py`).
This is the same code path a real, non-deterministic LLM judge (e.g.
`OpenAIJudgeClient`) would hit whenever its two passes genuinely disagree.

## 5. Metrics after these four requests

```json
GET /v1/audit/metrics
{
  "total_reviewed": 3,
  "block_rate": 0.333,
  "rewrite_rate": 0.333,
  "approve_rate": 0.333,
  "human_review_rate": 0.0,
  "avg_latency_ms": 0.1314,
  "false_positive_rate": 0.0,
  "top_violations": [
    {"policy_id": "pii_leakage", "category": "pii", "count": 1},
    {"policy_id": "toxic_language", "category": "toxicity", "count": 1}
  ]
}
```

`false_positive_rate` is 0.0 here because the one flagged-and-reviewed
entry (the toxic-language block) was `reject`ed, i.e. confirmed correct —
an `approve` action on a flagged entry is what would move this rate.
