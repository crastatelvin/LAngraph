from dataclasses import asdict
from contextlib import asynccontextmanager
import json
import logging
import os
import time
from datetime import UTC, datetime
from uuid import uuid4

from fastapi import Depends, FastAPI, HTTPException
from fastapi import Request
from fastapi.responses import JSONResponse
from fastapi.responses import StreamingResponse
from opentelemetry import trace
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from apps.api.audit import AuditStore
from apps.api.chain import get_chain_adapter, refresh_tx_status
from apps.api.context import RequestContext, get_request_context, require_roles
from apps.api.db import Base, engine, get_db
from apps.api.metrics import WorkflowMetricsStore
from apps.api.request_metrics import EndpointMetricsStore
from apps.api.models import (
    AgentProfileModel,
    AgentProfileVersionModel,
    ChainAnchorModel,
    DebateModel,
    FederationModel,
    FederationSessionModel,
    FederationSessionSubmissionModel,
    SlackOutboundMessageModel,
)
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


class AgentRecord(BaseModel):
    agent_id: str
    tenant_id: str
    user_id: str
    name: str
    role: str
    traits: dict
    calibration_score: float
    version: int
    updated_at: str


class AgentPatchRequest(BaseModel):
    traits: dict = Field(default_factory=dict)
    reason: str = Field(default="manual_update", min_length=3, max_length=256)


class FederationCreateRequest(BaseModel):
    name: str = Field(min_length=3, max_length=128)


class FederationSessionCreateRequest(BaseModel):
    mode: str = Field(default="standard", min_length=3, max_length=32)


class FederationJoinRequest(BaseModel):
    parliament_name: str = Field(min_length=2, max_length=128)
    position: str = Field(pattern="^(APPROVED|REJECTED|INCONCLUSIVE)$")
    confidence: float = Field(ge=0.0, le=1.0)
    summary: str = Field(min_length=5, max_length=4000)
    weight: float = Field(default=1.0, ge=0.1, le=10.0)


class AnchorDecisionRequest(BaseModel):
    debate_id: str = Field(min_length=3, max_length=64)
    report_hash: str = Field(min_length=16, max_length=128)
    network: str = Field(default="testnet", min_length=3, max_length=64)


def _queue_counts(db: Session, tenant_id: str | None = None) -> tuple[int, int]:
    queued_query = db.query(SlackOutboundMessageModel).filter(
        SlackOutboundMessageModel.status.in_(["queued", "retry"])
    )
    failed_query = db.query(SlackOutboundMessageModel).filter(SlackOutboundMessageModel.status == "failed")
    if tenant_id:
        queued_query = queued_query.filter(SlackOutboundMessageModel.tenant_id == tenant_id)
        failed_query = failed_query.filter(SlackOutboundMessageModel.tenant_id == tenant_id)
    return queued_query.count(), failed_query.count()


def _slack_tenant_from_payload(payload: dict) -> str:
    team_id = payload.get("team_id") or payload.get("team")
    if isinstance(team_id, dict):
        team_id = team_id.get("id")
    event_team = payload.get("event", {}).get("team")
    resolved = team_id or event_team
    if not resolved:
        return "slack-unknown-team"
    return f"slack-{resolved}"


def _to_agent_record(row: AgentProfileModel) -> AgentRecord:
    return AgentRecord(
        agent_id=row.agent_id,
        tenant_id=row.tenant_id,
        user_id=row.user_id,
        name=row.name,
        role=row.role,
        traits=json.loads(row.traits_json),
        calibration_score=round(float(row.calibration_score), 4),
        version=row.version,
        updated_at=row.updated_at,
    )


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


@app.get("/v1/agents")
def list_agents(
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
) -> list[dict]:
    rows = (
        db.query(AgentProfileModel)
        .filter(AgentProfileModel.tenant_id == ctx.tenant_id)
        .order_by(AgentProfileModel.updated_at.desc())
        .all()
    )
    audit_store.append(
        db=db,
        tenant_id=ctx.tenant_id,
        actor_id=ctx.user_id,
        action="agents.list",
        resource="agents",
        payload={"count": len(rows), "request_id": ctx.request_id, "role": ctx.user_role},
    )
    return [_to_agent_record(row).model_dump() for row in rows]


