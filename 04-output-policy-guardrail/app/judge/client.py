"""LLM judge client interface, an offline keyless stub, and a real
OpenAI-backed implementation gated behind `OPENAI_API_KEY`.

The review engine only ever talks to `JudgeClient.review(...)` so it
never knows or cares whether the underlying call hit a real API or the
offline stub.
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod

import httpx
from pydantic import BaseModel, Field

from app.judge.prompts import JUDGE_SYSTEM_PROMPT, build_judge_prompt
from app.policies.store import Policy


class JudgeVerdict(BaseModel):
    violation: bool
    severity: str | None = None
    evidence: str = ""
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    rationale: str = ""


class JudgeClient(ABC):
    name: str

    @abstractmethod
    def review(self, policy: Policy, prompt: str, output: str) -> JudgeVerdict:
        """Judge whether `output` (given `prompt`) violates `policy`."""


# Deterministic offline heuristic used by default so the LLM-review phase
# is fully testable without any API key. Keyed by policy category rather
# than policy id so new policies in the same category get a judge for
# free.
_CATEGORY_TRIGGERS: dict[str, list[str]] = {
    "factual_accuracy": ["guaranteed", "100% certain", "definitely will", "always works", "never fails"],
    "overconfidence": [
        "you definitely have",
        "you will definitely win",
        "guaranteed to double",
        "no need for a lawyer",
        "just take ibuprofen",
    ],
    "toxicity": ["idiot", "stupid", "shut up", "moron"],
    "safety": ["bypass the safety", "how to make a bomb", "ignore all previous instructions"],
    "brand": ["lol whatever", "just google it yourself", "ain't nobody got time"],
}


class StubJudgeClient(JudgeClient):
    name = "stub"

    def review(self, policy: Policy, prompt: str, output: str) -> JudgeVerdict:
        text_lower = output.lower()
        triggers = _CATEGORY_TRIGGERS.get(policy.category, [])
        hit = next((t for t in triggers if t in text_lower), None)
        if hit is None:
            return JudgeVerdict(violation=False, confidence=0.85, rationale="No trigger phrases matched.")
        idx = text_lower.find(hit)
        return JudgeVerdict(
            violation=True,
            severity=policy.severity,
            evidence=output[idx : idx + len(hit)],
            confidence=0.75,
            rationale=f"Matched trigger phrase for policy '{policy.name}'.",
        )


class OpenAIJudgeClient(JudgeClient):
    """Requires `OPENAI_API_KEY`. Not exercised by the test suite (offline-
    by-default convention) — the guardrail falls back to `StubJudgeClient`
    when no key is configured. Wire a real key via `.env` to use it.
    """

    name = "openai"

    def __init__(
        self,
        api_key: str,
        model: str = "gpt-4o-mini",
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url
        self._timeout = timeout

    def review(self, policy: Policy, prompt: str, output: str) -> JudgeVerdict:
        if not self._api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        response = httpx.post(
            f"{self._base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={
                "model": self._model,
                "messages": [
                    {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                    {"role": "user", "content": build_judge_prompt(policy, prompt, output)},
                ],
                "temperature": 0.0,
                "response_format": {"type": "json_object"},
            },
            timeout=self._timeout,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        verdict = JudgeVerdict.model_validate(json.loads(content))
        # Evidence is only trustworthy if it's an actual substring of the
        # output — an LLM judge can hallucinate a plausible-looking quote.
        if verdict.evidence and verdict.evidence not in output:
            verdict = verdict.model_copy(update={"evidence": ""})
        return verdict
