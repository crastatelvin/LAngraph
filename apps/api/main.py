from dataclasses import asdict
from contextlib import asynccontextmanager
import json
import time

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from apps.api.audit import AuditStore
from apps.api.context import RequestContext, get_request_context, require_roles
from apps.api.db import Base, engine, get_db
from apps.api.metrics import WorkflowMetricsStore
from apps.api.models import DebateModel
from apps.api.store import DebateStore
from packages.schemas.debate import (
    DebateApproveResponse,
    DebateCreateRequest,
    DebateCreateResponse,
    DebateEventsResponse,
    DebateRecord,
)

@asynccontextmanager
async def lifespan(_: FastAPI):
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(title="AI Parliament API", version="0.1.0", lifespan=lifespan)
store = DebateStore()
audit_store = AuditStore()
workflow_metrics_store = WorkflowMetricsStore()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/debates", response_model=DebateCreateResponse)
def create_debate(
    payload: DebateCreateRequest,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
) -> DebateCreateResponse:
    record, workflow_metrics = store.create(
        db,
        payload.proposal,
        tenant_id=ctx.tenant_id,
        request_id=ctx.request_id,
    )
    workflow_metrics_store.record_workflow(workflow_metrics)
    audit_store.append(
        db=db,
        tenant_id=ctx.tenant_id,
        actor_id=ctx.user_id,
        action="debate.create",
        resource=f"debates/{record.debate_id}",
        payload={
            "proposal": record.proposal,
            "role": ctx.user_role,
            "request_id": ctx.request_id,
            "workflow_metrics": workflow_metrics,
        },
    )
    return DebateCreateResponse(
        debate_id=record.debate_id,
        proposal=record.proposal,
        status=record.status,
    )


@app.get("/v1/debates/{debate_id}", response_model=DebateRecord)
def get_debate(
    debate_id: str,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
) -> DebateRecord:
    record = store.get(db, debate_id, tenant_id=ctx.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Debate not found")
    audit_store.append(
        db=db,
        tenant_id=ctx.tenant_id,
        actor_id=ctx.user_id,
        action="debate.read",
        resource=f"debates/{debate_id}",
        payload={"role": ctx.user_role, "request_id": ctx.request_id},
    )
    return record


@app.get("/v1/debates/{debate_id}/events", response_model=DebateEventsResponse)
def get_debate_events(
    debate_id: str,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
) -> DebateEventsResponse:
    events = store.get_events(db, debate_id, tenant_id=ctx.tenant_id)
    if events is None:
        raise HTTPException(status_code=404, detail="Debate not found")
    audit_store.append(
        db=db,
        tenant_id=ctx.tenant_id,
        actor_id=ctx.user_id,
        action="debate.events.read",
        resource=f"debates/{debate_id}/events",
        payload={"role": ctx.user_role, "request_id": ctx.request_id},
    )
    return DebateEventsResponse(debate_id=debate_id, events=events)


@app.post("/v1/debates/{debate_id}/approve", response_model=DebateApproveResponse)
def approve_debate(
    debate_id: str,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
) -> DebateApproveResponse:
    require_roles(ctx, {"admin", "owner"})
    record = store.approve(db, debate_id, tenant_id=ctx.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Debate not found")
    audit_store.append(
        db=db,
        tenant_id=ctx.tenant_id,
        actor_id=ctx.user_id,
        action="debate.approve",
        resource=f"debates/{debate_id}",
        payload={"status": record.status, "role": ctx.user_role, "request_id": ctx.request_id},
    )
    return DebateApproveResponse(debate_id=debate_id, status=record.status)


@app.get("/v1/admin/audit")
def get_audit_events(
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
) -> list[dict]:
    require_roles(ctx, {"admin", "owner"})
    return [asdict(event) for event in audit_store.list_for_tenant(db, ctx.tenant_id)]


@app.get("/v1/admin/metrics")
def get_metrics(ctx: RequestContext = Depends(get_request_context)) -> dict:
    require_roles(ctx, {"admin", "owner"})
    return workflow_metrics_store.snapshot()


@app.get("/v1/debates/{debate_id}/stream")
def stream_debate_events(
    debate_id: str,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    debate_exists = (
        db.query(DebateModel)
        .filter(DebateModel.debate_id == debate_id, DebateModel.tenant_id == ctx.tenant_id)
        .first()
    )
    if debate_exists is None:
        raise HTTPException(status_code=404, detail="Debate not found")

    def event_generator() -> str:
        events = store.get_events(db, debate_id, tenant_id=ctx.tenant_id) or []
        for event in events:
            yield f"data: {json.dumps(event.model_dump())}\n\n"
        # keep stream briefly alive for client compatibility
        time.sleep(0.1)

    return StreamingResponse(event_generator(), media_type="text/event-stream")
