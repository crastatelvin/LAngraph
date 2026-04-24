from pathlib import Path
import sys

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.main import app

HEADERS = {
    "X-Tenant-Id": "tenant-alpha",
    "X-User-Id": "user-1",
    "X-User-Role": "admin",
}
MEMBER_HEADERS = {
    "X-Tenant-Id": "tenant-alpha",
    "X-User-Id": "user-2",
    "X-User-Role": "member",
}


def test_debate_lifecycle() -> None:
    with TestClient(app) as client:
        create_resp = client.post(
            "/v1/debates",
            json={"proposal": "Adopt weekly async planning"},
            headers=HEADERS,
        )
        assert create_resp.status_code == 200
        created = create_resp.json()
        debate_id = created["debate_id"]
        assert created["status"] == "created"

        get_resp = client.get(f"/v1/debates/{debate_id}", headers=HEADERS)
        assert get_resp.status_code == 200
        assert get_resp.json()["proposal"] == "Adopt weekly async planning"

        events_resp = client.get(f"/v1/debates/{debate_id}/events", headers=HEADERS)
        assert events_resp.status_code == 200
        events = events_resp.json()["events"]
        assert len(events) >= 2
        assert events[0]["event_type"] == "debate_created"

        approve_resp = client.post(f"/v1/debates/{debate_id}/approve", headers=HEADERS)
        assert approve_resp.status_code == 200
        assert approve_resp.json()["status"] == "approved"

        events_after = client.get(f"/v1/debates/{debate_id}/events", headers=HEADERS).json()["events"]
        assert events_after[-1]["event_type"] == "human_approved"

        audit_resp = client.get("/v1/admin/audit", headers=HEADERS)
        assert audit_resp.status_code == 200
        assert len(audit_resp.json()) >= 4


def test_not_found_paths() -> None:
    with TestClient(app) as client:
        missing_id = "missing-debate"
        assert client.get(f"/v1/debates/{missing_id}", headers=HEADERS).status_code == 404
        assert client.get(f"/v1/debates/{missing_id}/events", headers=HEADERS).status_code == 404
        assert client.post(f"/v1/debates/{missing_id}/approve", headers=HEADERS).status_code == 404
        assert client.get(f"/v1/debates/{missing_id}/stream", headers=HEADERS).status_code == 404


def test_missing_context_headers() -> None:
    with TestClient(app) as client:
        response = client.post("/v1/debates", json={"proposal": "Missing context should fail"})
        assert response.status_code == 400


def test_role_restrictions_on_admin_actions() -> None:
    with TestClient(app) as client:
        created = client.post(
            "/v1/debates",
            json={"proposal": "Require admin for approval"},
            headers=HEADERS,
        ).json()
        debate_id = created["debate_id"]

        approve_resp = client.post(f"/v1/debates/{debate_id}/approve", headers=MEMBER_HEADERS)
        assert approve_resp.status_code == 403

        audit_resp = client.get("/v1/admin/audit", headers=MEMBER_HEADERS)
        assert audit_resp.status_code == 403


def test_debate_stream_sse() -> None:
    with TestClient(app) as client:
        created = client.post(
            "/v1/debates",
            json={"proposal": "Enable weekly roadmap checkpoint"},
            headers=HEADERS,
        ).json()
        debate_id = created["debate_id"]
        response = client.get(f"/v1/debates/{debate_id}/stream", headers=HEADERS)
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]
        assert "debate_created" in response.text
