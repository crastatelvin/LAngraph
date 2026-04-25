from pathlib import Path
import sys

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import apps.api.main as api_main
from apps.api.main import app
from apps.api.db import Base, SessionLocal, engine
from apps.api.models import ApiKeyModel

HEADERS = {
    "X-Tenant-Id": "tenant-admin-keys-001",
    "X-User-Id": "admin-keys-1",
    "X-User-Role": "admin",
    "X-Request-Id": "req-admin-keys-001",
}
MEMBER_HEADERS = {
    "X-Tenant-Id": "tenant-admin-keys-001",
    "X-User-Id": "member-keys-1",
    "X-User-Role": "member",
    "X-Request-Id": "req-admin-keys-002",
}


def _reset_api_keys_table() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.query(ApiKeyModel).delete()
    db.commit()
    db.close()


def test_admin_policy_endpoint() -> None:
    old_defaults = api_main.os.getenv("PLAN_LIMIT_DEFAULTS_JSON")
    old_overrides = api_main.os.getenv("PLAN_LIMIT_OVERRIDES_JSON")
    api_main.os.environ["PLAN_LIMIT_DEFAULTS_JSON"] = (
        '{"plan":"pro","limits":{"debate_create_per_day":100,"agent_outcome_ingest_per_day":100,"chain_anchor_requests_per_day":100}}'
    )
    api_main.os.environ["PLAN_LIMIT_OVERRIDES_JSON"] = (
        '{"tenant-admin-keys-001":{"plan":"enterprise","limits":{"debate_create_per_day":5000}}}'
    )
    try:
        with TestClient(app) as client:
            response = client.get("/v1/admin/policy", headers=HEADERS)
            assert response.status_code == 200
            payload = response.json()
            assert payload["plan"] == "enterprise"
            assert payload["limits"]["debate_create_per_day"] == 5000
    finally:
        if old_defaults is None:
            api_main.os.environ.pop("PLAN_LIMIT_DEFAULTS_JSON", None)
        else:
            api_main.os.environ["PLAN_LIMIT_DEFAULTS_JSON"] = old_defaults
        if old_overrides is None:
            api_main.os.environ.pop("PLAN_LIMIT_OVERRIDES_JSON", None)
        else:
            api_main.os.environ["PLAN_LIMIT_OVERRIDES_JSON"] = old_overrides


def test_admin_api_keys_create_list_revoke() -> None:
    _reset_api_keys_table()
    with TestClient(app) as client:
        created = client.post(
            "/v1/admin/api-keys",
            json={"name": "Primary Admin Key", "scopes": ["read:debates", "write:debates"]},
            headers=HEADERS,
        )
        assert created.status_code == 200
        created_payload = created.json()
        assert created_payload["raw_key"].startswith("apk_")
        key_id = created_payload["key"]["key_id"]

        listed = client.get("/v1/admin/api-keys", headers=HEADERS)
        assert listed.status_code == 200
        keys = listed.json()["keys"]
        assert any(item["key_id"] == key_id and item["status"] == "active" for item in keys)

        revoked = client.post(f"/v1/admin/api-keys/{key_id}/revoke", headers=HEADERS)
        assert revoked.status_code == 200
        assert revoked.json()["status"] == "revoked"

        listed_after = client.get("/v1/admin/api-keys", headers=HEADERS)
        assert listed_after.status_code == 200
        keys_after = listed_after.json()["keys"]
        assert any(item["key_id"] == key_id and item["status"] == "revoked" for item in keys_after)


def test_admin_api_keys_require_admin() -> None:
    _reset_api_keys_table()
    with TestClient(app) as client:
        denied_policy = client.get("/v1/admin/policy", headers=MEMBER_HEADERS)
        assert denied_policy.status_code == 403
        denied_list = client.get("/v1/admin/api-keys", headers=MEMBER_HEADERS)
        assert denied_list.status_code == 403
