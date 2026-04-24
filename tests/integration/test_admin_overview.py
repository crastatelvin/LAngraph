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


def test_admin_overview_requires_admin() -> None:
    with TestClient(app) as client:
        response = client.get("/v1/admin/overview", headers=MEMBER_HEADERS)
        assert response.status_code == 403


def test_admin_overview_shape() -> None:
    with TestClient(app) as client:
        response = client.get("/v1/admin/overview", headers=HEADERS)
        assert response.status_code == 200
        payload = response.json()
        assert "health" in payload
        assert "slo" in payload
        assert "metrics" in payload
        assert "workflow" in payload["metrics"]
        assert "endpoints" in payload["metrics"]
