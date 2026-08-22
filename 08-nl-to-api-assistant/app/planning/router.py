"""Assistant endpoints: submit a natural-language request and get back a
schema-validated call plan that has been dry-run previewed for writes and
gated by risk-based confirmation/approval.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import APIRouter, Depends, HTTPException, Request

from app.core.rate_limit import enforce_rate_limit
from app.planning.models import CreateWorkflowRequest, ResumeWorkflowRequest, Workflow
from app.planning.store import WorkflowStore
from app.planning.workflow import create_workflow, resume_workflow

router = APIRouter(prefix="/v1/assistant", tags=["assistant"], dependencies=[Depends(enforce_rate_limit)])

_store = WorkflowStore()


@router.post("/workflows", response_model=Workflow)
def create(req: CreateWorkflowRequest, request: Request) -> Workflow:
    openapi_schema = request.app.openapi()
    workflow = create_workflow(req, openapi_schema, now=datetime.now(timezone.utc))
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


@router.post("/workflows/{workflow_id}/resume", response_model=Workflow)
def resume(workflow_id: str, req: ResumeWorkflowRequest) -> Workflow:
    workflow = _store.get(workflow_id)
    if workflow is None:
        raise HTTPException(status_code=404, detail=f"No workflow with id '{workflow_id}'.")
    try:
        updated = resume_workflow(workflow, req, now=datetime.now(timezone.utc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _store.add(updated)
