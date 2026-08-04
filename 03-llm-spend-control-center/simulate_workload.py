"""Simulate a mixed production workload against the gateway.

Sends a batch of synthetic chat requests spanning all three routing tiers,
several teams, and every priority level through the in-process gateway
(the offline `stub` provider — no API keys or network access required) and
writes a Markdown cost-savings + routing-quality report. This is the
artifact referenced in the Phase 6 case study.

Usage:
    python simulate_workload.py --requests 1000 --seed 42
"""
from __future__ import annotations

import argparse
import os
import random
from pathlib import Path

# The rate limiter is sized for real public traffic (60 req/min per client
# key); an in-process simulation would trip it almost immediately since
# every request shares the same TestClient "host". Raise it before the app
# module (and its module-level `settings`) is imported.
os.environ.setdefault("RATE_LIMIT_PER_MINUTE", "1000000")

from fastapi.testclient import TestClient

from app.main import app

TEAMS = ["team-alpha", "team-beta", "team-gamma", "team-delta", "team-epsilon"]

TIER1_FEATURES = ["ticket-tagging", "data-extraction", "format-cleanup"]
TIER2_FEATURES = ["support-bot", "content-summary", "sentiment-classification"]
TIER3_FEATURES = ["legal-review", "medical-advice", "financial-planning", "incident-triage"]

TIER1_PROMPTS = [
    "Extract the order ID from this text: Order #48213 shipped yesterday.",
    "Format this list into a table: apples, bananas, cherries.",
    "Convert this date to ISO 8601 format: March 3rd, 2024.",
    "List the email addresses found in this text: contact us at a@b.com or c@d.com.",
    "Capitalize the first letter of every word in this title: the great gatsby.",
]

TIER2_PROMPTS = [
    (
        "Summarize this support thread in two sentences: the customer reported a "
        "billing discrepancy, support confirmed a duplicate charge, and a refund was issued."
    ),
    "Classify the sentiment of this review: 'The product works but shipping took forever.'",
    (
        "Summarize the key changes in this release note: added dark mode, fixed a login bug, "
        "and improved search performance."
    ),
    "Classify this support ticket by category: 'I can't reset my password.'",
]

# Long enough (2000+ chars) or with tier-3 reasoning verbs to clear the
# complexity classifier's own tier-3 thresholds — see app/routing/classifier.py.
TIER3_PROMPTS = [
    "Analyze and diagnose the root cause of this recurring production outage, "
    "considering the deployment timeline, recent config changes, and the incident "
    "history below. " + "The service degraded gradually over several hours. " * 40,
    "Evaluate and recommend which vendor contract we should renew, weighing pricing, "
    "support SLAs, integration risk, and long-term lock-in. " + "Vendor comparison notes. " * 40,
    "Investigate this reported security incident and recommend an immediate response plan. "
    + "Incident timeline detail. " * 40,
    "Provide financial planning guidance for restructuring this customer's payment plan. "
    + "Account history detail. " * 40,
]

PRIORITIES = ["low", "normal", "high"]
PRIORITY_WEIGHTS = [0.2, 0.7, 0.1]

# Risk tags line up with the high-risk features so the complexity
# classifier's own tier-3 signal agrees with the routing overrides.
RISK_TAGS_BY_FEATURE = {
    "legal-review": ["legal"],
    "medical-advice": ["medical"],
    "financial-planning": ["financial"],
    "incident-triage": ["security"],
}

_STATUS_LABELS = {200: "200 OK", 402: "402 Budget blocked", 429: "429 Rate limited"}


def _build_request(rng: random.Random) -> dict:
    tier = rng.choices([1, 2, 3], weights=[0.5, 0.35, 0.15])[0]
    if tier == 1:
        feature, prompt = rng.choice(TIER1_FEATURES), rng.choice(TIER1_PROMPTS)
    elif tier == 2:
        feature, prompt = rng.choice(TIER2_FEATURES), rng.choice(TIER2_PROMPTS)
    else:
        feature, prompt = rng.choice(TIER3_FEATURES), rng.choice(TIER3_PROMPTS)

    return {
        "messages": [{"role": "user", "content": prompt}],
        "team_id": rng.choice(TEAMS),
        "feature": feature,
        "priority": rng.choices(PRIORITIES, weights=PRIORITY_WEIGHTS)[0],
        "risk_tags": RISK_TAGS_BY_FEATURE.get(feature, []),
    }


