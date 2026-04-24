from pathlib import Path
import hashlib
import hmac
import json
import sys
import time

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import apps.api.main as api_main
from apps.api.main import app
from apps.api.db import SessionLocal
from apps.api.models import SlackInboundEventModel, SlackOutboundMessageModel, SlackSentDedupeModel


def _sign(secret: str, body: str, timestamp: str) -> str:
    base = f"v0:{timestamp}:{body}"
    digest = hmac.new(secret.encode("utf-8"), base.encode("utf-8"), hashlib.sha256).hexdigest()
    return f"v0={digest}"


def test_slack_endpoint_disabled_by_default() -> None:
    with TestClient(app) as client:
        response = client.post("/v1/integrations/slack/events", json={"foo": "bar"})
        assert response.status_code == 503


def test_slack_signature_and_challenge_flow() -> None:
    with TestClient(app) as client:
        old_flag = api_main.os.getenv("ENABLE_SLACK_INTEGRATION")
        old_secret = api_main.os.getenv("SLACK_SIGNING_SECRET")
        api_main.os.environ["ENABLE_SLACK_INTEGRATION"] = "true"
        api_main.os.environ["SLACK_SIGNING_SECRET"] = "test-secret"
        try:
            payload = {"challenge": "abc123"}
            body = json.dumps(payload)
            ts = str(int(time.time()))
            sig = _sign("test-secret", body, ts)
            headers = {"X-Slack-Signature": sig, "X-Slack-Request-Timestamp": ts}
            response = client.post("/v1/integrations/slack/events", content=body, headers=headers)
            assert response.status_code == 200
            assert response.json()["challenge"] == "abc123"
        finally:
            if old_flag is None:
                api_main.os.environ.pop("ENABLE_SLACK_INTEGRATION", None)
            else:
                api_main.os.environ["ENABLE_SLACK_INTEGRATION"] = old_flag
            if old_secret is None:
                api_main.os.environ.pop("SLACK_SIGNING_SECRET", None)
            else:
                api_main.os.environ["SLACK_SIGNING_SECRET"] = old_secret


def test_slack_idempotency_duplicate_ignored() -> None:
    with TestClient(app) as client:
        old_flag = api_main.os.getenv("ENABLE_SLACK_INTEGRATION")
        old_secret = api_main.os.getenv("SLACK_SIGNING_SECRET")
        api_main.os.environ["ENABLE_SLACK_INTEGRATION"] = "true"
        api_main.os.environ["SLACK_SIGNING_SECRET"] = "test-secret"
        db = SessionLocal()
        db.query(SlackInboundEventModel).delete()
        db.commit()
        db.close()
        try:
            payload = {"event_id": "evt-1", "event": {"type": "message"}}
            body = json.dumps(payload)
            ts = str(int(time.time()))
            sig = _sign("test-secret", body, ts)
            headers = {"X-Slack-Signature": sig, "X-Slack-Request-Timestamp": ts}
            first = client.post("/v1/integrations/slack/events", content=body, headers=headers)
            second = client.post("/v1/integrations/slack/events", content=body, headers=headers)
            assert first.status_code == 200
            assert first.json()["status"] == "accepted"
            assert second.status_code == 200
            assert second.json()["status"] == "duplicate_ignored"
        finally:
            if old_flag is None:
                api_main.os.environ.pop("ENABLE_SLACK_INTEGRATION", None)
            else:
                api_main.os.environ["ENABLE_SLACK_INTEGRATION"] = old_flag
            if old_secret is None:
                api_main.os.environ.pop("SLACK_SIGNING_SECRET", None)
            else:
                api_main.os.environ["SLACK_SIGNING_SECRET"] = old_secret


def test_slack_command_creates_debate() -> None:
    with TestClient(app) as client:
        old_flag = api_main.os.getenv("ENABLE_SLACK_INTEGRATION")
        old_secret = api_main.os.getenv("SLACK_SIGNING_SECRET")
        api_main.os.environ["ENABLE_SLACK_INTEGRATION"] = "true"
        api_main.os.environ["SLACK_SIGNING_SECRET"] = "test-secret"
        try:
            body = "command=/debate&text=Adopt+incident+review+cadence&team_id=T123&user_id=U123&channel_id=C123"
            ts = str(int(time.time()))
            sig = _sign("test-secret", body, ts)
            headers = {
                "X-Slack-Signature": sig,
                "X-Slack-Request-Timestamp": ts,
                "Content-Type": "application/x-www-form-urlencoded",
            }
            response = client.post("/v1/integrations/slack/commands", content=body, headers=headers)
            assert response.status_code == 200
            assert "Debate created:" in response.json()["text"]
            assert response.json()["response_type"] == "in_channel"
            status_headers = {
                "X-Tenant-Id": "tenant-int-001",
                "X-User-Id": "user-1",
                "X-User-Role": "admin",
            }
            status = client.get("/v1/integrations/slack/outbound/status", headers=status_headers)
            assert status.status_code == 200
            assert status.json()["queued"] >= 1
        finally:
            if old_flag is None:
                api_main.os.environ.pop("ENABLE_SLACK_INTEGRATION", None)
            else:
                api_main.os.environ["ENABLE_SLACK_INTEGRATION"] = old_flag
            if old_secret is None:
                api_main.os.environ.pop("SLACK_SIGNING_SECRET", None)
            else:
                api_main.os.environ["SLACK_SIGNING_SECRET"] = old_secret


