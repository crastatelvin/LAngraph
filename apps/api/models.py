from sqlalchemy import Integer, String, Text
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

