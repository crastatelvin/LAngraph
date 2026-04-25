from pathlib import Path
import sys

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.main import app

ADMIN_TENANT_A = {
    "X-Tenant-Id": "tenant-sec-a",
    "X-User-Id": "admin-a",
    "X-User-Role": "admin",
    "X-Request-Id": "req-sec-a-001",
}
ADMIN_TENANT_B = {
    "X-Tenant-Id": "tenant-sec-b",
    "X-User-Id": "admin-b",
    "X-User-Role": "admin",
    "X-Request-Id": "req-sec-b-001",
}
MEMBER_TENANT_A = {
    "X-Tenant-Id": "tenant-sec-a",
    "X-User-Id": "member-a",
    "X-User-Role": "member",
    "X-Request-Id": "req-sec-a-002",
}


def test_tenant_isolation_blocks_cross_tenant_debate_read() -> None:
    with TestClient(app) as client:
        created = client.post(
            "/v1/debates",
            json={"proposal": "Tenant-isolated debate artifact"},
            headers=ADMIN_TENANT_A,
        )
        assert created.status_code == 200
        debate_id = created.json()["debate_id"]

        cross_read = client.get(f"/v1/debates/{debate_id}", headers=ADMIN_TENANT_B)
        assert cross_read.status_code == 404

        cross_events = client.get(f"/v1/debates/{debate_id}/events", headers=ADMIN_TENANT_B)
        assert cross_events.status_code == 404


def test_role_escalation_blocked_for_plan_and_key_admin_endpoints() -> None:
    with TestClient(app) as client:
        policy_denied = client.get("/v1/admin/policy", headers=MEMBER_TENANT_A)
        assert policy_denied.status_code == 403

        list_keys_denied = client.get("/v1/admin/api-keys", headers=MEMBER_TENANT_A)
        assert list_keys_denied.status_code == 403

        create_key_denied = client.post(
            "/v1/admin/api-keys",
            json={"name": "member-attempt", "scopes": ["read:debates"]},
            headers=MEMBER_TENANT_A,
        )
        assert create_key_denied.status_code == 403


def test_missing_auth_context_rejected_for_admin_endpoints() -> None:
    with TestClient(app) as client:
        no_headers_policy = client.get("/v1/admin/policy")
        assert no_headers_policy.status_code == 400

        no_headers_usage = client.get("/v1/admin/usage")
        assert no_headers_usage.status_code == 400

        no_headers_audit_export = client.get("/v1/admin/audit/export?format=json")
        assert no_headers_audit_export.status_code == 400