def test_slack_command_usage_message_on_empty_text() -> None:
    with TestClient(app) as client:
        old_flag = api_main.os.getenv("ENABLE_SLACK_INTEGRATION")
        old_secret = api_main.os.getenv("SLACK_SIGNING_SECRET")
        api_main.os.environ["ENABLE_SLACK_INTEGRATION"] = "true"
        api_main.os.environ["SLACK_SIGNING_SECRET"] = "test-secret"
        try:
            body = "command=/debate&text=&team_id=T123&user_id=U123"
            ts = str(int(time.time()))
            sig = _sign("test-secret", body, ts)
            headers = {
                "X-Slack-Signature": sig,
                "X-Slack-Request-Timestamp": ts,
                "Content-Type": "application/x-www-form-urlencoded",
            }
            response = client.post("/v1/integrations/slack/commands", content=body, headers=headers)
            assert response.status_code == 200
            assert "Usage: /debate" in response.json()["text"]
            assert response.json()["response_type"] == "ephemeral"
        finally:
            if old_flag is None:
                api_main.os.environ.pop("ENABLE_SLACK_INTEGRATION", None)
            else:
                api_main.os.environ["ENABLE_SLACK_INTEGRATION"] = old_flag
            if old_secret is None:
                api_main.os.environ.pop("SLACK_SIGNING_SECRET", None)
            else:
                api_main.os.environ["SLACK_SIGNING_SECRET"] = old_secret


def test_slack_outbound_flush_retry_safe() -> None:
    with TestClient(app) as client:
        old_flag = api_main.os.getenv("ENABLE_SLACK_INTEGRATION")
        old_secret = api_main.os.getenv("SLACK_SIGNING_SECRET")
        old_token = api_main.os.getenv("SLACK_BOT_TOKEN")
        api_main.os.environ["ENABLE_SLACK_INTEGRATION"] = "true"
        api_main.os.environ["SLACK_SIGNING_SECRET"] = "test-secret"
        api_main.os.environ["SLACK_BOT_TOKEN"] = "xoxb-test"
        db = SessionLocal()
        db.query(SlackOutboundMessageModel).delete()
        db.query(SlackSentDedupeModel).delete()
        db.commit()
        db.close()
        sent_calls: list[tuple[str, str]] = []

        def fake_send(token: str, channel: str, text: str, thread_ts: str | None = None) -> bool:
            sent_calls.append((channel, text))
            return True

        original_sender = api_main.slack_integration._send_chat_post_message
        api_main.slack_integration._send_chat_post_message = fake_send
        try:
            db = SessionLocal()
            api_main.slack_integration.queue_thread_message(
                db=db, channel="C999", text="Hello thread", dedupe_key="d1"
            )
            db.close()
            status_headers = {
                "X-Tenant-Id": "tenant-int-001",
                "X-User-Id": "user-1",
                "X-User-Role": "admin",
            }
            flush = client.post("/v1/integrations/slack/outbound/flush", headers=status_headers)
            assert flush.status_code == 200
            assert flush.json()["sent"] == 1
            assert len(sent_calls) == 1

            # Deduped message should not enqueue again.
            db = SessionLocal()
            enqueued = api_main.slack_integration.queue_thread_message(
                db=db, channel="C999", text="Hello thread", dedupe_key="d1"
            )
            db.close()
            assert enqueued is False
        finally:
            api_main.slack_integration._send_chat_post_message = original_sender
            if old_flag is None:
                api_main.os.environ.pop("ENABLE_SLACK_INTEGRATION", None)
            else:
                api_main.os.environ["ENABLE_SLACK_INTEGRATION"] = old_flag
            if old_secret is None:
                api_main.os.environ.pop("SLACK_SIGNING_SECRET", None)
            else:
                api_main.os.environ["SLACK_SIGNING_SECRET"] = old_secret
            if old_token is None:
                api_main.os.environ.pop("SLACK_BOT_TOKEN", None)
            else:
                api_main.os.environ["SLACK_BOT_TOKEN"] = old_token
