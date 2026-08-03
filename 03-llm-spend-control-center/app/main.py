"""LLM Spend Control Center — unified gateway, budgets, and complexity routing.

Budgets are enforced *before* the provider call (using spend recorded so
far) because the final cost of a request is only known *after* the
response comes back — the gateway can't know a request's own cost in
advance, only whether prior spend has already exhausted the budget.

Endpoints:
  GET  /health              readiness probe
  POST /v1/chat             send a chat-style request through the gateway
  GET  /v1/budgets/{team}   current budget status for a team
  GET  /v1/usage/summary    spend broken down by team, feature, and model
  GET  /v1/quality/summary  routing verification pass rate and misses
  GET  /v1/dashboard/savings          actual spend vs. an all-strongest-model baseline
  GET  /v1/dashboard/routing-quality  escalation rate, verifier pass rate, latency/error by model/provider
"""
from __future__ import annotations

import random
import uuid
from datetime import datetime, timezone

from fastapi import BackgroundTasks, FastAPI, HTTPException, Request

from app.budgets.policy import BudgetPolicyStore
from app.budgets.tracker import BudgetTracker
from app.core.config import settings
from app.core.models import GatewayRequest, GatewayResponse
from app.core.rate_limit import RateLimiter
from app.providers.registry import get_adapter
from app.quality.store import QualityStore
from app.quality.verifier import QualityVerifier
from app.registry.models import ModelRegistry, estimate_cost
from app.routing.overrides import RoutingOverrides
from app.routing.router import select_tier
from app.usage.store import UsageLogEntry, UsageStore

app = FastAPI(title="LLM Spend Control Center", version="0.1.0")

_limiter = RateLimiter(settings.rate_limit_per_minute)
_model_registry = ModelRegistry.load(settings.model_registry_path)
_usage_store = UsageStore()
_policy_store = BudgetPolicyStore.load(settings.budget_policies_path)
_budget_tracker = BudgetTracker(_usage_store, _policy_store, settings.budget_warning_threshold_pct)
_routing_overrides = RoutingOverrides.load(settings.routing_overrides_path)
_quality_store = QualityStore()


def _available_providers() -> set[str]:
    """Providers routing may pick without an explicit model request.

    Only providers with credentials (or, for self-hosted Ollama, an
    explicit opt-in) configured are eligible — routing should never
    silently pick a model the gateway can't actually reach.
    """
    providers = {"stub"}
    if settings.openai_api_key:
        providers.add("openai")
    if settings.anthropic_api_key:
        providers.add("anthropic")
    if settings.ollama_enabled:
        providers.add("ollama")
    return providers


