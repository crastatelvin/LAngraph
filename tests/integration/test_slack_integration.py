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
        api_main.slack_integration._seen_event_ids.clear()
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
