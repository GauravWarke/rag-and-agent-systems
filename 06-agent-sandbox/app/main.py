"""Permissioned Tool-Using Agent Sandbox — a workspace assistant that can
use tools (calculator, sandboxed file reader, mock web search, CSV query,
mock ticket creation), gated by role permissions and risk-based approval.

Endpoints:
  GET  /health                       readiness probe
  GET  /v1/users                      list demo users and their roles
  GET  /v1/tools                      list the tool registry (spec, risk, roles)
  POST /v1/tools/call                 call one tool directly (low-level, permission-checked)
  POST /v1/agent/tasks                run a natural-language request through the agent workflow
  GET  /v1/agent/tasks                list agent tasks (including paused ones)
  GET  /v1/agent/tasks/{id}           fetch one agent task, with its full step trace
  POST /v1/agent/tasks/{id}/resume    approve/reject/modify/replan a paused task
  GET  /v1/agent/tasks/{id}/trace     timeline view of one task's steps, with latency/cost
  GET  /v1/agent/approvals            queue of tasks awaiting a human decision
  GET  /v1/agent/decisions            audit log of every approval decision made
  GET  /v1/agent/safety               fleet-wide safety analytics (tool usage, blocks, approval rate)
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import RedirectResponse

from app.agent.approvals import build_approval_queue
from app.agent.decisions import DecisionStore, build_decision_log
from app.agent.graph import resume_task, run_task
from app.agent.store import TaskStore
from app.core.config import settings
from app.core.models import (
    AgentTask,
    AgentTaskRequest,
    ApprovalQueueItem,
    DecisionLog,
    ResumeTaskRequest,
    SafetyAnalytics,
    ToolCallRequest,
    ToolCallResult,
    ToolSpec,
    TraceResponse,
    User,
)
from app.core.rate_limit import RateLimiter
from app.observability.safety import build_safety_analytics
from app.observability.tracing import build_trace
from app.permissions.users import list_users
from app.tools.executor import execute_tool_call
from app.tools.registry import list_tools

app = FastAPI(
    title='Permissioned Agent Sandbox',
    description=(
        'An agent that uses tools under a permission model. Every tool declares a '
        'required role and a risk tier; calls are checked before execution, rate '
        'limited, and high-risk actions pause for human approval. Every decision is '
        'written to an audit log.'
        '\n\n**Try it:** `GET /v1/tools` to see the registry, then `POST /v1/agent/tasks` '
        'to run a request through the workflow.'
    ),
    version="1.0.0",
)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse(url="/docs")

_limiter = RateLimiter(settings.rate_limit_per_minute)
_task_store = TaskStore()
_decision_store = DecisionStore()


def _rate_limited(request: Request) -> bool:
    client_key = request.client.host if request.client else "unknown"
    return not _limiter.allow(client_key)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/v1/users", response_model=list[User])
def get_users(request: Request) -> list[User]:
    if _rate_limited(request):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again shortly.")
    return list_users()


@app.get("/v1/tools", response_model=list[ToolSpec])
def get_tools(request: Request) -> list[ToolSpec]:
    if _rate_limited(request):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again shortly.")
    return list_tools()


@app.post("/v1/tools/call", response_model=ToolCallResult)
def call_tool(req: ToolCallRequest, request: Request) -> ToolCallResult:
    if _rate_limited(request):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again shortly.")
    return execute_tool_call(req)


@app.post("/v1/agent/tasks", response_model=AgentTask)
def create_task(req: AgentTaskRequest, request: Request) -> AgentTask:
    if _rate_limited(request):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again shortly.")
    task = run_task(req, now=datetime.now(timezone.utc))
    return _task_store.add(task)


@app.get("/v1/agent/tasks", response_model=list[AgentTask])
def list_tasks(request: Request) -> list[AgentTask]:
    if _rate_limited(request):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again shortly.")
    return _task_store.all()


@app.get("/v1/agent/tasks/{task_id}", response_model=AgentTask)
def get_task(task_id: str, request: Request) -> AgentTask:
    if _rate_limited(request):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again shortly.")
    task = _task_store.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"No task with id '{task_id}'.")
    return task


@app.post("/v1/agent/tasks/{task_id}/resume", response_model=AgentTask)
def resume(task_id: str, req: ResumeTaskRequest, request: Request) -> AgentTask:
    if _rate_limited(request):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again shortly.")
    task = _task_store.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"No task with id '{task_id}'.")
    try:
        updated = resume_task(task, req, now=datetime.now(timezone.utc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    _decision_store.add(build_decision_log(task, req, updated, now=datetime.now(timezone.utc)))
    return _task_store.add(updated)


@app.get("/v1/agent/tasks/{task_id}/trace", response_model=TraceResponse)
def get_task_trace(task_id: str, request: Request) -> TraceResponse:
    if _rate_limited(request):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again shortly.")
    task = _task_store.get(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail=f"No task with id '{task_id}'.")
    return build_trace(task, _decision_store.for_task(task_id))


@app.get("/v1/agent/approvals", response_model=list[ApprovalQueueItem])
def get_approval_queue(request: Request) -> list[ApprovalQueueItem]:
    if _rate_limited(request):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again shortly.")
    return build_approval_queue(_task_store.all())


@app.get("/v1/agent/decisions", response_model=list[DecisionLog])
def get_decisions(request: Request, task_id: str | None = None) -> list[DecisionLog]:
    if _rate_limited(request):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again shortly.")
    return _decision_store.for_task(task_id) if task_id else _decision_store.all()


@app.get("/v1/agent/safety", response_model=SafetyAnalytics)
def get_safety_analytics(request: Request) -> SafetyAnalytics:
    if _rate_limited(request):
        raise HTTPException(status_code=429, detail="Rate limit exceeded, try again shortly.")
    return build_safety_analytics(_task_store.all(), _decision_store.all())
