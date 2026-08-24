"""Assistant endpoints: submit a natural-language request and get back a
schema-validated call plan that has been dry-run previewed for writes and
gated by risk-based confirmation/approval.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.rate_limit import enforce_rate_limit
from app.planning.audit_log import log_workflow_event
from app.planning.models import (
    CreateWorkflowRequest,
    ResumeWorkflowRequest,
    Workflow,
    WorkflowView,
)
from app.planning.store import WorkflowStore
from app.planning.view import build_workflow_view
from app.planning.workflow import create_workflow, resume_workflow

router = APIRouter(prefix="/v1/assistant", tags=["assistant"], dependencies=[Depends(enforce_rate_limit)])

_store = WorkflowStore()


@router.post("/workflows", response_model=Workflow)
def create(req: CreateWorkflowRequest, request: Request) -> Workflow:
    openapi_schema = request.app.openapi()
    workflow = create_workflow(req, openapi_schema, now=datetime.now(timezone.utc))
    log_workflow_event("create", workflow)
    return _store.add(workflow)


@router.get("/workflows", response_model=list[Workflow])
def list_workflows() -> list[Workflow]:
    return _store.all()


@router.get("/workflows/{workflow_id}", response_model=Workflow)
def get_workflow(workflow_id: str) -> Workflow:
    workflow = _store.get(workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail=f"No workflow with id '{workflow_id}'.")
    return workflow


@router.get("/workflows/{workflow_id}/view", response_model=WorkflowView)
def get_workflow_view(workflow_id: str) -> WorkflowView:
    """UI read-model for one workflow: request, planned call(s), dry-run
    preview, which actions (approve/reject) are currently available, and
    the final result — everything a workflow review screen needs in one
    call.
    """
    workflow = _store.get(workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail=f"No workflow with id '{workflow_id}'.")
    return build_workflow_view(workflow)


@router.post("/workflows/{workflow_id}/resume", response_model=Workflow)
def resume(workflow_id: str, req: ResumeWorkflowRequest, request: Request) -> Workflow:
    workflow = _store.get(workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail=f"No workflow with id '{workflow_id}'.")
    try:
        updated = resume_workflow(workflow, req, now=datetime.now(timezone.utc), openapi_schema=request.app.openapi())
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    log_workflow_event("resume", updated)
    return _store.add(updated)
