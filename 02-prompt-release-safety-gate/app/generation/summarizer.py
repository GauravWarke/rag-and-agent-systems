"""Offline, keyless generation for the CRM summary feature (Phase 1).

`run_prompt` returns the model's *raw* output dict plus generation
metadata — mirroring how a real provider call would return unvalidated
JSON text. Callers validate the raw dict against `NoteSummary` themselves
(catching `pydantic.ValidationError`), which is what lets "the prompt
returned fluent prose that breaks the schema" be a real, testable failure
mode for the regression runner rather than something the stub can't ever
produce.

The default `stub` generator is rule-based and deterministic so the whole
pipeline — prompt loading, generation, scoring, gating — is testable
without any LLM provider key. Swap `model_settings.model` to a real
provider and implement `_generate_llm` when a provider key is configured.
"""
from __future__ import annotations

import re
import time

from app.prompts.spec import PromptSpec

# Nominal USD price per 1M tokens (input, output), keyed by model name.
# Used only to produce a realistic, comparable cost estimate for the
# regression runner — not a live pricing source.
_PRICE_PER_MILLION = {
    "stub": (0.15, 0.60),
    "gpt-4o-mini": (0.15, 0.60),
    "claude-haiku": (0.25, 1.25),
}

_FRUSTRATED_MARKERS = (
    "again", "still", "unacceptable", "ridiculous", "worst", "furious", "so mad",
    "scream", "verge of canceling", "over and over",
)
_NEGATIVE_WORDS = (
    "broken", "error", "issue", "problem", "fail", "not working", "cancel",
    "refund", "complain", "wrong", "double charged", "double-charged",
    "rude", "scared", "threatening", "terrifying", "unauthorized", "disappointed",
    "declined", "overwhelmed",
)
_POSITIVE_WORDS = ("thanks", "thank you", "great", "awesome", "love", "appreciate", "happy", "perfect", "fantastic", "well done")

_CRITICAL_WORDS = (
    "down", "outage", "urgent", "asap", "immediately", "critical", "emergency",
    "can't log in", "cannot access", "cant log in", "lawyer", "legal", "unauthorized",
    "threatening", "crashes immediately", "ssn", "social security",
)
_HIGH_WORDS = (
    "broken", "not working", "twice", "escalate", "still not", "again", "rude",
    "scared", "cancel", "three times", "500 error",
)
_MEDIUM_WORDS = ("soon", "when possible", "issue", "problem", "wrong")


def _detect_sentiment(note_lower: str) -> str:
    if note_lower.count("!") >= 2 or any(w in note_lower for w in _FRUSTRATED_MARKERS):
        return "frustrated"
    if any(w in note_lower for w in _NEGATIVE_WORDS):
        return "negative"
    if any(w in note_lower for w in _POSITIVE_WORDS):
        return "positive"
    return "neutral"


def _detect_urgency(note_lower: str) -> str:
    if any(w in note_lower for w in _CRITICAL_WORDS):
        return "critical"
    if any(w in note_lower for w in _HIGH_WORDS):
        return "high"
    if any(w in note_lower for w in _MEDIUM_WORDS):
        return "medium"
    return "low"


def _next_action(note_lower: str) -> str:
    if any(w in note_lower for w in ("lawyer", "legal action", "sue ")):
        return "Escalate to a manager and loop in legal/compliance."
    if any(w in note_lower for w in ("hacked", "without my permission", "threatening", "unauthorized", "compromised", "scared")):
        return "Escalate to the security team and help the customer secure the account."
    if any(w in note_lower for w in ("social security", "ssn", "remove it from my account", "remove my data")):
        return "Escalate to the privacy/security team to review and remove sensitive data."
    if any(w in note_lower for w in ("rude", "accent", "discriminat")):
        return "Escalate to a manager to review the support interaction."
    if any(w in note_lower for w in ("refund", "charge", "billing", "invoice", "discount", "price")):
        return "Verify the billing charge and process a refund if appropriate."
    if any(w in note_lower for w in ("bug", "error", "crash", "broken", "not working", "500")):
        return "Escalate to engineering with reproduction details."
    if "pause" in note_lower and "membership" in note_lower:
        return "Explain the pause option and confirm which the customer prefers."
    if "cancel" in note_lower:
        return "Process the cancellation request and confirm with the customer."
    if any(w in note_lower for w in ("login", "log in", "password", "sign in", "access my account")):
        return "Help the customer reset their password and regain account access."
    if any(w in note_lower for w in _POSITIVE_WORDS):
        return "Thank the customer and share the feedback with the product team."
    if "?" in note_lower or note_lower.strip().startswith(
        ("is ", "does ", "can ", "how ", "what ", "when ", "where ", "why ")
    ):
        return "Send the customer documentation answering their question."
    return "Follow up with the customer to clarify the issue before taking action."


