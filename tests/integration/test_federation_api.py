from pathlib import Path
import sys

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.main import app
from apps.api.db import Base, SessionLocal, engine
from apps.api.models import FederationModel, FederationSessionModel, FederationSessionSubmissionModel

HEADERS = {
    "X-Tenant-Id": "tenant-fed-001",
    "X-User-Id": "owner-1",
    "X-User-Role": "owner",
    "X-Request-Id": "req-fed-001",
}
MEMBER_HEADERS = {
    "X-Tenant-Id": "tenant-fed-001",
    "X-User-Id": "member-1",
    "X-User-Role": "member",
    "X-Request-Id": "req-fed-002",
}


def _reset_federation_tables() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.query(FederationSessionSubmissionModel).delete()
    db.query(FederationSessionModel).delete()
    db.query(FederationModel).delete()
    db.commit()
    db.close()


def test_federation_end_to_end() -> None:
    _reset_federation_tables()
    with TestClient(app) as client:
        created = client.post("/v1/federations", json={"name": "Global Product Council"}, headers=HEADERS)
        assert created.status_code == 200
        federation_id = created.json()["federation_id"]

        session = client.post(
            f"/v1/federations/{federation_id}/sessions",
            json={"mode": "treaty"},
            headers=HEADERS,
        )
        assert session.status_code == 200
        session_id = session.json()["session_id"]

        join_a = client.post(
            f"/v1/federations/sessions/{session_id}/join",
            json={
                "parliament_name": "Platform Parliament",
                "position": "APPROVED",
                "confidence": 0.82,
                "summary": "Shared architecture and reliability gains.",
                "weight": 1.2,
            },
            headers=HEADERS,
        )
        assert join_a.status_code == 200
        join_b = client.post(
            f"/v1/federations/sessions/{session_id}/join",
            json={
                "parliament_name": "Security Parliament",
                "position": "REJECTED",
                "confidence": 0.4,
                "summary": "Needs stronger controls before broad rollout.",
                "weight": 1.0,
            },
            headers=HEADERS,
        )
        assert join_b.status_code == 200

        decision = client.get(f"/v1/federations/sessions/{session_id}/decision", headers=HEADERS)
        assert decision.status_code == 200
        payload = decision.json()
        assert payload["session_id"] == session_id
        assert payload["submissions"] == 2
        assert payload["decision"] in {"APPROVED", "REJECTED", "INCONCLUSIVE"}


def test_federation_admin_permissions() -> None:
    _reset_federation_tables()
    with TestClient(app) as client:
        response = client.post("/v1/federations", json={"name": "Restricted"}, headers=MEMBER_HEADERS)
        assert response.status_code == 403


def test_federation_session_missing() -> None:
    _reset_federation_tables()
    with TestClient(app) as client:
        missing = client.get("/v1/federations/sessions/missing-session/decision", headers=HEADERS)
        assert missing.status_code == 404
