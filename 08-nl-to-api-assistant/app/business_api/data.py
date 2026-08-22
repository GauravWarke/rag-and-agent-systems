"""In-memory seeded mock data for the SaaS admin business domain.

This stands in for a real database: a handful of customers, subscriptions,
and invoices are seeded up front; tickets and refunds start empty and are
created through the API.
"""
from __future__ import annotations

import itertools
from datetime import datetime, timezone

from app.business_api.models import (
    CreateTicketRequest,
    Customer,
    Invoice,
    IssueRefundRequest,
    PlanName,
    Refund,
    Subscription,
    Ticket,
)


def _dt(year: int, month: int, day: int) -> datetime:
    return datetime(year, month, day, tzinfo=timezone.utc)


_CUSTOMERS: list[Customer] = [
    Customer(id="cust_1", name="Ana Ortiz", email="ana@example.com", created_at=_dt(2023, 1, 10)),
    Customer(id="cust_2", name="Ben Carter", email="ben@example.com", created_at=_dt(2023, 3, 22)),
    Customer(id="cust_3", name="Chloe Diaz", email="chloe@example.com", created_at=_dt(2024, 6, 5)),
]

_SUBSCRIPTIONS: list[Subscription] = [
    Subscription(id="sub_1", customer_id="cust_1", plan="pro", status="active", renewed_at=_dt(2026, 7, 1)),
    Subscription(id="sub_2", customer_id="cust_2", plan="basic", status="active", renewed_at=_dt(2026, 6, 15)),
    Subscription(
        id="sub_3", customer_id="cust_3", plan="enterprise", status="past_due", renewed_at=_dt(2026, 5, 1)
    ),
]

_INVOICES: list[Invoice] = [
    Invoice(id="inv_1", customer_id="cust_1", amount_cents=4900, status="paid", issued_at=_dt(2026, 7, 1)),
    Invoice(id="inv_2", customer_id="cust_2", amount_cents=1900, status="open", issued_at=_dt(2026, 6, 15)),
    Invoice(id="inv_3", customer_id="cust_3", amount_cents=29900, status="open", issued_at=_dt(2026, 5, 1)),
]

_TICKETS: list[Ticket] = []
_REFUNDS: list[Refund] = []

_ticket_ids = itertools.count(1)
_refund_ids = itertools.count(1)


def list_customers() -> list[Customer]:
    return list(_CUSTOMERS)


def get_customer(customer_id: str) -> Customer | None:
    return next((c for c in _CUSTOMERS if c.id == customer_id), None)


def find_customer_by_email(email: str) -> Customer | None:
    return next((c for c in _CUSTOMERS if c.email.lower() == email.lower()), None)


def list_subscriptions_for_customer(customer_id: str) -> list[Subscription]:
    return [s for s in _SUBSCRIPTIONS if s.customer_id == customer_id]


def get_subscription(subscription_id: str) -> Subscription | None:
    return next((s for s in _SUBSCRIPTIONS if s.id == subscription_id), None)


def list_invoices(customer_id: str | None = None) -> list[Invoice]:
    if customer_id is None:
        return list(_INVOICES)
    return [i for i in _INVOICES if i.customer_id == customer_id]


def get_invoice(invoice_id: str) -> Invoice | None:
    return next((i for i in _INVOICES if i.id == invoice_id), None)


def create_ticket(req: CreateTicketRequest) -> Ticket:
    ticket = Ticket(
        id=f"tic_{next(_ticket_ids)}",
        customer_id=req.customer_id,
        subject=req.subject,
        description=req.description,
        status="open",
        created_at=datetime.now(timezone.utc),
    )
    _TICKETS.append(ticket)
    return ticket


def update_subscription_plan(subscription_id: str, plan: PlanName) -> Subscription | None:
    subscription = get_subscription(subscription_id)
    if subscription is None:
        return None
    updated = subscription.model_copy(update={"plan": plan})
    _SUBSCRIPTIONS[_SUBSCRIPTIONS.index(subscription)] = updated
    return updated


def create_refund(req: IssueRefundRequest) -> Refund:
    refund = Refund(
        id=f"ref_{next(_refund_ids)}",
        invoice_id=req.invoice_id,
        amount_cents=req.amount_cents,
        reason=req.reason,
        status="issued",
        created_at=datetime.now(timezone.utc),
    )
    _REFUNDS.append(refund)
    return refund


def list_tickets() -> list[Ticket]:
    return list(_TICKETS)


def list_refunds() -> list[Refund]:
    return list(_REFUNDS)
