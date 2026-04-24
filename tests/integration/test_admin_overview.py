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
OWNER_HEADERS = {
    "X-Tenant-Id": "tenant-int-001",
    "X-User-Id": "owner-1",
    "X-User-Role": "owner",
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


def test_admin_overview_compact_shape() -> None:
    with TestClient(app) as client:
        response = client.get("/v1/admin/overview?compact=true", headers=HEADERS)
        assert response.status_code == 200
        payload = response.json()
        assert payload["scope"]["effective_tenant_id"] == "tenant-int-001"
        assert payload["scope"]["queue_scope"] == "tenant"
        assert "workflow_total_runs" in payload["metrics"]
        assert "workflow" not in payload["metrics"]


def test_admin_overview_cross_tenant_requires_owner() -> None:
    with TestClient(app) as client:
        forbidden = client.get("/v1/admin/overview?tenant_id=tenant-int-999", headers=HEADERS)
        assert forbidden.status_code == 403

        allowed = client.get("/v1/admin/overview?tenant_id=tenant-int-999", headers=OWNER_HEADERS)
        assert allowed.status_code == 200
        payload = allowed.json()
        assert payload["scope"]["requested_tenant_id"] == "tenant-int-999"
        assert payload["scope"]["effective_tenant_id"] == "tenant-int-999"
