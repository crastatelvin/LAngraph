import hashlib
import hmac
import json
import os
import time
from urllib import error, request
from urllib.parse import parse_qs


class SlackIntegration:
    def __init__(self) -> None:
        self._seen_event_ids: dict[str, float] = {}
        self._outbound_queue: list[dict] = []
        self._sent_dedupe_keys: set[str] = set()

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

    def is_duplicate(self, event_id: str | None) -> bool:
        if not event_id:
            return False
        now = time.time()
        self._seen_event_ids = {
            key: seen_at for key, seen_at in self._seen_event_ids.items() if now - seen_at < 3600
        }
        if event_id in self._seen_event_ids:
            return True
        self._seen_event_ids[event_id] = now
        return False

    def parse_body(self, body: bytes) -> dict:
        return json.loads(body.decode("utf-8"))

    def parse_form_body(self, body: bytes) -> dict[str, str]:
        parsed = parse_qs(body.decode("utf-8"), keep_blank_values=True)
        return {key: values[0] for key, values in parsed.items()}

    def queue_thread_message(
        self, channel: str, text: str, thread_ts: str | None = None, dedupe_key: str | None = None
    ) -> bool:
        if dedupe_key and dedupe_key in self._sent_dedupe_keys:
            return False
        if dedupe_key and any(item.get("dedupe_key") == dedupe_key for item in self._outbound_queue):
            return False
        self._outbound_queue.append(
            {
                "channel": channel,
                "text": text,
                "thread_ts": thread_ts,
                "dedupe_key": dedupe_key,
                "attempts": 0,
            }
        )
        return True

    def outbound_status(self) -> dict:
        return {"queued": len(self._outbound_queue), "sent_dedupes": len(self._sent_dedupe_keys)}

    def flush_outbound_queue(self, max_items: int = 20) -> dict:
        if not self.enabled():
            return {"processed": 0, "sent": 0, "failed": 0, "detail": "integration_disabled"}
        token = os.getenv("SLACK_BOT_TOKEN", "")
        if not token:
            return {"processed": 0, "sent": 0, "failed": 0, "detail": "missing_slack_bot_token"}

        processed = 0
        sent = 0
        failed = 0
        remaining: list[dict] = []

        for item in self._outbound_queue:
            if processed >= max_items:
                remaining.append(item)
                continue
            processed += 1
            item["attempts"] += 1
            ok = self._send_chat_post_message(
                token=token,
                channel=item["channel"],
                text=item["text"],
                thread_ts=item["thread_ts"],
            )
            if ok:
                sent += 1
                if item.get("dedupe_key"):
                    self._sent_dedupe_keys.add(item["dedupe_key"])
            else:
                failed += 1
                if item["attempts"] < 3:
                    remaining.append(item)

        self._outbound_queue = remaining
        return {"processed": processed, "sent": sent, "failed": failed, "remaining": len(remaining)}

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