@app.patch("/v1/agents/{agent_id}")
def patch_agent(
    agent_id: str,
    payload: AgentPatchRequest,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
) -> dict:
    require_roles(ctx, {"admin", "owner"})
    row = (
        db.query(AgentProfileModel)
        .filter(AgentProfileModel.agent_id == agent_id, AgentProfileModel.tenant_id == ctx.tenant_id)
        .first()
    )
    if row is None:
        row = AgentProfileModel(
            agent_id=agent_id,
            tenant_id=ctx.tenant_id,
            user_id=ctx.user_id,
            name=f"Agent {agent_id[:8]}",
            role="representative",
            traits_json=json.dumps(payload.traits),
            calibration_score=0.5,
            version=1,
            updated_at=datetime.now(UTC).isoformat(),
        )
        db.add(row)
    else:
        previous_traits = row.traits_json
        previous_calibration = row.calibration_score
        db.add(
            AgentProfileVersionModel(
                agent_id=row.agent_id,
                tenant_id=row.tenant_id,
                version=row.version,
                traits_json=previous_traits,
                calibration_score=previous_calibration,
                reason=payload.reason,
                created_at=datetime.now(UTC).isoformat(),
            )
        )
        row.version += 1
        row.traits_json = json.dumps(payload.traits)
        row.updated_at = datetime.now(UTC).isoformat()

    db.commit()
    db.refresh(row)
    audit_store.append(
        db=db,
        tenant_id=ctx.tenant_id,
        actor_id=ctx.user_id,
        action="agent.patch",
        resource=f"agents/{agent_id}",
        payload={"version": row.version, "reason": payload.reason, "request_id": ctx.request_id},
    )
    return _to_agent_record(row).model_dump()


@app.post("/v1/agents/{agent_id}/recalibrate")
def recalibrate_agent(
    agent_id: str,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
) -> dict:
    require_roles(ctx, {"admin", "owner"})
    row = (
        db.query(AgentProfileModel)
        .filter(AgentProfileModel.agent_id == agent_id, AgentProfileModel.tenant_id == ctx.tenant_id)
        .first()
    )
    if row is None:
        raise HTTPException(status_code=404, detail="Agent not found")

    db.add(
        AgentProfileVersionModel(
            agent_id=row.agent_id,
            tenant_id=row.tenant_id,
            version=row.version,
            traits_json=row.traits_json,
            calibration_score=row.calibration_score,
            reason="recalibration",
            created_at=datetime.now(UTC).isoformat(),
        )
    )
    # Simple bounded calibration update until full evaluator pipeline is added.
    row.version += 1
    row.calibration_score = round(min(0.95, row.calibration_score + 0.05), 4)
    row.updated_at = datetime.now(UTC).isoformat()
    db.commit()
    db.refresh(row)
    audit_store.append(
        db=db,
        tenant_id=ctx.tenant_id,
        actor_id=ctx.user_id,
        action="agent.recalibrate",
        resource=f"agents/{agent_id}",
        payload={"version": row.version, "request_id": ctx.request_id},
    )
    return _to_agent_record(row).model_dump()


@app.post("/v1/federations")
def create_federation(
    payload: FederationCreateRequest,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
) -> dict:
    require_roles(ctx, {"admin", "owner"})
    federation_id = str(uuid4())
    row = FederationModel(
        federation_id=federation_id,
        tenant_id=ctx.tenant_id,
        name=payload.name,
        status="active",
        created_by=ctx.user_id,
        created_at=datetime.now(UTC).isoformat(),
    )
    db.add(row)
    db.commit()
    audit_store.append(
        db=db,
        tenant_id=ctx.tenant_id,
        actor_id=ctx.user_id,
        action="federation.create",
        resource=f"federations/{federation_id}",
        payload={"name": payload.name, "request_id": ctx.request_id},
    )
    return {"federation_id": federation_id, "name": payload.name, "status": "active"}


