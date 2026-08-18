"""LLM-as-judge for answer drift: decide whether two answers to the same
probe question mean the same thing, and whether the current answer's
citation still supports its claim.

The default `StubAnswerJudgeClient` is a deterministic offline heuristic
(cosine similarity over the stub embedder) so answer drift can be tested
without any API key. Swap in `OpenAIAnswerJudgeClient` behind
`OPENAI_API_KEY` for a real judge.
"""
from __future__ import annotations

import json
from abc import ABC, abstractmethod

import httpx
from pydantic import BaseModel, Field

from app.core.models import ChunkRecord
from app.indexing.embeddings import cosine, embed

# Below this cosine similarity between two answers, the judge treats the
# meaning as changed rather than just reworded.
_MEANING_CHANGE_THRESHOLD = 0.9

JUDGE_SYSTEM_PROMPT = (
    "You are a strict RAG answer-drift judge. Compare a previous answer to "
    "a current answer for the same question and respond only with the "
    "requested JSON."
)


class AnswerJudgeVerdict(BaseModel):
    meaning_changed: bool
    citation_supports_answer: bool
    confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    rationale: str = ""


class AnswerJudgeClient(ABC):
    name: str

    @abstractmethod
    def compare(
        self,
        question: str,
        previous_answer: str,
        current_answer: str,
        current_chunk: ChunkRecord | None,
    ) -> AnswerJudgeVerdict:
        """Judge whether `current_answer` changed in meaning from
        `previous_answer`, and whether `current_chunk` still supports it."""


class StubAnswerJudgeClient(AnswerJudgeClient):
    name = "stub"

    def compare(
        self,
        question: str,
        previous_answer: str,
        current_answer: str,
        current_chunk: ChunkRecord | None,
    ) -> AnswerJudgeVerdict:
        if previous_answer.strip() == current_answer.strip():
            similarity = 1.0
        else:
            similarity = cosine(embed(previous_answer), embed(current_answer))
        meaning_changed = similarity < _MEANING_CHANGE_THRESHOLD
        citation_supports = current_chunk is not None and current_chunk.chunk_id in current_answer
        rationale = (
            f"Similarity {similarity:.3f} "
            f"{'below' if meaning_changed else 'at/above'} threshold {_MEANING_CHANGE_THRESHOLD}."
        )
        return AnswerJudgeVerdict(
            meaning_changed=meaning_changed,
            citation_supports_answer=citation_supports,
            confidence=0.7,
            rationale=rationale,
        )


class OpenAIAnswerJudgeClient(AnswerJudgeClient):
    """Requires `OPENAI_API_KEY`. Not exercised by the test suite (offline-
    by-default convention) — falls back to `StubAnswerJudgeClient` when no
    key is configured. Wire a real key via `.env` to use it.
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

    def compare(
        self,
        question: str,
        previous_answer: str,
        current_answer: str,
        current_chunk: ChunkRecord | None,
    ) -> AnswerJudgeVerdict:
        if not self._api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        context = current_chunk.text if current_chunk is not None else "(no chunk retrieved)"
        prompt = f"""Question: {question}

Previous answer:
\"\"\"{previous_answer}\"\"\"

Current answer:
\"\"\"{current_answer}\"\"\"

Current supporting context (chunk_id={current_chunk.chunk_id if current_chunk else None}):
\"\"\"{context}\"\"\"

Respond with strict JSON only, no other text, in this exact shape:
{{"meaning_changed": true or false, "citation_supports_answer": true or false, \
"confidence": <0.0-1.0>, "rationale": "<one sentence>"}}"""
        response = httpx.post(
            f"{self._base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={
                "model": self._model,
                "messages": [
                    {"role": "system", "content": JUDGE_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                "temperature": 0.0,
                "response_format": {"type": "json_object"},
            },
            timeout=self._timeout,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return AnswerJudgeVerdict.model_validate(json.loads(content))
