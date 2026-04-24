from pathlib import Path
import sys

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import apps.api.main as api_main
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


def test_admin_health_dependencies_requires_admin() -> None:
    with TestClient(app) as client:
        response = client.get("/v1/admin/health/dependencies", headers=MEMBER_HEADERS)
        assert response.status_code == 403


def test_admin_health_dependencies_shape() -> None:
    with TestClient(app) as client:
        old_flag = api_main.os.getenv("ENABLE_SLACK_INTEGRATION")
        old_token = api_main.os.getenv("SLACK_BOT_TOKEN")
        api_main.os.environ["ENABLE_SLACK_INTEGRATION"] = "true"
        api_main.os.environ["SLACK_BOT_TOKEN"] = "xoxb-test"
        try:
            response = client.get("/v1/admin/health/dependencies", headers=HEADERS)
            assert response.status_code == 200
            payload = response.json()
            assert payload["database"]["status"] == "ok"
            assert "slack" in payload
            assert "worker_queue" in payload
        finally:
            if old_flag is None:
                api_main.os.environ.pop("ENABLE_SLACK_INTEGRATION", None)
            else:
                api_main.os.environ["ENABLE_SLACK_INTEGRATION"] = old_flag
            if old_token is None:
                api_main.os.environ.pop("SLACK_BOT_TOKEN", None)
            else:
                api_main.os.environ["SLACK_BOT_TOKEN"] = old_token
