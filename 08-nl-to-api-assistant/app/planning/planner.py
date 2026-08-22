"""Planner: turns a natural-language request plus a shortlist of candidate
endpoints (from the selector) into a structured `CallPlan`.

`StubPlanner` is deterministic regex/keyword routing so the whole
assistant is testable offline with no API key. `OpenAIPlanner` is a real
LLM-backed implementation gated behind `OPENAI_API_KEY`, matching this
repo's offline-by-default convention.
"""
from __future__ import annotations

import json
import re
from abc import ABC, abstractmethod
from typing import Any

import httpx

from app.planning.models import CallPlan, EndpointSpec

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_CUSTOMER_ID = re.compile(r"\bcust_\d+\b")
_SUBSCRIPTION_ID = re.compile(r"\bsub_\d+\b")
_INVOICE_ID = re.compile(r"\binv_\d+\b")
_AMOUNT = re.compile(r"\$\s?(\d+(?:\.\d{1,2})?)")
_PLAN_NAMES = ("basic", "pro", "enterprise")


def _extract_entities(text: str) -> dict[str, Any]:
    entities: dict[str, Any] = {}
    if match := _EMAIL.search(text):
        entities["email"] = match.group(0)
    if match := _CUSTOMER_ID.search(text):
        entities["customer_id"] = match.group(0)
    if match := _SUBSCRIPTION_ID.search(text):
        entities["subscription_id"] = match.group(0)
    if match := _INVOICE_ID.search(text):
        entities["invoice_id"] = match.group(0)
    if match := _AMOUNT.search(text):
        entities["amount_cents"] = round(float(match.group(1)) * 100)
    lowered = text.lower()
    for plan_name in _PLAN_NAMES:
        if plan_name in lowered:
            entities["plan"] = plan_name
            break
    return entities


class Planner(ABC):
    name: str

    @abstractmethod
    def plan(self, request: str, candidates: list[EndpointSpec]) -> CallPlan:
        """Propose an endpoint call for a natural-language request."""


class StubPlanner(Planner):
    """Offline heuristic planner: keyword/regex routing over the candidate
    endpoints returned by the selector. Deterministic on purpose so
    planning tests never need network access or an API key.
    """

    name = "stub"

    def plan(self, request: str, candidates: list[EndpointSpec]) -> CallPlan:
        lowered = request.lower()
        entities = _extract_entities(request)
        by_id = {endpoint.operation_id: endpoint for endpoint in candidates}

        def build(operation_id: str, reason: str, expected_result: str, confidence: float) -> CallPlan | None:
            endpoint = by_id.get(operation_id)
            if endpoint is None:
                return None
            parameters = {
                param.name: entities[param.name] for param in endpoint.parameters if param.name in entities
            }
            return CallPlan(
                operation_id=endpoint.operation_id,
                method=endpoint.method,
                path=endpoint.path,
                parameters=parameters,
                reason=reason,
                expected_result=expected_result,
                requires_confirmation=endpoint.risk_level != "read_only",
                risk_level=endpoint.risk_level,
                confidence=confidence,
            )

        if "refund" in lowered:
            plan = build(
                "issue_refund",
                "Request asks to issue a refund against an invoice.",
                "A refund record is created against the given invoice.",
                0.8,
            )
            if plan is not None:
                plan.parameters.setdefault("reason", request[:200])
                return plan

        if "ticket" in lowered:
            plan = build(
                "create_ticket",
                "Request asks to open a support ticket.",
                "A new support ticket is created for the customer.",
                0.75,
            )
            if plan is not None:
                plan.parameters.setdefault("subject", request[:80])
                plan.parameters.setdefault("description", request)
                return plan

        if "plan" in entities and any(
            word in lowered for word in ("upgrade", "downgrade", "change", "update", "switch")
        ):
            plan = build(
                "update_subscription_plan",
                "Request asks to change a subscription's plan tier.",
                "The subscription's plan is updated to the requested tier.",
                0.75,
            )
            if plan is not None:
                return plan

        if "subscription" in lowered:
            plan = build(
                "list_customer_subscriptions",
                "Request asks about a customer's subscriptions.",
                "Returns the customer's subscriptions.",
                0.7,
            )
            if plan is not None:
                return plan

        if "invoice" in lowered:
            plan = build(
                "list_invoices",
                "Request asks about invoices.",
                "Returns matching invoices.",
                0.7,
            )
            if plan is not None:
                return plan

        if "email" in entities:
            plan = build(
                "list_customers",
                "Request looks up a customer by email.",
                "Returns the customer matching the given email.",
                0.7,
            )
            if plan is not None:
                return plan

        if "customer" in lowered and "customer_id" in entities:
            plan = build(
                "get_customer",
                "Request looks up a customer by id.",
                "Returns the customer's profile.",
                0.7,
            )
            if plan is not None:
                return plan

        if candidates:
            top = candidates[0]
            parameters = {p.name: entities[p.name] for p in top.parameters if p.name in entities}
            return CallPlan(
                operation_id=top.operation_id,
                method=top.method,
                path=top.path,
                parameters=parameters,
                reason=f"No strong keyword match; falling back to the closest matching endpoint '{top.operation_id}'.",
                expected_result="Uncertain — review before relying on this plan.",
                requires_confirmation=top.risk_level != "read_only",
                risk_level=top.risk_level,
                confidence=0.2,
            )

        return CallPlan(
            operation_id=None,
            method=None,
            path=None,
            parameters={},
            reason="No endpoint matches this request confidently enough to propose a call.",
            expected_result="",
            requires_confirmation=False,
            risk_level=None,
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
        model: str = "gpt-4o-mini",
        base_url: str = "https://api.openai.com/v1",
        timeout: float = 30.0,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._base_url = base_url
        self._timeout = timeout

    def plan(self, request: str, candidates: list[EndpointSpec]) -> CallPlan:
        if not self._api_key:
            raise RuntimeError("OPENAI_API_KEY is not configured")
        catalog = [
            {
                "operation_id": e.operation_id,
                "method": e.method,
                "path": e.path,
                "description": e.description,
                "parameters": [p.name for p in e.parameters],
                "risk_level": e.risk_level,
            }
            for e in candidates
        ]
        system_prompt = (
            "You plan a single API call for a natural-language business request. "
            f"Candidate endpoints: {json.dumps(catalog)}. Return a JSON object matching: "
            "operation_id (string or null), method (string or null), path (string or null), "
            "parameters (object), reason (string), expected_result (string), "
            "requires_confirmation (bool), risk_level (string or null), confidence (0-1)."
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
        return CallPlan.model_validate(json.loads(content))
