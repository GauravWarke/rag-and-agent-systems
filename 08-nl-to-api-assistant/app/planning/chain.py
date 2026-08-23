"""Multi-step chained workflows: split a natural-language request that
describes several actions ("find the customer, then create a ticket") into
ordered clauses, plan each clause against the endpoint catalog, and thread
outputs from earlier steps into later ones via a typed workflow state
instead of relying on unstructured memory.
"""
from __future__ import annotations

import re
from typing import Any

from app.planning.models import ChainStepPlan, EndpointSpec
from app.planning.planner import Planner
from app.planning.selector import select_endpoints

_THEN = re.compile(r"\band\s+then\b|\bthen\b", re.IGNORECASE)
_CLAUSE_SEP = re.compile(r",\s*(?:and\s+)?|\s+and\s+", re.IGNORECASE)

# Maps an executed operation's result to the (id-slot-name, item-slot-name)
# it contributes to the workflow state, so later steps can reference "the
# customer just found" by name rather than re-parsing free text.
_STATE_ID_FIELDS: dict[str, tuple[str, str]] = {
    "list_customers": ("customer_id", "customer"),
    "get_customer": ("customer_id", "customer"),
    "list_customer_subscriptions": ("subscription_id", "subscription"),
    "list_invoices": ("invoice_id", "invoice"),
    "create_ticket": ("ticket_id", "ticket"),
    "update_subscription_plan": ("subscription_id", "subscription"),
    "issue_refund": ("refund_id", "refund"),
}

# Parameter names it is safe to auto-fill from earlier-step state when a
# step's own clause doesn't mention them directly (e.g. "fetch her
# subscription" has no id in the text, but the prior clause resolved one).
_CARRY_FORWARD_PARAMS = ("customer_id", "subscription_id", "invoice_id")


def split_chain_requests(request: str) -> list[str]:
    """Split a request into ordered clauses when it describes a chain of
    actions (contains "then"); otherwise return it unchanged as one clause.
    Once chain mode is triggered, each "then"-group is further split on
    commas/"and" so a single group like "find X, fetch Y, check Z" becomes
    three clauses.
    """
    if not _THEN.search(request):
        return [request]
    groups = [g.strip() for g in _THEN.split(request) if g.strip()]
    segments: list[str] = []
    for group in groups:
        segments.extend(part.strip() for part in _CLAUSE_SEP.split(group) if part.strip())
    return segments


def carry_forward_parameters(
    parameters: dict[str, Any], endpoint: EndpointSpec, state: dict[str, Any]
) -> dict[str, Any]:
    """Fill in parameters this step's own clause didn't mention from values
    earlier steps already resolved into the workflow state.
    """
    filled = dict(parameters)
    known_params = {p.name for p in endpoint.parameters}
    for name in _CARRY_FORWARD_PARAMS:
        if name in known_params and name not in filled and name in state:
            filled[name] = state[name]
    return filled


def extract_state_updates(operation_id: str, result: Any) -> tuple[dict[str, Any], str | None]:
    """After executing a step, derive the named values it contributes to the
    workflow state. Returns `(updates, clarification_message)`: a
    clarification message is returned instead of updates when the result is
    a list with more than one item, since silently picking one would be a
    guess rather than an answer.
    """
    mapping = _STATE_ID_FIELDS.get(operation_id)
    if mapping is None:
        return {}, None
    id_field, item_key = mapping

    if isinstance(result, list):
        if len(result) == 0:
            return {}, None
        if len(result) > 1:
            ids = [item.get("id") for item in result if isinstance(item, dict)]
            return {}, f"Found {len(result)} matching records for '{operation_id}' ({ids}) — which one did you mean?"
        item = result[0]
    else:
        item = result

    if not isinstance(item, dict) or "id" not in item:
        return {}, None
    return {id_field: item["id"], item_key: item}, None


def plan_chain(request: str, endpoints: list[EndpointSpec], planner: Planner) -> list[ChainStepPlan]:
    """Plan (but do not execute) every step of a chained request, in order.
    Each step is planned from its own clause text alone; state-based
    parameter carry-forward happens at execution time, once earlier steps'
    real results are known.
    """
    steps: list[ChainStepPlan] = []
    for segment in split_chain_requests(request):
        candidates = select_endpoints(segment, endpoints)
        plan = planner.plan(segment, candidates)
        output_key = _STATE_ID_FIELDS[plan.operation_id][1] if plan.operation_id in _STATE_ID_FIELDS else None
        steps.append(
            ChainStepPlan(
                segment=segment,
                operation_id=plan.operation_id,
                method=plan.method,
                path=plan.path,
                parameters=plan.parameters,
                reason=plan.reason,
                expected_result=plan.expected_result,
                risk_level=plan.risk_level,
                confidence=plan.confidence,
                output_key=output_key,
            )
        )
    return steps
