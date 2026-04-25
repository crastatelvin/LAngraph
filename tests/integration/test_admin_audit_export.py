from pathlib import Path
import sys

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.main import app

HEADERS = {
    "X-Tenant-Id": "tenant-audit-export-001",
    "X-User-Id": "admin-audit-1",
    "X-User-Role": "admin",
    "X-Request-Id": "req-audit-export-001",
}
MEMBER_HEADERS = {
    "X-Tenant-Id": "tenant-audit-export-001",
    "X-User-Id": "member-audit-1",
    "X-User-Role": "member",
    "X-Request-Id": "req-audit-export-002",
}


def test_admin_audit_export_json_and_csv() -> None:
    with TestClient(app) as client:
        created = client.post(
            "/v1/debates",
            json={"proposal": "Audit export verification proposal"},
            headers=HEADERS,
        )
        assert created.status_code == 200

        json_resp = client.get(
            "/v1/admin/audit/export?format=json&since_hours=24&action_prefix=debate.",
            headers=HEADERS,
        )
        assert json_resp.status_code == 200
        payload = json_resp.json()
        assert payload["count"] >= 1
        assert any(item["action"].startswith("debate.") for item in payload["events"])

        csv_resp = client.get(
            "/v1/admin/audit/export?format=csv&since_hours=24&action_prefix=debate.",
            headers=HEADERS,
        )
        assert csv_resp.status_code == 200
        assert "text/csv" in csv_resp.headers["content-type"]
        assert "attachment; filename=audit_export.csv" == csv_resp.headers["content-disposition"]
        assert "timestamp,tenant_id,actor_id,action,resource,payload_json" in csv_resp.text
        assert "debate.create" in csv_resp.text


def test_admin_audit_export_requires_admin() -> None:
    with TestClient(app) as client:
        denied = client.get("/v1/admin/audit/export?format=json", headers=MEMBER_HEADERS)
        assert denied.status_code == 403


def test_admin_audit_export_invalid_format() -> None:
    with TestClient(app) as client:
        bad = client.get("/v1/admin/audit/export?format=xml", headers=HEADERS)
        assert bad.status_code == 400