def run_simulation(n: int, seed: int) -> dict:
    rng = random.Random(seed)
    status_counts: dict[int, int] = {}
    tier_counts: dict[str, int] = {}
    escalation_count = 0
    warning_count = 0

    with TestClient(app) as client:
        for _ in range(n):
            payload = _build_request(rng)
            resp = client.post("/v1/chat", json=payload)
            status_counts[resp.status_code] = status_counts.get(resp.status_code, 0) + 1
            if resp.status_code == 200:
                body = resp.json()
                tier_key = str(body["routing_tier"]) if body["routing_tier"] is not None else "explicit"
                tier_counts[tier_key] = tier_counts.get(tier_key, 0) + 1
                if body["escalated"]:
                    escalation_count += 1
                if body["warnings"]:
                    warning_count += 1

        spend = client.get("/v1/dashboard/spend").json()
        savings = client.get("/v1/dashboard/savings").json()
        routing_quality = client.get("/v1/dashboard/routing-quality").json()
        quality_summary = client.get("/v1/quality/summary").json()

    return {
        "requests_sent": n,
        "seed": seed,
        "status_counts": status_counts,
        "tier_counts": tier_counts,
        "escalation_count": escalation_count,
        "warning_count": warning_count,
        "spend": spend,
        "savings": savings,
        "routing_quality": routing_quality,
        "quality_summary": quality_summary,
    }


def render_report(result: dict) -> str:
    savings = result["savings"]
    routing_quality = result["routing_quality"]
    lines = [
        "# Simulated Workload Cost Savings Report",
        "",
        (
            f"Sent **{result['requests_sent']}** synthetic requests (seed `{result['seed']}`) "
            "across 5 teams, 11 features, and all three routing tiers through the gateway's "
            "`stub` provider (offline, keyless, deterministic)."
        ),
        "",
        "## Headline result",
        "",
        (
            f"Reduced simulated LLM spend by **{savings['savings_pct']:.1%}** "
            f"(${savings['actual_cost_usd']:.4f} actual vs. "
            f"${savings['hypothetical_strongest_model_cost_usd']:.4f} if every request had gone "
            f"to `{savings['strongest_model']}`) while maintaining a "
            f"**{routing_quality['verifier_pass_rate']:.1%}** verification pass rate on sampled "
            "cheap-model responses."
        ),
        "",
        "## Request outcomes",
        "",
        "| Status | Count |",
        "|---|---|",
    ]
    for status, count in sorted(result["status_counts"].items()):
        lines.append(f"| {_STATUS_LABELS.get(status, str(status))} | {count} |")

    lines += [
        "",
        "## Routing tier distribution (successful requests)",
        "",
        "| Tier | Count |",
        "|---|---|",
    ]
    for tier, count in sorted(result["tier_counts"].items()):
        lines.append(f"| {tier} | {count} |")

    lines += [
        "",
        "## Routing quality",
        "",
        f"- Escalated requests (this run): {result['escalation_count']}",
        f"- Requests with budget warnings (this run): {result['warning_count']}",
        f"- Escalation rate (all-time): {routing_quality['escalation_rate']:.1%}",
        f"- Verifier pass rate (all-time): {routing_quality['verifier_pass_rate']:.1%}",
        f"- Quality checks sampled: {result['quality_summary']['total_checks']}",
        f"- Routing misses caught: {result['quality_summary']['routing_miss_count']}",
        "",
        "## Spend breakdown",
        "",
        f"- Daily cost: ${result['spend']['daily_cost_usd']:.4f}",
        f"- Monthly cost so far: ${result['spend']['monthly_cost_usd']:.4f}",
        f"- Monthly run-rate projection: ${result['spend']['monthly_projection_usd']:.4f}",
        "",
        "| Team | Spend (USD) |",
        "|---|---|",
    ]
    for team, cost in sorted(result["spend"]["by_team"].items()):
        lines.append(f"| {team} | ${cost:.4f} |")

    lines += [
        "",
        (
            "*Generated by `python simulate_workload.py`. Uses the offline stub provider, so "
            "cost and routing numbers are fully reproducible with the same `--seed` and no API "
            "keys — the quality-check sample count varies slightly run to run because the "
            "verifier's sampling itself is unseeded (see `app/main.py`).*"
        ),
        "",
    ]
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--requests", type=int, default=1000, help="number of simulated requests to send")
    parser.add_argument("--seed", type=int, default=42, help="random seed for reproducible workload generation")
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("reports/workload_simulation.md"),
        help="path to write the Markdown report to",
    )
    args = parser.parse_args()

    result = run_simulation(args.requests, args.seed)
    report = render_report(result)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(report)
    print(report)
    print(f"\nWrote report to {args.output}")


if __name__ == "__main__":
    main()
