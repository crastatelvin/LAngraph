from dataclasses import asdict
from contextlib import asynccontextmanager
import json
import logging
import os
import time

from fastapi import Depends, FastAPI, HTTPException
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.responses import StreamingResponse
from opentelemetry import trace
from sqlalchemy.orm import Session

from apps.api.audit import AuditStore
from apps.api.context import RequestContext, get_request_context, require_roles
from apps.api.db import Base, engine, get_db
from apps.api.metrics import WorkflowMetricsStore
from apps.api.request_metrics import EndpointMetricsStore
from apps.api.models import DebateModel
from apps.api.store import DebateStore
from apps.api.slack import SlackIntegration
from apps.api.telemetry import setup_telemetry
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
    setup_telemetry()
    yield


app = FastAPI(title="AI Parliament API", version="0.1.0", lifespan=lifespan)
store = DebateStore()
audit_store = AuditStore()
workflow_metrics_store = WorkflowMetricsStore()
endpoint_metrics_store = EndpointMetricsStore()
logger = logging.getLogger("api.requests")
tracer = trace.get_tracer("ai-parliament-api")
slack_integration = SlackIntegration()
rate_limit_store: dict[str, list[float]] = {}
MAX_REQUESTS_PER_MINUTE = int(os.getenv("MAX_REQUESTS_PER_MINUTE", "240"))
MAX_REQUEST_BODY_BYTES = int(os.getenv("MAX_REQUEST_BODY_BYTES", "16384"))
SECURITY_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "X-XSS-Protection": "1; mode=block",
}


@app.middleware("http")
async def observe_requests(request: Request, call_next):
    started = time.perf_counter()
    request_id = request.headers.get("X-Request-Id", "missing")
    route_key = f"{request.method} {request.url.path}"
    tenant_id = request.headers.get("X-Tenant-Id", "public")
    user_id = request.headers.get("X-User-Id", request.client.host if request.client else "unknown")
    limiter_key = f"{tenant_id}:{user_id}"
    now = time.time()
    recent = [ts for ts in rate_limit_store.get(limiter_key, []) if now - ts < 60.0]
    if len(recent) >= MAX_REQUESTS_PER_MINUTE:
        return JSONResponse(status_code=429, content={"detail": "Rate limit exceeded"})
    recent.append(now)
    rate_limit_store[limiter_key] = recent

    if request.method in {"POST", "PUT", "PATCH"}:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_REQUEST_BODY_BYTES:
            return JSONResponse(status_code=413, content={"detail": "Request body too large"})

    with tracer.start_as_current_span("http.request") as span:
        span.set_attribute("http.method", request.method)
        span.set_attribute("http.route", request.url.path)
        span.set_attribute("request.id", request_id)
        response = await call_next(request)
        latency_ms = (time.perf_counter() - started) * 1000
        endpoint_metrics_store.observe(route_key, latency_ms)
        span.set_attribute("http.status_code", response.status_code)
        span.set_attribute("http.latency_ms", round(latency_ms, 2))
        logger.info(
            "request_complete method=%s path=%s status=%s latency_ms=%.2f request_id=%s",
            request.method,
            request.url.path,
            response.status_code,
            latency_ms,
            request_id,
        )
        for key, value in SECURITY_HEADERS.items():
            response.headers[key] = value
        return response


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
    return {
        "workflow": workflow_metrics_store.snapshot(),
        "endpoints": endpoint_metrics_store.snapshot(),
    }


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


@app.post("/v1/integrations/slack/events")
async def slack_events(request: Request) -> JSONResponse:
    if not slack_integration.enabled():
        return JSONResponse(status_code=503, content={"detail": "Slack integration disabled"})

    body = await request.body()
    signature = request.headers.get("X-Slack-Signature")
    timestamp = request.headers.get("X-Slack-Request-Timestamp")
    if not slack_integration.verify_signature(timestamp, signature, body):
        return JSONResponse(status_code=401, content={"detail": "Invalid Slack signature"})

    payload = slack_integration.parse_body(body)
    if "challenge" in payload:
        return JSONResponse(status_code=200, content={"challenge": payload["challenge"]})

    event_id = payload.get("event_id")
    if slack_integration.is_duplicate(event_id):
        return JSONResponse(status_code=200, content={"status": "duplicate_ignored"})

    event_type = payload.get("event", {}).get("type", "unknown")
    return JSONResponse(status_code=200, content={"status": "accepted", "event_type": event_type})
