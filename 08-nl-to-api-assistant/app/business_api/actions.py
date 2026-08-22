"""Operation-id-keyed action registry over the mock business data layer.

This is the execution surface the planning assistant calls into directly
(in-process, no HTTP round trip) once a proposed call has passed schema
validation and risk-based gating. Every action takes a plain parameter
dict and returns JSON-serializable output, raising `ValueError` for
not-found/invalid domain state — the same failure mode the HTTP router
translates into 404/400 responses.
"""
from __future__ import annotations

from collections.abc import Callable
from typing import Any

from app.business_api import data
from app.business_api.models import (
    CreateTicketRequest,
    IssueRefundRequest,
    UpdateSubscriptionPlanRequest,
)


def _list_customers(params: dict[str, Any]) -> list[dict[str, Any]]:
    email = params.get("email")
    if email:
        customer = data.find_customer_by_email(email)
        return [customer.model_dump(mode="json")] if customer else []
    return [c.model_dump(mode="json") for c in data.list_customers()]


def _get_customer(params: dict[str, Any]) -> dict[str, Any]:
    customer_id = params["customer_id"]
    customer = data.get_customer(customer_id)
    if customer is None:
        raise ValueError(f"No customer with id '{customer_id}'.")
    return customer.model_dump(mode="json")


def _list_customer_subscriptions(params: dict[str, Any]) -> list[dict[str, Any]]:
    customer_id = params["customer_id"]
    if data.get_customer(customer_id) is None:
        raise ValueError(f"No customer with id '{customer_id}'.")
    return [s.model_dump(mode="json") for s in data.list_subscriptions_for_customer(customer_id)]


def _list_invoices(params: dict[str, Any]) -> list[dict[str, Any]]:
    return [i.model_dump(mode="json") for i in data.list_invoices(params.get("customer_id"))]


def _create_ticket(params: dict[str, Any]) -> dict[str, Any]:
    req = CreateTicketRequest(
        customer_id=params["customer_id"], subject=params["subject"], description=params["description"]
    )
    if data.get_customer(req.customer_id) is None:
        raise ValueError(f"No customer with id '{req.customer_id}'.")
    return data.create_ticket(req).model_dump(mode="json")


def _update_subscription_plan(params: dict[str, Any]) -> dict[str, Any]:
    subscription_id = params["subscription_id"]
    req = UpdateSubscriptionPlanRequest(plan=params["plan"])
    subscription = data.update_subscription_plan(subscription_id, req.plan)
    if subscription is None:
        raise ValueError(f"No subscription with id '{subscription_id}'.")
    return subscription.model_dump(mode="json")


def _issue_refund(params: dict[str, Any]) -> dict[str, Any]:
    req = IssueRefundRequest(
        invoice_id=params["invoice_id"], amount_cents=params["amount_cents"], reason=params["reason"]
    )
    invoice = data.get_invoice(req.invoice_id)
    if invoice is None:
        raise ValueError(f"No invoice with id '{req.invoice_id}'.")
    if req.amount_cents > invoice.amount_cents:
        raise ValueError("Refund amount cannot exceed the invoice amount.")
    return data.create_refund(req).model_dump(mode="json")


ACTIONS: dict[str, Callable[[dict[str, Any]], Any]] = {
    "list_customers": _list_customers,
    "get_customer": _get_customer,
    "list_customer_subscriptions": _list_customer_subscriptions,
    "list_invoices": _list_invoices,
    "create_ticket": _create_ticket,
    "update_subscription_plan": _update_subscription_plan,
    "issue_refund": _issue_refund,
}


def execute(operation_id: str, parameters: dict[str, Any]) -> Any:
    action = ACTIONS.get(operation_id)
    if action is None:
        raise ValueError(f"No executable action registered for operation '{operation_id}'.")
    return action(parameters)
