from pathlib import Path
import sys

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.main import app
from apps.api.db import Base, SessionLocal, engine
from apps.api.models import AgentOutcomeModel, AgentProfileModel, AgentProfileVersionModel

HEADERS = {
    "X-Tenant-Id": "tenant-int-001",
    "X-User-Id": "admin-1",
    "X-User-Role": "admin",
    "X-Request-Id": "req-agents-001",
}
MEMBER_HEADERS = {
    "X-Tenant-Id": "tenant-int-001",
    "X-User-Id": "member-1",
    "X-User-Role": "member",
    "X-Request-Id": "req-agents-002",
}


def _reset_agent_tables() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.query(AgentOutcomeModel).delete()
    db.query(AgentProfileVersionModel).delete()
    db.query(AgentProfileModel).delete()
    db.commit()
    db.close()


def test_patch_and_list_agents() -> None:
    _reset_agent_tables()
    with TestClient(app) as client:
        patch_resp = client.patch(
            "/v1/agents/agent-001",
            json={"traits": {"risk_tolerance": 0.3, "priority": "reliability"}, "reason": "initial_profile"},
            headers=HEADERS,
        )
        assert patch_resp.status_code == 200
        patched = patch_resp.json()
        assert patched["agent_id"] == "agent-001"
        assert patched["version"] == 1

        list_resp = client.get("/v1/agents", headers=HEADERS)
        assert list_resp.status_code == 200
        agents = list_resp.json()
        assert any(agent["agent_id"] == "agent-001" for agent in agents)


def test_patch_agent_requires_admin() -> None:
    _reset_agent_tables()
    with TestClient(app) as client:
        response = client.patch(
            "/v1/agents/agent-002",
            json={"traits": {"risk_tolerance": 0.8}, "reason": "member_attempt"},
            headers=MEMBER_HEADERS,
        )
        assert response.status_code == 403


def test_recalibrate_agent() -> None:
    _reset_agent_tables()
    with TestClient(app) as client:
        client.patch(
            "/v1/agents/agent-003",
            json={"traits": {"risk_tolerance": 0.4}, "reason": "seed"},
            headers=HEADERS,
        )
        recalibrate = client.post("/v1/agents/agent-003/recalibrate", headers=HEADERS)
        assert recalibrate.status_code == 200
        payload = recalibrate.json()
        assert payload["agent_id"] == "agent-003"
        assert payload["version"] == 2
        assert payload["calibration_score"] >= 0.55


def test_agent_outcome_evolve_and_rollback() -> None:
    _reset_agent_tables()
    with TestClient(app) as client:
        seed = client.patch(
            "/v1/agents/agent-004",
            json={"traits": {"risk_tolerance": 0.4, "reliability": 0.5}, "reason": "seed"},
            headers=HEADERS,
        )
        assert seed.status_code == 200

        outcome = client.post(
            "/v1/agents/agent-004/outcomes",
            json={
                "debate_id": "debate-900",
                "predicted_confidence": 0.4,
                "actual_score": 0.8,
                "notes": "Strong positive result",
            },
            headers=HEADERS,
        )
        assert outcome.status_code == 200
        assert outcome.json()["outcome_score"] > 0

        evolve = client.post(
            "/v1/agents/agent-004/evolve",
            json={"max_delta": 0.1, "reason": "auto_evolve_cycle"},
            headers=HEADERS,
        )
        assert evolve.status_code == 200
        evolved = evolve.json()
        assert evolved["agent"]["version"] == 2
        assert evolved["evolution"]["outcome_count"] >= 1

        rollback = client.post("/v1/agents/agent-004/rollback/1", headers=HEADERS)
        assert rollback.status_code == 200
        rolled = rollback.json()
        assert rolled["rollback"]["target_version"] == 1
        assert rolled["agent"]["version"] == 3
