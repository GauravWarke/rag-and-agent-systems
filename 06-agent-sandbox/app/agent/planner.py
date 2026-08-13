"""Planner: turns a natural-language request into a proposed tool call.

`StubPlanner` is a deterministic keyword/regex planner so the whole agent
is testable offline with no API key. `OpenAIPlanner` is a real LLM-backed
implementation gated behind `OPENAI_API_KEY`, matching this repo's
offline-by-default convention.
"""
from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Any

import httpx
from pydantic import BaseModel, Field

_EXPRESSION_CHARS = re.compile(r"[0-9+\-*/(). ]+")
_WHERE_CLAUSE = re.compile(r"where\s+(\w+)\s+is\s+([\w.\-]+)", re.IGNORECASE)


class ToolPlan(BaseModel):
    tool_name: str | None
    arguments: dict[str, Any] = Field(default_factory=dict)
    reasoning: str
    confidence: float = Field(ge=0.0, le=1.0)


class Planner(ABC):
    name: str

    @abstractmethod
    def plan(self, request: str) -> ToolPlan:
        """Propose a tool + arguments for a natural-language request."""


class StubPlanner(Planner):
    """Offline heuristic planner: keyword/regex routing to the tool
    registry. Deterministic on purpose so agent-workflow tests never need
    network access or an API key.
    """

    name = "stub"

    def plan(self, request: str) -> ToolPlan:
        text = request.lower()

        if "ticket" in text:
            return ToolPlan(
                tool_name="ticket_create",
                arguments={"title": request[:80], "description": request},
                reasoning="Request asks to create a support ticket.",
                confidence=0.75,
            )

        where_match = _WHERE_CLAUSE.search(text)
        if where_match and ("customer" in text or "account" in text or "csv" in text):
            column, value = where_match.group(1), where_match.group(2)
            return ToolPlan(
                tool_name="csv_query",
                arguments={"column": column, "value": value},
                reasoning=f"Request looks like a customer-data lookup filtered by {column}.",
                confidence=0.7,
            )

        if "read" in text and "file" in text:
            tokens = request.split()
            path = tokens[-1] if tokens else ""
            return ToolPlan(
                tool_name="file_reader",
                arguments={"path": path},
                reasoning="Request asks to read a file from the sandbox.",
                confidence=0.65,
            )

        if "search" in text or "look up" in text or "find docs" in text:
            return ToolPlan(
                tool_name="web_search",
                arguments={"query": request},
                reasoning="Request looks like an information lookup.",
                confidence=0.6,
            )

        expression = next(
            (
                candidate.strip()
                for candidate in _EXPRESSION_CHARS.findall(request)
                if any(ch.isdigit() for ch in candidate) and any(op in candidate for op in "+-*/")
            ),
            None,
        )
        if expression:
            return ToolPlan(
                tool_name="calculator",
                arguments={"expression": expression},
                reasoning="Request contains an arithmetic expression.",
                confidence=0.8,
            )

        return ToolPlan(
            tool_name=None,
            arguments={},
            reasoning="No registered tool matches this request.",
            confidence=0.0,
        )


class OpenAIPlanner(Planner):
    """Requires `OPENAI_API_KEY`. Not exercised by the test suite (offline-
    by-default convention) — callers fall back to `StubPlanner` when no key
    is configured.
    """

    name = "openai"

    def __init__(
        self,
        api_key: str,
        tool_names: list[str],
        model: str = "gpt-4o-mini",
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key
        self._tool_names = tool_names
        self._model = model
        self._base_url = base_url
        self._timeout = timeout

    def plan(self, request: str) -> ToolPlan:
        if not self._api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        system_prompt = (
            "You select at most one tool for a workspace assistant. Available tools: "
            f"{', '.join(self._tool_names)}, or null if none apply. Return a JSON object "
            "matching: tool_name (string or null), arguments (object), reasoning (string), "
            "confidence (0-1)."
        )
        response = httpx.post(
            f"{self._base_url}/chat/completions",
            headers={"Authorization": f"Bearer {self._api_key}"},
            json={
                "model": self._model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": request},
                ],
                "temperature": 0.0,
                "response_format": {"type": "json_object"},
            },
            timeout=self._timeout,
        )
        response.raise_for_status()
        content = response.json()["choices"][0]["message"]["content"]
        return ToolPlan.model_validate(json.loads(content))
