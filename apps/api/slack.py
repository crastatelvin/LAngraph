import hashlib
import hmac
import json
import os
import time


class SlackIntegration:
    def __init__(self) -> None:
        self._seen_event_ids: dict[str, float] = {}

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
