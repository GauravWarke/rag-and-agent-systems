"""Portfolio walkthrough (Phase 6): drives the real FastAPI app end to end
through three requests — a read-only lookup that completes immediately, a
multi-step chain whose final write step pauses for confirmation, and a
high-risk write that pauses for human approval before executing. No API key
or network access required, matching this repo's offline-runnable-by-default
convention.
"""
from __future__ import annotations

from fastapi.testclient import TestClient

from app.main import app


def _render(label: str, workflow: dict) -> str:
    lines = [f"=== {label} ===", f"request: {workflow['request']!r}", f"status: {workflow['status']}"]
    for step in workflow["steps"]:
        lines.append(f"  [{step['node']}] {step['detail']}")
    if workflow.get("dry_run_preview"):
        lines.append(f"dry run: {workflow['dry_run_preview']}")
    if workflow.get("result") is not None:
        lines.append(f"result: {workflow['result']}")
    return "\n".join(lines)


def run_demo() -> str:
    sections: list[str] = []

    with TestClient(app) as client:
        read_only = client.post(
            "/v1/assistant/workflows", json={"user_id": "u_support", "request": "get customer cust_1"}
        ).json()
        sections.append(_render("Read-only request (auto-completes)", read_only))

        chain = client.post(
            "/v1/assistant/workflows",
            json={
                "user_id": "u_support",
                "request": (
                    "find customer by email chloe@example.com, then list her subscriptions, "
                    "then create a support ticket about the past due account"
                ),
            },
        ).json()
        sections.append(_render("Multi-step chain (pauses before the write step)", chain))

        chain_resumed = client.post(
            f"/v1/assistant/workflows/{chain['id']}/resume",
            json={"decision": "approve", "reviewer": "support_lead", "reason": "confirmed with customer"},
        ).json()
        sections.append(_render("Multi-step chain, resumed (confirmed and completed)", chain_resumed))

        high_risk = client.post(
            "/v1/assistant/workflows",
            json={"user_id": "u_billing", "request": "issue a refund of $10 for inv_1, service outage credit"},
        ).json()
        sections.append(_render("High-risk write (pauses for human approval)", high_risk))

        high_risk_resumed = client.post(
            f"/v1/assistant/workflows/{high_risk['id']}/resume",
            json={"decision": "approve", "reviewer": "billing_admin", "reason": "confirmed outage credit"},
        ).json()
        sections.append(_render("High-risk write, resumed (approved and executed)", high_risk_resumed))

    return "\n\n".join(sections)