@app.post("/v1/federations/{federation_id}/sessions")
def create_federation_session(
    federation_id: str,
    payload: FederationSessionCreateRequest,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
) -> dict:
    require_roles(ctx, {"admin", "owner"})
    federation = (
        db.query(FederationModel)
        .filter(FederationModel.federation_id == federation_id, FederationModel.tenant_id == ctx.tenant_id)
        .first()
    )
    if federation is None:
        raise HTTPException(status_code=404, detail="Federation not found")
    session_id = str(uuid4())
    row = FederationSessionModel(
        session_id=session_id,
        federation_id=federation_id,
        tenant_id=ctx.tenant_id,
        status="open",
        created_by=ctx.user_id,
        created_at=datetime.now(UTC).isoformat(),
    )
    db.add(row)
    db.commit()
    audit_store.append(
        db=db,
        tenant_id=ctx.tenant_id,
        actor_id=ctx.user_id,
        action="federation.session.create",
        resource=f"federations/{federation_id}/sessions/{session_id}",
        payload={"mode": payload.mode, "request_id": ctx.request_id},
    )
    return {"session_id": session_id, "federation_id": federation_id, "status": "open"}


@app.post("/v1/federations/sessions/{session_id}/join")
def join_federation_session(
    session_id: str,
    payload: FederationJoinRequest,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
) -> dict:
    session = (
        db.query(FederationSessionModel)
        .filter(FederationSessionModel.session_id == session_id, FederationSessionModel.tenant_id == ctx.tenant_id)
        .first()
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Federation session not found")
    if session.status != "open":
        raise HTTPException(status_code=409, detail="Federation session is closed")
    db.add(
        FederationSessionSubmissionModel(
            session_id=session_id,
            tenant_id=ctx.tenant_id,
            parliament_name=payload.parliament_name,
            position=payload.position,
            confidence=payload.confidence,
            summary=payload.summary,
            weight=payload.weight,
            submitted_by=ctx.user_id,
            submitted_at=datetime.now(UTC).isoformat(),
        )
    )
    db.commit()
    audit_store.append(
        db=db,
        tenant_id=ctx.tenant_id,
        actor_id=ctx.user_id,
        action="federation.session.join",
        resource=f"federations/sessions/{session_id}",
        payload={"parliament_name": payload.parliament_name, "request_id": ctx.request_id},
    )
    return {"session_id": session_id, "joined": True, "parliament_name": payload.parliament_name}


@app.get("/v1/federations/sessions/{session_id}/decision")
def federation_session_decision(
    session_id: str,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
) -> dict:
    session = (
        db.query(FederationSessionModel)
        .filter(FederationSessionModel.session_id == session_id, FederationSessionModel.tenant_id == ctx.tenant_id)
        .first()
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Federation session not found")
    submissions = (
        db.query(FederationSessionSubmissionModel)
        .filter(
            FederationSessionSubmissionModel.session_id == session_id,
            FederationSessionSubmissionModel.tenant_id == ctx.tenant_id,
        )
        .all()
    )
    if not submissions:
        return {
            "session_id": session_id,
            "federation_id": session.federation_id,
            "decision": "INCONCLUSIVE",
            "confidence": "low",
            "reason": "No submissions yet",
            "submissions": 0,
        }

    score = 0.0
    total_weight = 0.0
    for submission in submissions:
        stance = 1 if submission.position == "APPROVED" else -1 if submission.position == "REJECTED" else 0
        weighted = stance * submission.confidence * submission.weight
        score += weighted
        total_weight += submission.weight
    normalized = score / total_weight if total_weight > 0 else 0.0
    decision = "APPROVED" if normalized > 0.15 else "REJECTED" if normalized < -0.15 else "INCONCLUSIVE"
    confidence = "high" if abs(normalized) > 0.7 else "medium" if abs(normalized) > 0.35 else "low"
    dissent = [s.parliament_name for s in submissions if (decision == "APPROVED" and s.position != "APPROVED")]
    if decision == "REJECTED":
        dissent = [s.parliament_name for s in submissions if s.position != "REJECTED"]
    audit_store.append(
        db=db,
        tenant_id=ctx.tenant_id,
        actor_id=ctx.user_id,
        action="federation.session.decision.read",
        resource=f"federations/sessions/{session_id}/decision",
        payload={"submissions": len(submissions), "request_id": ctx.request_id},
    )
    return {
        "session_id": session_id,
        "federation_id": session.federation_id,
        "decision": decision,
        "confidence": confidence,
        "score": round(normalized, 4),
        "submissions": len(submissions),
        "dissenting_parliaments": dissent,
    }


@app.post("/v1/chain/anchor-decision")
def anchor_decision(
    payload: AnchorDecisionRequest,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
) -> dict:
    require_roles(ctx, {"admin", "owner"})
    adapter = get_chain_adapter()
    anchor_result = adapter.anchor_decision(
        debate_id=payload.debate_id,
        report_hash=payload.report_hash,
        network=payload.network,
    )
    existing = (
        db.query(ChainAnchorModel)
        .filter(ChainAnchorModel.tenant_id == ctx.tenant_id, ChainAnchorModel.tx_hash == anchor_result["tx_hash"])
        .first()
    )
    if existing is not None:
        return {
            "anchor_id": existing.anchor_id,
            "tx_hash": existing.tx_hash,
            "status": existing.status,
            "provider": existing.provider,
            "network": existing.network,
            "duplicate": True,
        }
    now_iso = datetime.now(UTC).isoformat()
    row = ChainAnchorModel(
        anchor_id=str(uuid4()),
        tenant_id=ctx.tenant_id,
        debate_id=payload.debate_id,
        report_hash=payload.report_hash,
        tx_hash=anchor_result["tx_hash"],
        provider=anchor_result["provider"],
        network=anchor_result["network"],
        status="submitted",
        submitted_by=ctx.user_id,
        created_at=now_iso,
        updated_at=now_iso,
    )
    db.add(row)
    db.commit()
    audit_store.append(
        db=db,
        tenant_id=ctx.tenant_id,
        actor_id=ctx.user_id,
        action="chain.anchor.create",
        resource=f"chain/tx/{row.tx_hash}",
        payload={"debate_id": payload.debate_id, "network": payload.network, "request_id": ctx.request_id},
    )
    return {
        "anchor_id": row.anchor_id,
        "tx_hash": row.tx_hash,
        "status": row.status,
        "provider": row.provider,
        "network": row.network,
        "duplicate": False,
    }


@app.get("/v1/chain/tx/{tx_hash}")
def get_chain_tx(
    tx_hash: str,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
) -> dict:
    require_roles(ctx, {"admin", "owner"})
    refreshed = refresh_tx_status(db=db, tenant_id=ctx.tenant_id, tx_hash=tx_hash)
    if refreshed is None:
        raise HTTPException(status_code=404, detail="Transaction not found")
    audit_store.append(
        db=db,
        tenant_id=ctx.tenant_id,
        actor_id=ctx.user_id,
        action="chain.tx.read",
        resource=f"chain/tx/{tx_hash}",
        payload={"request_id": ctx.request_id, "status": refreshed["status"]},
    )
    return refreshed


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


@app.get("/v1/admin/slo")
def get_slo(
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
) -> dict:
    require_roles(ctx, {"admin", "owner"})
    workflow = workflow_metrics_store.snapshot()
    endpoints = endpoint_metrics_store.snapshot()
    queued, failed = _queue_counts(db, tenant_id=ctx.tenant_id)
    fallback_rate = 0.0
    if workflow["total_runs"] > 0:
        fallback_rate = round(workflow["fallback_count"] / workflow["total_runs"], 4)
    return {
        "slo_targets": {
            "api_non_llm_p95_ms_target": 700,
            "debate_completion_target_s": 60,
        },
        "observed": {
            "workflow_avg_latency_ms": workflow["avg_workflow_latency_ms"],
            "workflow_fallback_rate": fallback_rate,
            "workflow_parse_failures": workflow["parse_failure_count"],
            "endpoint_count": len(endpoints),
            "slack_queue_depth": queued,
            "slack_failed_messages": failed,
        },
    }


@app.get("/v1/admin/health/dependencies")
def admin_health_dependencies(
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
) -> dict:
    require_roles(ctx, {"admin", "owner"})
    db_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"

    slack_enabled = slack_integration.enabled()
    slack_token_configured = bool(os.getenv("SLACK_BOT_TOKEN"))
    queue_depth, failed_depth = _queue_counts(db, tenant_id=ctx.tenant_id)

    return {
        "database": {"status": db_status},
        "slack": {
            "enabled": slack_enabled,
            "bot_token_configured": slack_token_configured,
            "ready": (not slack_enabled) or (slack_enabled and slack_token_configured),
        },
        "worker_queue": {
            "queued": queue_depth,
            "failed": failed_depth,
            "status": "backlog" if queue_depth > 100 else "ok",
        },
    }


@app.get("/v1/admin/overview")
def admin_overview(
    compact: bool = False,
    tenant_id: str | None = None,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
) -> dict:
    require_roles(ctx, {"admin", "owner"})
    scope_tenant_id = ctx.tenant_id
    if tenant_id and tenant_id != ctx.tenant_id:
        if ctx.user_role != "owner":
            raise HTTPException(status_code=403, detail="Only owner can query cross-tenant overview")
        scope_tenant_id = tenant_id

    # Metrics snapshot
    workflow = workflow_metrics_store.snapshot()
    endpoints = endpoint_metrics_store.snapshot()

    # SLO snapshot
    queued, failed = _queue_counts(db, tenant_id=scope_tenant_id)
    fallback_rate = 0.0
    if workflow["total_runs"] > 0:
        fallback_rate = round(workflow["fallback_count"] / workflow["total_runs"], 4)

    # Dependency health snapshot
    db_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        db_status = "error"
    slack_enabled = slack_integration.enabled()
    slack_token_configured = bool(os.getenv("SLACK_BOT_TOKEN"))

    payload = {
        "scope": {
            "requested_tenant_id": tenant_id,
            "effective_tenant_id": scope_tenant_id,
            "queue_scope": "tenant",
        },
        "health": {
            "database": {"status": db_status},
            "slack": {
                "enabled": slack_enabled,
                "bot_token_configured": slack_token_configured,
                "ready": (not slack_enabled) or (slack_enabled and slack_token_configured),
            },
            "worker_queue": {
                "queued": queued,
                "failed": failed,
                "status": "backlog" if queued > 100 else "ok",
            },
        },
        "slo": {
            "slo_targets": {
                "api_non_llm_p95_ms_target": 700,
                "debate_completion_target_s": 60,
            },
            "observed": {
                "workflow_avg_latency_ms": workflow["avg_workflow_latency_ms"],
                "workflow_fallback_rate": fallback_rate,
                "workflow_parse_failures": workflow["parse_failure_count"],
                "endpoint_count": len(endpoints),
                "slack_queue_depth": queued,
                "slack_failed_messages": failed,
            },
        },
    }
    if compact:
        payload["metrics"] = {
            "workflow_total_runs": workflow["total_runs"],
            "workflow_fallback_count": workflow["fallback_count"],
            "endpoint_count": len(endpoints),
        }
    else:
        payload["metrics"] = {
            "workflow": workflow,
            "endpoints": endpoints,
        }
    return payload


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
async def slack_events(request: Request, db: Session = Depends(get_db)) -> JSONResponse:
    if not slack_integration.enabled():
        return JSONResponse(status_code=503, content={"detail": "Slack integration disabled"})

    body = await request.body()
    signature = request.headers.get("X-Slack-Signature")
    timestamp = request.headers.get("X-Slack-Request-Timestamp")
    if not slack_integration.verify_signature(timestamp, signature, body):
        return JSONResponse(status_code=401, content={"detail": "Invalid Slack signature"})

    payload = slack_integration.parse_body(body)
    slack_tenant_id = _slack_tenant_from_payload(payload)
    if "challenge" in payload:
        return JSONResponse(status_code=200, content={"challenge": payload["challenge"]})

    event_id = payload.get("event_id")
    if slack_integration.is_duplicate(db, event_id, tenant_id=slack_tenant_id):
        return JSONResponse(status_code=200, content={"status": "duplicate_ignored"})

    event_type = payload.get("event", {}).get("type", "unknown")
    return JSONResponse(status_code=200, content={"status": "accepted", "event_type": event_type})


@app.post("/v1/integrations/slack/commands")
async def slack_commands(request: Request, db: Session = Depends(get_db)) -> JSONResponse:
    if not slack_integration.enabled():
        return JSONResponse(status_code=503, content={"detail": "Slack integration disabled"})

    body = await request.body()
    signature = request.headers.get("X-Slack-Signature")
    timestamp = request.headers.get("X-Slack-Request-Timestamp")
    if not slack_integration.verify_signature(timestamp, signature, body):
        return JSONResponse(status_code=401, content={"detail": "Invalid Slack signature"})

    form = slack_integration.parse_form_body(body)
    command = form.get("command", "")
    text = form.get("text", "").strip()
    team_id = form.get("team_id", "unknown-team")
    user_id = form.get("user_id", "unknown-user")

    if command != "/debate":
        return JSONResponse(status_code=200, content={"response_type": "ephemeral", "text": "Unsupported command."})
    if not text:
        return JSONResponse(
            status_code=200,
            content={"response_type": "ephemeral", "text": "Usage: /debate <proposal text>"},
        )

    tenant_id = f"slack-{team_id}"
    request_id = f"slack-cmd-{int(time.time() * 1000)}"
    record, workflow_metrics = store.create(
        db=db,
        proposal=text,
        tenant_id=tenant_id,
        request_id=request_id,
    )
    workflow_metrics_store.record_workflow(workflow_metrics)
    audit_store.append(
        db=db,
        tenant_id=tenant_id,
        actor_id=f"slack-{user_id}",
        action="slack.command.debate.create",
        resource=f"debates/{record.debate_id}",
        payload={"request_id": request_id, "source": "slack", "command": command},
    )
    channel_id = form.get("channel_id", "")
    if channel_id:
        slack_integration.queue_thread_message(
            db=db,
            tenant_id=tenant_id,
            channel=channel_id,
            text=f"Debate `{record.debate_id}` queued. Proposal: {record.proposal}",
            dedupe_key=f"debate-created:{record.debate_id}",
        )
    return JSONResponse(
        status_code=200,
        content={
            "response_type": "in_channel",
            "text": f"Debate created: {record.debate_id} for proposal '{record.proposal}'",
        },
    )


@app.get("/v1/integrations/slack/outbound/status")
def slack_outbound_status(
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
) -> dict:
    require_roles(ctx, {"admin", "owner"})
    return slack_integration.outbound_status(db, tenant_id=ctx.tenant_id)


@app.post("/v1/integrations/slack/outbound/flush")
def slack_outbound_flush(
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
) -> dict:
    require_roles(ctx, {"admin", "owner"})
    return slack_integration.flush_outbound_queue(db, tenant_id=ctx.tenant_id)


@app.post("/v1/admin/slack/cleanup")
def slack_cleanup(
    retention_hours: int = 24,
    ctx: RequestContext = Depends(get_request_context),
    db: Session = Depends(get_db),
) -> dict:
    require_roles(ctx, {"admin", "owner"})
    if retention_hours < 1 or retention_hours > 24 * 30:
        raise HTTPException(status_code=400, detail="retention_hours must be between 1 and 720")
    return slack_integration.cleanup_old_state(db=db, retention_hours=retention_hours)
