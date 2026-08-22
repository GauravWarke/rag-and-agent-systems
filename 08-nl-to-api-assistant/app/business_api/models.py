"""Domain models for the mock SaaS admin business system: customers,
subscriptions, invoices, tickets, and refunds.
"""
from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

PlanName = Literal["basic", "pro", "enterprise"]


class Customer(BaseModel):
    id: str
    name: str
    email: str
    created_at: datetime


class Subscription(BaseModel):
    id: str
    customer_id: str
    plan: PlanName
    status: Literal["active", "canceled", "past_due"]
    renewed_at: datetime


class Invoice(BaseModel):
    id: str
    customer_id: str
    amount_cents: int
    status: Literal["paid", "open", "void"]
    issued_at: datetime


class Ticket(BaseModel):
    id: str
    customer_id: str
    subject: str
    description: str
    status: Literal["open", "closed"]
    created_at: datetime


class Refund(BaseModel):
    id: str
    invoice_id: str
    amount_cents: int
    reason: str
    status: Literal["issued"]
    created_at: datetime


class CreateTicketRequest(BaseModel):
    customer_id: str = Field(min_length=1, max_length=64)
    subject: str = Field(min_length=1, max_length=200)
    description: str = Field(min_length=1, max_length=2000)


class UpdateSubscriptionPlanRequest(BaseModel):
    plan: PlanName


class IssueRefundRequest(BaseModel):
    invoice_id: str = Field(min_length=1, max_length=64)
    amount_cents: int = Field(gt=0)
    reason: str = Field(min_length=1, max_length=500)
