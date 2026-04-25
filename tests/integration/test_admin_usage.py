from pathlib import Path
import sys

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.main import app
from apps.api.db import Base, SessionLocal, engine
from apps.api.models import AgentOutcomeModel, AgentProfileModel, AgentProfileVersionModel, ChainAnchorJobModel, UsageEventModel

HEADERS = {
    "X-Tenant-Id": "tenant-usage-001",
    "X-User-Id": "admin-usage-1",
    "X-User-Role": "admin",
    "X-Request-Id": "req-usage-001",
}
MEMBER_HEADERS = {
    "X-Tenant-Id": "tenant-usage-001",
    "X-User-Id": "member-usage-1",
    "X-User-Role": "member",
    "X-Request-Id": "req-usage-002",
}


def _reset_usage_related_tables() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.query(UsageEventModel).delete()
    db.query(ChainAnchorJobModel).delete()
    db.query(AgentOutcomeModel).delete()
    db.query(AgentProfileVersionModel).delete()
    db.query(AgentProfileModel).delete()
    db.commit()
    db.close()


def test_admin_usage_summary_and_events() -> None:
    _reset_usage_related_tables()
    with TestClient(app) as client:
        debate = client.post("/v1/debates", json={"proposal": "Usage metering baseline"}, headers=HEADERS)
        assert debate.status_code == 200
        debate_id = debate.json()["debate_id"]

        patch = client.patch(
            "/v1/agents/agent-usage-001",
            json={"traits": {"reliability": 0.6}, "reason": "seed"},
            headers=HEADERS,
        )
        assert patch.status_code == 200

        outcome = client.post(
            "/v1/agents/agent-usage-001/outcomes",
            json={
                "debate_id": debate_id,
                "predicted_confidence": 0.5,
                "actual_score": 0.7,
                "notes": "usage test",
            },
            headers=HEADERS,
        )
        assert outcome.status_code == 200

        queued = client.post(
            "/v1/chain/anchor-decision",
            json={"debate_id": debate_id, "report_hash": "e" * 32, "network": "testnet", "deferred": True},
            headers=HEADERS,
        )
        assert queued.status_code == 200
        assert queued.json()["queued"] is True

        usage = client.get("/v1/admin/usage?since_hours=24", headers=HEADERS)
        assert usage.status_code == 200
        payload = usage.json()
        assert payload["summary"]["total_events"] >= 3
        by_event = payload["summary"]["by_event_type"]
        assert by_event["debate.create"] >= 1
        assert by_event["agent.outcome.ingest"] >= 1
        assert by_event["chain.anchor.queue"] >= 1
        assert len(payload["events"]) >= 3


def test_admin_usage_requires_admin() -> None:
    _reset_usage_related_tables()
    with TestClient(app) as client:
        denied = client.get("/v1/admin/usage", headers=MEMBER_HEADERS)
        assert denied.status_code == 403
