from sqlalchemy import Float, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from apps.api.db import Base


class DebateModel(Base):
    __tablename__ = "debates"

    debate_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), index=True)
    proposal: Mapped[str] = mapped_column(Text())
    status: Mapped[str] = mapped_column(String(32))


class DebateEventModel(Base):
    __tablename__ = "debate_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    debate_id: Mapped[str] = mapped_column(String(64), index=True)
    tenant_id: Mapped[str] = mapped_column(String(128), index=True)
    seq: Mapped[int] = mapped_column(Integer)
    event_type: Mapped[str] = mapped_column(String(64))
    payload_json: Mapped[str] = mapped_column(Text())


class AuditEventModel(Base):
    __tablename__ = "audit_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(128), index=True)
    actor_id: Mapped[str] = mapped_column(String(128))
    action: Mapped[str] = mapped_column(String(128))
    resource: Mapped[str] = mapped_column(String(256))
    payload_json: Mapped[str] = mapped_column(Text())
    timestamp: Mapped[str] = mapped_column(String(64))


class SlackInboundEventModel(Base):
    __tablename__ = "slack_inbound_events"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(128), index=True)
    event_id: Mapped[str] = mapped_column(String(128), index=True)
    seen_at: Mapped[str] = mapped_column(String(64))


class SlackSentDedupeModel(Base):
    __tablename__ = "slack_sent_dedupes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(128), index=True)
    dedupe_key: Mapped[str] = mapped_column(String(256), index=True)
    sent_at: Mapped[str] = mapped_column(String(64))


class SlackOutboundMessageModel(Base):
    __tablename__ = "slack_outbound_messages"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String(128), index=True)
    channel: Mapped[str] = mapped_column(String(128), index=True)
    text: Mapped[str] = mapped_column(Text())
    thread_ts: Mapped[str] = mapped_column(String(64), nullable=True)
    dedupe_key: Mapped[str] = mapped_column(String(256), nullable=True, index=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(32), default="queued", index=True)
    created_at: Mapped[str] = mapped_column(String(64))


class AgentProfileModel(Base):
    __tablename__ = "agent_profiles"

    agent_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), index=True)
    user_id: Mapped[str] = mapped_column(String(128), index=True)
    name: Mapped[str] = mapped_column(String(128))
    role: Mapped[str] = mapped_column(String(64))
    traits_json: Mapped[str] = mapped_column(Text())
    calibration_score: Mapped[float] = mapped_column(Float(), default=0.5)
    version: Mapped[int] = mapped_column(Integer, default=1)
    updated_at: Mapped[str] = mapped_column(String(64))


class AgentProfileVersionModel(Base):
    __tablename__ = "agent_profile_versions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    agent_id: Mapped[str] = mapped_column(String(64), index=True)
    tenant_id: Mapped[str] = mapped_column(String(128), index=True)
    version: Mapped[int] = mapped_column(Integer)
    traits_json: Mapped[str] = mapped_column(Text())
    calibration_score: Mapped[float] = mapped_column(Float(), default=0.5)
    reason: Mapped[str] = mapped_column(String(256))
    created_at: Mapped[str] = mapped_column(String(64))


class FederationModel(Base):
    __tablename__ = "federations"

    federation_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), index=True)
    name: Mapped[str] = mapped_column(String(128))
    status: Mapped[str] = mapped_column(String(32), default="active")
    created_by: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[str] = mapped_column(String(64))


class FederationSessionModel(Base):
    __tablename__ = "federation_sessions"

    session_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    federation_id: Mapped[str] = mapped_column(String(64), index=True)
    tenant_id: Mapped[str] = mapped_column(String(128), index=True)
    status: Mapped[str] = mapped_column(String(32), default="open")
    created_by: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[str] = mapped_column(String(64))


class FederationSessionSubmissionModel(Base):
    __tablename__ = "federation_session_submissions"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    session_id: Mapped[str] = mapped_column(String(64), index=True)
    tenant_id: Mapped[str] = mapped_column(String(128), index=True)
    parliament_name: Mapped[str] = mapped_column(String(128))
    position: Mapped[str] = mapped_column(String(32))
    confidence: Mapped[float] = mapped_column(Float())
    summary: Mapped[str] = mapped_column(Text())
    weight: Mapped[float] = mapped_column(Float(), default=1.0)
    submitted_by: Mapped[str] = mapped_column(String(128))
    submitted_at: Mapped[str] = mapped_column(String(64))


class ChainAnchorModel(Base):
    __tablename__ = "chain_anchors"

    anchor_id: Mapped[str] = mapped_column(String(64), primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), index=True)
    debate_id: Mapped[str] = mapped_column(String(64), index=True)
    report_hash: Mapped[str] = mapped_column(String(128), index=True)
    tx_hash: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    provider: Mapped[str] = mapped_column(String(64))
    network: Mapped[str] = mapped_column(String(64))
    status: Mapped[str] = mapped_column(String(32), default="submitted", index=True)
    submitted_by: Mapped[str] = mapped_column(String(128))
    created_at: Mapped[str] = mapped_column(String(64))
    updated_at: Mapped[str] = mapped_column(String(64))

