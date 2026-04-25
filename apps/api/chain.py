import hashlib
import os
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from apps.api.models import ChainAnchorModel


class ChainAdapter:
    def anchor_decision(self, debate_id: str, report_hash: str, network: str) -> dict:
        raise NotImplementedError

    def get_tx_status(self, tx_hash: str, submitted_at_iso: str) -> str:
        raise NotImplementedError


class DeterministicChainAdapter(ChainAdapter):
    def anchor_decision(self, debate_id: str, report_hash: str, network: str) -> dict:
        seed = f"{debate_id}:{report_hash}:{network}"
        tx_hash = hashlib.sha256(seed.encode("utf-8")).hexdigest()
        return {"tx_hash": tx_hash, "provider": "deterministic", "network": network}

    def get_tx_status(self, tx_hash: str, submitted_at_iso: str) -> str:
        _ = tx_hash
        submitted = datetime.fromisoformat(submitted_at_iso)
        age_seconds = (datetime.now(UTC) - submitted).total_seconds()
        return "confirmed" if age_seconds > 1 else "pending"


def get_chain_adapter() -> ChainAdapter:
    provider = os.getenv("CHAIN_PROVIDER", "deterministic").lower()
    if provider == "deterministic":
        return DeterministicChainAdapter()
    return DeterministicChainAdapter()


def refresh_tx_status(db: Session, tenant_id: str, tx_hash: str, adapter: ChainAdapter | None = None) -> dict | None:
    row = (
        db.query(ChainAnchorModel)
        .filter(ChainAnchorModel.tenant_id == tenant_id, ChainAnchorModel.tx_hash == tx_hash)
        .first()
    )
    if row is None:
        return None
    resolved = (adapter or get_chain_adapter()).get_tx_status(tx_hash=row.tx_hash, submitted_at_iso=row.created_at)
    row.status = resolved
    row.updated_at = datetime.now(UTC).isoformat()
    db.commit()
    db.refresh(row)
    return {
        "tx_hash": row.tx_hash,
        "status": row.status,
        "provider": row.provider,
        "network": row.network,
        "debate_id": row.debate_id,
        "report_hash": row.report_hash,
    }