_quality_verifier = QualityVerifier(
    _model_registry,
    _quality_store,
    get_adapter,
    _available_providers,
    settings.quality_similarity_threshold,
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/chat", response_model=GatewayResponse)
def chat(req: GatewayRequest, request: Request, background_tasks: BackgroundTasks) -> GatewayResponse:
    client_key = request.client.host if request.client else "unknown"
    if not _limiter.allow(client_key):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again shortly.")

    warnings: list[str] = []
    budget_result = _budget_tracker.check(req.team_id, req.feature)
    if budget_result.status == "blocked" and req.priority != "high" and not req.override_budget_block:
        raise HTTPException(
            status_code=402,
            detail=(
                f"Budget exceeded for {budget_result.scope} '{budget_result.key}': "
                f"${budget_result.spent_usd:.4f} of ${budget_result.limit_usd:.2f} used."
            ),
        )
    if budget_result.status == "warning":
        warnings.append(
            f"Budget at {budget_result.pct_used:.0%} for {budget_result.scope} '{budget_result.key}'."
        )

    routing_tier: int | None = None
    escalated = False
    escalation_reason: str | None = None
    try:
        if req.model:
            model_spec = _model_registry.get(req.model)
        else:
            routing_tier = select_tier(req, _routing_overrides)
            if routing_tier < 3 and req.priority == "high":
                escalated, escalation_reason, routing_tier = True, "high_priority", 3
            elif routing_tier < 3 and _quality_store.should_escalate(
                req.feature, settings.escalation_min_samples, settings.escalation_miss_rate_threshold
            ):
                escalated, escalation_reason, routing_tier = True, "low_confidence", 3
            model_spec = _model_registry.default_for_tier(routing_tier, _available_providers())
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc

    adapter = get_adapter(model_spec.provider)
    request_id = uuid.uuid4().hex
    now = datetime.now(timezone.utc)
    try:
        result = adapter.complete(req.messages, model_spec.name, req.max_tokens, req.temperature)
    except (RuntimeError, ValueError) as exc:
        _usage_store.log(
            UsageLogEntry(
                request_id=request_id,
                timestamp=now,
                team_id=req.team_id,
                feature=req.feature,
                model=model_spec.name,
                provider=model_spec.provider,
                input_tokens=0,
                output_tokens=0,
                latency_ms=0.0,
                status="error",
                cost_usd=0.0,
                escalated=escalated,
            )
        )
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    cost_usd = estimate_cost(model_spec, result.input_tokens, result.output_tokens)
    _usage_store.log(
        UsageLogEntry(
            request_id=request_id,
            timestamp=now,
            team_id=req.team_id,
            feature=req.feature,
            model=model_spec.name,
            provider=model_spec.provider,
            input_tokens=result.input_tokens,
            output_tokens=result.output_tokens,
            latency_ms=result.latency_ms,
            status="ok",
            cost_usd=cost_usd,
            escalated=escalated,
        )
    )

    if not escalated and model_spec.quality_tier < 3 and random.random() < settings.quality_sample_rate:
        background_tasks.add_task(
            _quality_verifier.verify,
            request_id=request_id,
            team_id=req.team_id,
            feature=req.feature,
            messages=req.messages,
            cheap_model_name=model_spec.name,
            cheap_output=result.output,
            max_tokens=req.max_tokens,
            temperature=req.temperature,
        )

    return GatewayResponse(
        request_id=request_id,
        output=result.output,
        provider=model_spec.provider,
        model_used=model_spec.name,
        input_tokens=result.input_tokens,
        output_tokens=result.output_tokens,
        routing_tier=routing_tier,
        cost_usd=cost_usd,
        latency_ms=result.latency_ms,
        budget_status=budget_result.status,
        warnings=warnings,
        escalated=escalated,
        escalation_reason=escalation_reason,
    )


@app.get("/v1/budgets/{team_id}")
def budget_status(team_id: str) -> dict:
    result = _budget_tracker.check(team_id, feature="__none__")
    return {
        "team_id": team_id,
        "status": result.status,
        "pct_used": result.pct_used,
        "spent_usd": result.spent_usd,
        "limit_usd": result.limit_usd,
    }


@app.get("/v1/usage/summary")
def usage_summary() -> dict:
    return {
        "by_team": _usage_store.spend_by_team(),
        "by_feature": _usage_store.spend_by_feature(),
        "by_model": _usage_store.spend_by_model(),
    }


@app.get("/v1/dashboard/spend")
def dashboard_spend() -> dict:
    return {
        "daily_cost_usd": _usage_store.spend_today_total(),
        "monthly_cost_usd": _usage_store.spend_month_total(),
        "monthly_projection_usd": _usage_store.monthly_projection(),
        "top_expensive_requests": _usage_store.top_expensive(),
        "by_team": _usage_store.spend_by_team(),
        "by_feature": _usage_store.spend_by_feature(),
        "by_model": _usage_store.spend_by_model(),
    }


@app.get("/v1/dashboard/savings")
def dashboard_savings() -> dict:
    strongest = _model_registry.default_for_tier(3, _available_providers())
    return _usage_store.savings_estimate(strongest)


@app.get("/v1/dashboard/routing-quality")
def dashboard_routing_quality() -> dict:
    return {
        "escalation_rate": _usage_store.escalation_rate(),
        "verifier_pass_rate": _quality_store.pass_rate(),
        "latency_ms_by_model": _usage_store.latency_by_model(),
        "error_rate_by_provider": _usage_store.error_rate_by_provider(),
    }


@app.get("/v1/quality/summary")
def quality_summary() -> dict:
    misses = _quality_store.misses()
    return {
        "total_checks": len(_quality_store.all()),
        "routing_miss_count": len(misses),
        "pass_rate": _quality_store.pass_rate(),
        "misses": [
            {
                "request_id": e.request_id,
                "team_id": e.team_id,
                "feature": e.feature,
                "cheap_model": e.cheap_model,
                "reference_model": e.reference_model,
                "similarity_score": e.similarity_score,
                "prompt_preview": e.prompt_preview,
                "reason": e.reason,
            }
            for e in misses
        ],
    }
