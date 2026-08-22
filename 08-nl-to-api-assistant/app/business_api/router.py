"""Mock SaaS admin business API: customers, subscriptions, invoices,
tickets, and refunds. Every endpoint declares its risk tier and required
roles as OpenAPI extensions (`x-risk-level`, `x-required-roles`) so the
planning assistant can parse them straight out of the generated schema.
"""
from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query

from app.business_api import data
from app.business_api.models import (
    CreateTicketRequest,
    Customer,
    Invoice,
    IssueRefundRequest,
    Refund,
    Subscription,
    Ticket,
    UpdateSubscriptionPlanRequest,
)
from app.core.rate_limit import enforce_rate_limit

router = APIRouter(prefix="/biz", tags=["business-api"], dependencies=[Depends(enforce_rate_limit)])

READ_ROLES = ["viewer", "analyst", "operator", "admin"]
LOW_RISK_WRITE_ROLES = ["analyst", "operator", "admin"]
HIGH_RISK_WRITE_ROLES = ["operator", "admin"]


def _risk_extra(risk_level: str, required_roles: list[str]) -> dict[str, Any]:
    return {"x-risk-level": risk_level, "x-required-roles": required_roles}


@router.get(
    "/customers",
    response_model=list[Customer],
    operation_id="list_customers",
    summary="List or search customers",
    description="List all customers, optionally filtered by an exact email match.",
    openapi_extra=_risk_extra("read_only", READ_ROLES),
)
def list_customers(email: str | None = Query(default=None, max_length=254)) -> list[Customer]:
    if email:
        customer = data.find_customer_by_email(email)
        return [customer] if customer else []
    return data.list_customers()


@router.get(
    "/customers/{customer_id}",
    response_model=Customer,
    operation_id="get_customer",
    summary="Get a customer by id",
    description="Fetch one customer's profile by their customer id.",
    openapi_extra=_risk_extra("read_only", READ_ROLES),
)
def get_customer(customer_id: str) -> Customer:
    customer = data.get_customer(customer_id)
    if customer is None:
        raise HTTPException(status_code=404, detail=f"No customer with id '{customer_id}'.")
    return customer


@router.get(
    "/customers/{customer_id}/subscriptions",
    response_model=list[Subscription],
    operation_id="list_customer_subscriptions",
    summary="List a customer's subscriptions",
    description="List all subscriptions belonging to one customer.",
    openapi_extra=_risk_extra("read_only", READ_ROLES),
)
def list_customer_subscriptions(customer_id: str) -> list[Subscription]:
    if data.get_customer(customer_id) is None:
        raise HTTPException(status_code=404, detail=f"No customer with id '{customer_id}'.")
    return data.list_subscriptions_for_customer(customer_id)


@router.get(
    "/invoices",
    response_model=list[Invoice],
    operation_id="list_invoices",
    summary="List invoices",
    description="List invoices, optionally filtered by customer id.",
    openapi_extra=_risk_extra("read_only", READ_ROLES),
)
def list_invoices(customer_id: str | None = Query(default=None, max_length=64)) -> list[Invoice]:
    return data.list_invoices(customer_id)


@router.post(
    "/tickets",
    response_model=Ticket,
    status_code=201,
    operation_id="create_ticket",
    summary="Create a support ticket",
    description="Open a new support ticket for a customer.",
    openapi_extra=_risk_extra("low_risk_write", LOW_RISK_WRITE_ROLES),
)
def create_ticket(req: CreateTicketRequest) -> Ticket:
    if data.get_customer(req.customer_id) is None:
        raise HTTPException(status_code=404, detail=f"No customer with id '{req.customer_id}'.")
    return data.create_ticket(req)


@router.patch(
    "/subscriptions/{subscription_id}",
    response_model=Subscription,
    operation_id="update_subscription_plan",
    summary="Update a subscription's plan",
    description="Change the plan tier of an existing subscription.",
    openapi_extra=_risk_extra("high_risk_write", HIGH_RISK_WRITE_ROLES),
)
def update_subscription_plan(subscription_id: str, req: UpdateSubscriptionPlanRequest) -> Subscription:
    subscription = data.update_subscription_plan(subscription_id, req.plan)
    if subscription is None:
        raise HTTPException(status_code=404, detail=f"No subscription with id '{subscription_id}'.")
    return subscription


@router.post(
    "/refunds",
    response_model=Refund,
    status_code=201,
    operation_id="issue_refund",
    summary="Issue a refund",
    description="Issue a refund against an existing invoice.",
    openapi_extra=_risk_extra("high_risk_write", HIGH_RISK_WRITE_ROLES),
)
def issue_refund(req: IssueRefundRequest) -> Refund:
    invoice = data.get_invoice(req.invoice_id)
    if invoice is None:
        raise HTTPException(status_code=404, detail=f"No invoice with id '{req.invoice_id}'.")
    if req.amount_cents > invoice.amount_cents:
        raise HTTPException(status_code=400, detail="Refund amount cannot exceed the invoice amount.")
    return data.create_refund(req)
