from dataclasses import asdict

from fastapi import Depends, FastAPI, HTTPException

from apps.api.audit import AuditStore
from apps.api.context import RequestContext, get_request_context
from apps.api.store import DebateStore
from packages.schemas.debate import (
    DebateApproveResponse,
    DebateCreateRequest,
    DebateCreateResponse,
    DebateEventsResponse,
    DebateRecord,
)

app = FastAPI(title="AI Parliament API", version="0.1.0")
store = DebateStore()
audit_store = AuditStore()


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/v1/debates", response_model=DebateCreateResponse)
def create_debate(
    payload: DebateCreateRequest,
    ctx: RequestContext = Depends(get_request_context),
) -> DebateCreateResponse:
    record = store.create(payload.proposal, tenant_id=ctx.tenant_id)
    audit_store.append(
        tenant_id=ctx.tenant_id,
        actor_id=ctx.user_id,
        action="debate.create",
        resource=f"debates/{record.debate_id}",
        payload={"proposal": record.proposal, "role": ctx.user_role},
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
) -> DebateRecord:
    record = store.get(debate_id, tenant_id=ctx.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Debate not found")
    audit_store.append(
        tenant_id=ctx.tenant_id,
        actor_id=ctx.user_id,
        action="debate.read",
        resource=f"debates/{debate_id}",
        payload={"role": ctx.user_role},
    )
    return record


@app.get("/v1/debates/{debate_id}/events", response_model=DebateEventsResponse)
def get_debate_events(
    debate_id: str,
    ctx: RequestContext = Depends(get_request_context),
) -> DebateEventsResponse:
    events = store.get_events(debate_id, tenant_id=ctx.tenant_id)
    if events is None:
        raise HTTPException(status_code=404, detail="Debate not found")
    audit_store.append(
        tenant_id=ctx.tenant_id,
        actor_id=ctx.user_id,
        action="debate.events.read",
        resource=f"debates/{debate_id}/events",
        payload={"role": ctx.user_role},
    )
    return DebateEventsResponse(debate_id=debate_id, events=events)


@app.post("/v1/debates/{debate_id}/approve", response_model=DebateApproveResponse)
def approve_debate(
    debate_id: str,
    ctx: RequestContext = Depends(get_request_context),
) -> DebateApproveResponse:
    record = store.approve(debate_id, tenant_id=ctx.tenant_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Debate not found")
    audit_store.append(
        tenant_id=ctx.tenant_id,
        actor_id=ctx.user_id,
        action="debate.approve",
        resource=f"debates/{debate_id}",
        payload={"status": record.status, "role": ctx.user_role},
    )
    return DebateApproveResponse(debate_id=debate_id, status=record.status)


@app.get("/v1/admin/audit")
def get_audit_events(ctx: RequestContext = Depends(get_request_context)) -> list[dict]:
    return [asdict(event) for event in audit_store.list_for_tenant(ctx.tenant_id)]
