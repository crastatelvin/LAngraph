from pathlib import Path
import sys

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from apps.api.main import app
from apps.api.db import Base, SessionLocal, engine
from apps.api.models import ChainAnchorModel

HEADERS = {
    "X-Tenant-Id": "tenant-chain-001",
    "X-User-Id": "owner-1",
    "X-User-Role": "owner",
    "X-Request-Id": "req-chain-001",
}
MEMBER_HEADERS = {
    "X-Tenant-Id": "tenant-chain-001",
    "X-User-Id": "member-1",
    "X-User-Role": "member",
    "X-Request-Id": "req-chain-002",
}


def _reset_chain_table() -> None:
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    db.query(ChainAnchorModel).delete()
    db.commit()
    db.close()


def test_anchor_and_get_tx_status() -> None:
    _reset_chain_table()
    with TestClient(app) as client:
        anchor = client.post(
            "/v1/chain/anchor-decision",
            json={"debate_id": "debate-123", "report_hash": "a" * 32, "network": "testnet"},
            headers=HEADERS,
        )
        assert anchor.status_code == 200
        anchor_payload = anchor.json()
        assert anchor_payload["status"] == "submitted"
        tx_hash = anchor_payload["tx_hash"]

        tx = client.get(f"/v1/chain/tx/{tx_hash}", headers=HEADERS)
        assert tx.status_code == 200
        tx_payload = tx.json()
        assert tx_payload["tx_hash"] == tx_hash
        assert tx_payload["status"] in {"pending", "confirmed"}


def test_anchor_duplicate_is_idempotent() -> None:
    _reset_chain_table()
    with TestClient(app) as client:
        payload = {"debate_id": "debate-dup", "report_hash": "b" * 32, "network": "testnet"}
        first = client.post("/v1/chain/anchor-decision", json=payload, headers=HEADERS)
        second = client.post("/v1/chain/anchor-decision", json=payload, headers=HEADERS)
        assert first.status_code == 200
        assert second.status_code == 200
        assert second.json()["duplicate"] is True
        assert first.json()["tx_hash"] == second.json()["tx_hash"]


def test_chain_endpoints_require_admin() -> None:
    _reset_chain_table()
    with TestClient(app) as client:
        denied = client.post(
            "/v1/chain/anchor-decision",
            json={"debate_id": "debate-rbac", "report_hash": "c" * 32, "network": "testnet"},
            headers=MEMBER_HEADERS,
        )
        assert denied.status_code == 403
