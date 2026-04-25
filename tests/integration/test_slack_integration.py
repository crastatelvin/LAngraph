from pathlib import Path
import hashlib
import hmac
import json
import sys
import time
from urllib.parse import quote_plus

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import apps.api.main as api_main
from apps.api.main import app
from apps.api.db import SessionLocal
from apps.api.models import (
    FederationModel,
    FederationSessionModel,
    FederationSessionSubmissionModel,
    SlackInboundEventModel,
    SlackOutboundMessageModel,
    SlackSentDedupeModel,
)


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
            blocks = response.json().get("blocks", [])
            action_ids = [item["action_id"] for block in blocks for item in block.get("elements", []) if "action_id" in item]
            assert "debate_approve" in action_ids
            assert "debate_reject" in action_ids
            status_headers = {
                "X-Tenant-Id": "slack-T123",
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
                db=db,
                tenant_id="tenant-int-001",
                channel="C999",
                text="Hello thread",
                dedupe_key="d1",
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
                db=db,
                tenant_id="tenant-int-001",
                channel="C999",
                text="Hello thread",
                dedupe_key="d1",
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


def test_slack_interaction_approves_and_rejects_debate() -> None:
    with TestClient(app) as client:
        old_flag = api_main.os.getenv("ENABLE_SLACK_INTEGRATION")
        old_secret = api_main.os.getenv("SLACK_SIGNING_SECRET")
        api_main.os.environ["ENABLE_SLACK_INTEGRATION"] = "true"
        api_main.os.environ["SLACK_SIGNING_SECRET"] = "test-secret"
        try:
            command_body = "command=/debate&text=Interactive+approval+flow&team_id=T999&user_id=U999&channel_id=C999"
            command_ts = str(int(time.time()))
            command_sig = _sign("test-secret", command_body, command_ts)
            command_headers = {
                "X-Slack-Signature": command_sig,
                "X-Slack-Request-Timestamp": command_ts,
                "Content-Type": "application/x-www-form-urlencoded",
            }
            command_resp = client.post("/v1/integrations/slack/commands", content=command_body, headers=command_headers)
            assert command_resp.status_code == 200
            created_text = command_resp.json()["text"]
            debate_id = created_text.split("Debate created: ")[1].split(" for proposal")[0]

            approve_payload = {
                "type": "block_actions",
                "team": {"id": "T999"},
                "user": {"id": "U999"},
                "actions": [{"action_id": "debate_approve", "value": debate_id}],
            }
            approve_payload_str = json.dumps(approve_payload)
            approve_body = f"payload={quote_plus(approve_payload_str)}"
            approve_ts = str(int(time.time()))
            approve_sig = _sign("test-secret", approve_body, approve_ts)
            interaction_headers = {
                "X-Slack-Signature": approve_sig,
                "X-Slack-Request-Timestamp": approve_ts,
                "Content-Type": "application/x-www-form-urlencoded",
            }
            approve_resp = client.post(
                "/v1/integrations/slack/interactions",
                content=approve_body,
                headers=interaction_headers,
            )
            assert approve_resp.status_code == 200
            assert "approved" in approve_resp.json()["text"]

            get_headers = {
                "X-Tenant-Id": "slack-T999",
                "X-User-Id": "owner-1",
                "X-User-Role": "owner",
                "X-Request-Id": "req-slack-int-1",
            }
            debate_after_approve = client.get(f"/v1/debates/{debate_id}", headers=get_headers)
            assert debate_after_approve.status_code == 200
            assert debate_after_approve.json()["status"] == "approved"

            reject_payload = {
                "type": "block_actions",
                "team": {"id": "T999"},
                "user": {"id": "U999"},
                "actions": [{"action_id": "debate_reject", "value": debate_id}],
            }
            reject_payload_str = json.dumps(reject_payload)
            reject_body = f"payload={quote_plus(reject_payload_str)}"
            reject_ts = str(int(time.time()))
            reject_sig = _sign("test-secret", reject_body, reject_ts)
            reject_headers = {
                "X-Slack-Signature": reject_sig,
                "X-Slack-Request-Timestamp": reject_ts,
                "Content-Type": "application/x-www-form-urlencoded",
            }
            reject_resp = client.post(
                "/v1/integrations/slack/interactions",
                content=reject_body,
                headers=reject_headers,
            )
            assert reject_resp.status_code == 200
            assert "rejected" in reject_resp.json()["text"]

            debate_after_reject = client.get(f"/v1/debates/{debate_id}", headers=get_headers)
            assert debate_after_reject.status_code == 200
            assert debate_after_reject.json()["status"] == "rejected"
        finally:
            if old_flag is None:
                api_main.os.environ.pop("ENABLE_SLACK_INTEGRATION", None)
            else:
                api_main.os.environ["ENABLE_SLACK_INTEGRATION"] = old_flag
            if old_secret is None:
                api_main.os.environ.pop("SLACK_SIGNING_SECRET", None)
            else:
                api_main.os.environ["SLACK_SIGNING_SECRET"] = old_secret


def test_slack_federation_command_and_interaction_submission() -> None:
    with TestClient(app) as client:
        old_flag = api_main.os.getenv("ENABLE_SLACK_INTEGRATION")
        old_secret = api_main.os.getenv("SLACK_SIGNING_SECRET")
        api_main.os.environ["ENABLE_SLACK_INTEGRATION"] = "true"
        api_main.os.environ["SLACK_SIGNING_SECRET"] = "test-secret"
        try:
            db = SessionLocal()
            db.query(FederationSessionSubmissionModel).delete()
            db.query(FederationSessionModel).delete()
            db.query(FederationModel).delete()
            db.commit()
            federation = FederationModel(
                federation_id="fed-slack-1",
                tenant_id="slack-T321",
                name="Slack Federation",
                status="active",
                created_by="seed",
                created_at="2026-01-01T00:00:00+00:00",
            )
            db.add(federation)
            db.commit()
            db.close()

            command_body = "command=/federation&text=create-session+fed-slack-1&team_id=T321&user_id=U321&channel_id=C321"
            command_ts = str(int(time.time()))
            command_sig = _sign("test-secret", command_body, command_ts)
            command_headers = {
                "X-Slack-Signature": command_sig,
                "X-Slack-Request-Timestamp": command_ts,
                "Content-Type": "application/x-www-form-urlencoded",
            }
            command_resp = client.post("/v1/integrations/slack/commands", content=command_body, headers=command_headers)
            assert command_resp.status_code == 200
            assert "Federation session created:" in command_resp.json()["text"]
            session_id = command_resp.json()["text"].split("Federation session created: ")[1]

            interaction_payload = {
                "type": "block_actions",
                "team": {"id": "T321"},
                "user": {"id": "U321"},
                "actions": [{"action_id": "federation_join_approved", "value": session_id}],
            }
            interaction_payload_str = json.dumps(interaction_payload)
            interaction_body = f"payload={quote_plus(interaction_payload_str)}"
            interaction_ts = str(int(time.time()))
            interaction_sig = _sign("test-secret", interaction_body, interaction_ts)
            interaction_headers = {
                "X-Slack-Signature": interaction_sig,
                "X-Slack-Request-Timestamp": interaction_ts,
                "Content-Type": "application/x-www-form-urlencoded",
            }
            interaction_resp = client.post(
                "/v1/integrations/slack/interactions",
                content=interaction_body,
                headers=interaction_headers,
            )
            assert interaction_resp.status_code == 200
            assert "recorded `APPROVED`" in interaction_resp.json()["text"]

            db = SessionLocal()
            submission = (
                db.query(FederationSessionSubmissionModel)
                .filter(
                    FederationSessionSubmissionModel.session_id == session_id,
                    FederationSessionSubmissionModel.tenant_id == "slack-T321",
                )
                .first()
            )
            db.close()
            assert submission is not None
            assert submission.position == "APPROVED"
        finally:
            if old_flag is None:
                api_main.os.environ.pop("ENABLE_SLACK_INTEGRATION", None)
            else:
                api_main.os.environ["ENABLE_SLACK_INTEGRATION"] = old_flag
            if old_secret is None:
                api_main.os.environ.pop("SLACK_SIGNING_SECRET", None)
            else:
                api_main.os.environ["SLACK_SIGNING_SECRET"] = old_secret


def test_slack_federation_decision_command_returns_snapshot() -> None:
    with TestClient(app) as client:
        old_flag = api_main.os.getenv("ENABLE_SLACK_INTEGRATION")
        old_secret = api_main.os.getenv("SLACK_SIGNING_SECRET")
        api_main.os.environ["ENABLE_SLACK_INTEGRATION"] = "true"
        api_main.os.environ["SLACK_SIGNING_SECRET"] = "test-secret"
        try:
            db = SessionLocal()
            db.query(FederationSessionSubmissionModel).delete()
            db.query(FederationSessionModel).delete()
            db.query(FederationModel).delete()
            db.commit()
            federation = FederationModel(
                federation_id="fed-slack-2",
                tenant_id="slack-T654",
                name="Decision Federation",
                status="active",
                created_by="seed",
                created_at="2026-01-01T00:00:00+00:00",
            )
            session = FederationSessionModel(
                session_id="sess-slack-2",
                federation_id="fed-slack-2",
                tenant_id="slack-T654",
                status="open",
                created_by="seed",
                created_at="2026-01-01T00:00:00+00:00",
            )
            db.add(federation)
            db.add(session)
            db.add(
                FederationSessionSubmissionModel(
                    session_id="sess-slack-2",
                    tenant_id="slack-T654",
                    parliament_name="Platform",
                    position="APPROVED",
                    confidence=0.8,
                    summary="Ready to proceed",
                    weight=1.0,
                    submitted_by="seed",
                    submitted_at="2026-01-01T00:00:00+00:00",
                )
            )
            db.commit()
            db.close()

            command_body = "command=/federation&text=decision+sess-slack-2&team_id=T654&user_id=U654&channel_id=C654"
            command_ts = str(int(time.time()))
            command_sig = _sign("test-secret", command_body, command_ts)
            command_headers = {
                "X-Slack-Signature": command_sig,
                "X-Slack-Request-Timestamp": command_ts,
                "Content-Type": "application/x-www-form-urlencoded",
            }
            command_resp = client.post("/v1/integrations/slack/commands", content=command_body, headers=command_headers)
            assert command_resp.status_code == 200
            assert "decision: APPROVED" in command_resp.json()["text"]
            assert "submissions=1" in command_resp.json()["text"]
        finally:
            if old_flag is None:
                api_main.os.environ.pop("ENABLE_SLACK_INTEGRATION", None)
            else:
                api_main.os.environ["ENABLE_SLACK_INTEGRATION"] = old_flag
            if old_secret is None:
                api_main.os.environ.pop("SLACK_SIGNING_SECRET", None)
            else:
                api_main.os.environ["SLACK_SIGNING_SECRET"] = old_secret


def test_slack_federation_submissions_command_returns_compact_list() -> None:
    with TestClient(app) as client:
        old_flag = api_main.os.getenv("ENABLE_SLACK_INTEGRATION")
        old_secret = api_main.os.getenv("SLACK_SIGNING_SECRET")
        api_main.os.environ["ENABLE_SLACK_INTEGRATION"] = "true"
        api_main.os.environ["SLACK_SIGNING_SECRET"] = "test-secret"
        try:
            db = SessionLocal()
            db.query(FederationSessionSubmissionModel).delete()
            db.query(FederationSessionModel).delete()
            db.query(FederationModel).delete()
            db.commit()
            federation = FederationModel(
                federation_id="fed-slack-3",
                tenant_id="slack-T777",
                name="Submission Federation",
                status="active",
                created_by="seed",
                created_at="2026-01-01T00:00:00+00:00",
            )
            session = FederationSessionModel(
                session_id="sess-slack-3",
                federation_id="fed-slack-3",
                tenant_id="slack-T777",
                status="open",
                created_by="seed",
                created_at="2026-01-01T00:00:00+00:00",
            )
            db.add(federation)
            db.add(session)
            db.add(
                FederationSessionSubmissionModel(
                    session_id="sess-slack-3",
                    tenant_id="slack-T777",
                    parliament_name="Platform",
                    position="APPROVED",
                    confidence=0.82,
                    summary="Ready",
                    weight=1.1,
                    submitted_by="seed",
                    submitted_at="2026-01-01T00:00:00+00:00",
                )
            )
            db.add(
                FederationSessionSubmissionModel(
                    session_id="sess-slack-3",
                    tenant_id="slack-T777",
                    parliament_name="Security",
                    position="INCONCLUSIVE",
                    confidence=0.51,
                    summary="Need more evidence",
                    weight=1.0,
                    submitted_by="seed",
                    submitted_at="2026-01-01T00:00:00+00:00",
                )
            )
            db.commit()
            db.close()

            command_body = "command=/federation&text=submissions+sess-slack-3&team_id=T777&user_id=U777&channel_id=C777"
            command_ts = str(int(time.time()))
            command_sig = _sign("test-secret", command_body, command_ts)
            command_headers = {
                "X-Slack-Signature": command_sig,
                "X-Slack-Request-Timestamp": command_ts,
                "Content-Type": "application/x-www-form-urlencoded",
            }
            command_resp = client.post("/v1/integrations/slack/commands", content=command_body, headers=command_headers)
            assert command_resp.status_code == 200
            message = command_resp.json()["text"]
            assert "submissions (2)" in message
            assert "Platform: APPROVED" in message
            assert "Security: INCONCLUSIVE" in message
        finally:
            if old_flag is None:
                api_main.os.environ.pop("ENABLE_SLACK_INTEGRATION", None)
            else:
                api_main.os.environ["ENABLE_SLACK_INTEGRATION"] = old_flag
            if old_secret is None:
                api_main.os.environ.pop("SLACK_SIGNING_SECRET", None)
            else:
                api_main.os.environ["SLACK_SIGNING_SECRET"] = old_secret
