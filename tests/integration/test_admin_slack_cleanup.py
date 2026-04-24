from pathlib import Path
import sys

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.main import app

HEADERS = {
    "X-Tenant-Id": "tenant-int-001",
    "X-User-Id": "user-1",
    "X-User-Role": "admin",
}
MEMBER_HEADERS = {
    "X-Tenant-Id": "tenant-int-001",
    "X-User-Id": "user-2",
    "X-User-Role": "member",
}


def test_admin_slack_cleanup_requires_admin() -> None:
    with TestClient(app) as client:
        forbidden = client.post("/v1/admin/slack/cleanup?retention_hours=24", headers=MEMBER_HEADERS)
        assert forbidden.status_code == 403


def test_admin_slack_cleanup_validates_range() -> None:
    with TestClient(app) as client:
        bad = client.post("/v1/admin/slack/cleanup?retention_hours=0", headers=HEADERS)
        assert bad.status_code == 400


def test_admin_slack_cleanup_success_shape() -> None:
    with TestClient(app) as client:
        ok = client.post("/v1/admin/slack/cleanup?retention_hours=24", headers=HEADERS)
        assert ok.status_code == 200
        body = ok.json()
        assert "deleted_inbound_events" in body
        assert "deleted_sent_dedupes" in body
        assert "deleted_failed_messages" in body