def _confidence(note: str, note_lower: str) -> float:
    score = 0.6
    if len(note) >= 40:
        score += 0.2
    if len(note) < 15:
        score -= 0.25
    if any(w in note_lower for w in _NEGATIVE_WORDS + _POSITIVE_WORDS + _CRITICAL_WORDS):
        score += 0.1
    return max(0.0, min(1.0, round(score, 2)))


def _clean(note: str) -> str:
    text = re.sub(r"\s+", " ", note).strip()
    text = re.sub(r"!{2,}", "!", text)
    if text and text[0].islower():
        text = text[0].upper() + text[1:]
    return text


def _summarize_text(note: str, sentiment: str, urgency: str, style: str) -> str:
    cleaned = _clean(note)
    if style == "verbose":
        body = cleaned if len(cleaned) <= 400 else cleaned[:397] + "..."
        return f"{body} The customer's tone reads as {sentiment} with {urgency} urgency."
    if len(cleaned) <= 140:
        return cleaned
    truncated = cleaned[:140].rsplit(" ", 1)[0]
    return f"{truncated}..."


def _estimate_tokens(text: str) -> int:
    return max(1, len(text) // 4)


def _estimate_cost(model: str, input_tokens: int, output_tokens: int) -> float:
    input_price, output_price = _PRICE_PER_MILLION.get(model, _PRICE_PER_MILLION["stub"])
    return round((input_tokens * input_price + output_tokens * output_price) / 1_000_000, 8)


def _generate_llm(note: str, prompt: PromptSpec) -> dict:
    raise NotImplementedError(
        f"Generation model '{prompt.model_settings.model}' not wired yet; "
        "use model_settings.model: stub or implement the provider adapter "
        "using prompt.system_prompt / prompt.few_shot_examples."
    )


def _generate_stub(note: str, prompt: PromptSpec) -> dict:
    note_lower = note.lower()
    sentiment = _detect_sentiment(note_lower)
    urgency = _detect_urgency(note_lower)
    return {
        "summary": _summarize_text(note, sentiment, urgency, prompt.model_settings.style),
        "sentiment": sentiment,
        "next_action": _next_action(note_lower),
        "urgency": urgency,
        "confidence": _confidence(note, note_lower),
    }


def run_prompt(note: str, prompt: PromptSpec) -> tuple[dict, dict]:
    """Run `prompt` against `note` and return (raw_output, generation_meta).

    `raw_output` is unvalidated — callers should parse it with
    `NoteSummary.model_validate(raw_output)` and treat a `ValidationError`
    as a schema-validity failure.
    """
    start = time.perf_counter()
    error: str | None = None
    try:
        if prompt.model_settings.model != "stub":
            raw = _generate_llm(note, prompt)
        else:
            raw = _generate_stub(note, prompt)
    except NotImplementedError as exc:
        raw = {}
        error = str(exc)
    latency_ms = round((time.perf_counter() - start) * 1000, 4)

    prompt_text = prompt.system_prompt + "".join(
        ex.input + str(ex.output) for ex in prompt.few_shot_examples
    )
    input_tokens = _estimate_tokens(prompt_text + note)
    output_tokens = _estimate_tokens(str(raw))

    meta = {
        "prompt_name": prompt.name,
        "prompt_version": prompt.version,
        "model": prompt.model_settings.model,
        "latency_ms": latency_ms,
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "cost_usd": _estimate_cost(prompt.model_settings.model, input_tokens, output_tokens),
        "error": error,
    }
    return raw, meta
