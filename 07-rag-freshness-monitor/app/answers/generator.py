"""Generate answers for probe questions by retrieving the top matching
chunk and producing a grounded, citation-tagged answer.

The default `StubAnswerGenerator` is a deterministic offline extractive
generator (no API key needed): the answer is the first sentence of the
retrieved chunk plus a `[source: <chunk_id>]` citation tag, so answer
drift can be run and tested without any provider. Swap in
`OpenAIAnswerGenerator` behind `OPENAI_API_KEY` for a real model.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime

import httpx

from app.core.models import AnswerRecord, AnswerRunSummary, ChunkRecord, ProbeQuestion
from app.drift.retriever import top_match


class AnswerGenerator(ABC):
    name: str

    @abstractmethod
    def generate(self, question: str, chunk: ChunkRecord | None) -> str:
        """Return a grounded answer for `question`, given the retrieved
        `chunk` (or `None` if nothing matched)."""


class StubAnswerGenerator(AnswerGenerator):
    name = "stub"

    def generate(self, question: str, chunk: ChunkRecord | None) -> str:
        if chunk is None:
            return "I could not find this in the docs."
        sentence = chunk.text.strip().split(". ")[0].strip()
        if sentence and not sentence.endswith("."):
            sentence += "."
        return f"{sentence} [source: {chunk.chunk_id}]"


class OpenAIAnswerGenerator(AnswerGenerator):
    """Requires `OPENAI_API_KEY`. Not exercised by the test suite (offline-
    by-default convention) — falls back to `StubAnswerGenerator` when no
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

    def generate(self, question: str, chunk: ChunkRecord | None) -> str:
        if not self._api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        if chunk is None:
            return "I could not find this in the docs."
        response = httpx.post(
            f"{self._base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={
                "model": self._model,
                "messages": [
                    {
                        "role": "system",
                        "content": (
                            "Answer only from the provided context. Cite the "
                            "chunk id in the form [source: <chunk_id>]. If the "
                            "context does not answer the question, say so."
                        ),
                    },
                    {
                        "role": "user",
                        "content": f"Context (chunk_id={chunk.chunk_id}):\n{chunk.text}\n\nQuestion: {question}",
                    },
                ],
                "temperature": 0.0,
            },
            timeout=self._timeout,
        )
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]


def generate_answers(
    probes: list[ProbeQuestion],
    chunks: list[ChunkRecord],
    generator: AnswerGenerator | None = None,
) -> AnswerRunSummary:
    generator = generator or StubAnswerGenerator()
    chunks_by_id = {c.chunk_id: c for c in chunks}
    answers: list[AnswerRecord] = []
    for probe in probes:
        chunk_id, _ = top_match(probe.question, chunks)
        chunk = chunks_by_id.get(chunk_id) if chunk_id else None
        answers.append(
            AnswerRecord(
                probe_id=probe.probe_id,
                question=probe.question,
                chunk_id=chunk_id,
                answer_text=generator.generate(probe.question, chunk),
            )
        )
    return AnswerRunSummary(run_at=datetime.now(UTC).isoformat(), answers=answers)
