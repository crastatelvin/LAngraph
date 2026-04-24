import hashlib
import hmac
import json
import os
import time
from datetime import datetime, UTC
from urllib import error, request
from urllib.parse import parse_qs

from sqlalchemy.orm import Session

from apps.api.models import SlackInboundEventModel, SlackOutboundMessageModel, SlackSentDedupeModel


class SlackIntegration:
    def __init__(self) -> None:
        pass

    def enabled(self) -> bool:
        return os.getenv("ENABLE_SLACK_INTEGRATION", "false").lower() == "true"

    def verify_signature(self, timestamp: str | None, signature: str | None, body: bytes) -> bool:
        secret = os.getenv("SLACK_SIGNING_SECRET", "")
        if not secret or not timestamp or not signature:
            return False

        # Reject stale requests to limit replay attacks.
        now = int(time.time())
        if abs(now - int(timestamp)) > 60 * 5:
            return False

        base = f"v0:{timestamp}:{body.decode('utf-8')}"
        digest = hmac.new(secret.encode("utf-8"), base.encode("utf-8"), hashlib.sha256).hexdigest()
        expected = f"v0={digest}"
        return hmac.compare_digest(expected, signature)

    def is_duplicate(self, db: Session, event_id: str | None) -> bool:
        if not event_id:
            return False
        exists = db.query(SlackInboundEventModel).filter(SlackInboundEventModel.event_id == event_id).first()
        if exists is not None:
            return True
        db.add(SlackInboundEventModel(event_id=event_id, seen_at=datetime.now(UTC).isoformat()))
        db.commit()
        return False

    def parse_body(self, body: bytes) -> dict:
        return json.loads(body.decode("utf-8"))

    def parse_form_body(self, body: bytes) -> dict[str, str]:
        parsed = parse_qs(body.decode("utf-8"), keep_blank_values=True)
        return {key: values[0] for key, values in parsed.items()}

    def queue_thread_message(
        self,
        db: Session,
        channel: str,
        text: str,
        thread_ts: str | None = None,
        dedupe_key: str | None = None,
    ) -> bool:
        if dedupe_key:
            sent = db.query(SlackSentDedupeModel).filter(SlackSentDedupeModel.dedupe_key == dedupe_key).first()
            queued = (
                db.query(SlackOutboundMessageModel)
                .filter(
                    SlackOutboundMessageModel.dedupe_key == dedupe_key,
                    SlackOutboundMessageModel.status.in_(["queued", "retry"]),
                )
                .first()
            )
            if sent is not None or queued is not None:
                return False

        db.add(
            SlackOutboundMessageModel(
                channel=channel,
                text=text,
                thread_ts=thread_ts,
                dedupe_key=dedupe_key,
                attempts=0,
                status="queued",
                created_at=datetime.now(UTC).isoformat(),
            )
        )
        db.commit()
        return True

    def outbound_status(self, db: Session) -> dict:
        queued = (
            db.query(SlackOutboundMessageModel)
            .filter(SlackOutboundMessageModel.status.in_(["queued", "retry"]))
            .count()
        )
        sent = db.query(SlackSentDedupeModel).count()
        return {"queued": queued, "sent_dedupes": sent}

    def flush_outbound_queue(self, db: Session, max_items: int = 20) -> dict:
        if not self.enabled():
            return {"processed": 0, "sent": 0, "failed": 0, "detail": "integration_disabled"}
        token = os.getenv("SLACK_BOT_TOKEN", "")
        if not token:
            return {"processed": 0, "sent": 0, "failed": 0, "detail": "missing_slack_bot_token"}

        items = (
            db.query(SlackOutboundMessageModel)
            .filter(SlackOutboundMessageModel.status.in_(["queued", "retry"]))
            .order_by(SlackOutboundMessageModel.id.asc())
            .limit(max_items)
            .all()
        )
        processed = 0
        sent = 0
        failed = 0

        for item in items:
            processed += 1
            item.attempts += 1
            ok = self._send_chat_post_message(
                token=token,
                channel=item.channel,
                text=item.text,
                thread_ts=item.thread_ts,
            )
            if ok:
                item.status = "sent"
                sent += 1
                if item.dedupe_key:
                    existing = (
                        db.query(SlackSentDedupeModel)
                        .filter(SlackSentDedupeModel.dedupe_key == item.dedupe_key)
                        .first()
                    )
                    if existing is None:
                        db.add(
                            SlackSentDedupeModel(
                                dedupe_key=item.dedupe_key, sent_at=datetime.now(UTC).isoformat()
                            )
                        )
            else:
                failed += 1
                item.status = "retry" if item.attempts < 3 else "failed"
        db.commit()
        remaining = (
            db.query(SlackOutboundMessageModel)
            .filter(SlackOutboundMessageModel.status.in_(["queued", "retry"]))
            .count()
        )
        return {"processed": processed, "sent": sent, "failed": failed, "remaining": remaining}

    def cleanup_old_state(self, db: Session, retention_hours: int = 24) -> dict:
        cutoff_iso = datetime.now(UTC).isoformat()
        # Convert to deterministic cutoff using unix timestamp arithmetic.
        cutoff_ts = time.time() - (retention_hours * 3600)
        cutoff_iso = datetime.fromtimestamp(cutoff_ts, UTC).isoformat()

        inbound_deleted = (
            db.query(SlackInboundEventModel)
            .filter(SlackInboundEventModel.seen_at < cutoff_iso)
            .delete(synchronize_session=False)
        )
        dedupe_deleted = (
            db.query(SlackSentDedupeModel)
            .filter(SlackSentDedupeModel.sent_at < cutoff_iso)
            .delete(synchronize_session=False)
        )
        failed_deleted = (
            db.query(SlackOutboundMessageModel)
            .filter(
                SlackOutboundMessageModel.status == "failed",
                SlackOutboundMessageModel.created_at < cutoff_iso,
            )
            .delete(synchronize_session=False)
        )
        db.commit()
        return {
            "retention_hours": retention_hours,
            "deleted_inbound_events": inbound_deleted,
            "deleted_sent_dedupes": dedupe_deleted,
            "deleted_failed_messages": failed_deleted,
        }

    def _send_chat_post_message(
        self, token: str, channel: str, text: str, thread_ts: str | None = None
    ) -> bool:
        payload = {"channel": channel, "text": text}
        if thread_ts:
            payload["thread_ts"] = thread_ts
        req = request.Request(
            "https://slack.com/api/chat.postMessage",
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json; charset=utf-8",
            },
            method="POST",
        )
        try:
            with request.urlopen(req, timeout=5) as resp:
                body = resp.read().decode("utf-8")
                result = json.loads(body)
                return bool(result.get("ok"))
        except (error.URLError, TimeoutError, json.JSONDecodeError):
            return False
