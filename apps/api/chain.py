import hashlib
import os
from datetime import UTC, datetime

from sqlalchemy.orm import Session

from apps.api.models import ChainAnchorJobModel, ChainAnchorModel


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


def queue_status(db: Session, tenant_id: str | None = None) -> dict:
    query = db.query(ChainAnchorJobModel)
    if tenant_id:
        query = query.filter(ChainAnchorJobModel.tenant_id == tenant_id)
    queued = query.filter(ChainAnchorJobModel.status.in_(["queued", "retry"])).count()
    submitted = query.filter(ChainAnchorJobModel.status == "submitted").count()
    failed = query.filter(ChainAnchorJobModel.status == "failed").count()
    return {"queued": queued, "submitted": submitted, "failed": failed}


def process_anchor_jobs(
    db: Session,
    max_items: int = 20,
    tenant_id: str | None = None,
    adapter: ChainAdapter | None = None,
) -> dict:
    resolved = adapter or get_chain_adapter()
    query = db.query(ChainAnchorJobModel).filter(ChainAnchorJobModel.status.in_(["queued", "retry"]))
    if tenant_id:
        query = query.filter(ChainAnchorJobModel.tenant_id == tenant_id)
    jobs = query.order_by(ChainAnchorJobModel.created_at.asc()).limit(max_items).all()

    processed = 0
    submitted = 0
    failed = 0
    retried = 0
    for job in jobs:
        processed += 1
        job.status = "processing"
        job.attempts += 1
        job.updated_at = datetime.now(UTC).isoformat()
        try:
            anchor_result = resolved.anchor_decision(
                debate_id=job.debate_id,
                report_hash=job.report_hash,
                network=job.network,
            )
            existing = (
                db.query(ChainAnchorModel)
                .filter(ChainAnchorModel.tenant_id == job.tenant_id, ChainAnchorModel.tx_hash == anchor_result["tx_hash"])
                .first()
            )
            if existing is None:
                now_iso = datetime.now(UTC).isoformat()
                db.add(
                    ChainAnchorModel(
                        anchor_id=f"anchor-job-{job.job_id}",
                        tenant_id=job.tenant_id,
                        debate_id=job.debate_id,
                        report_hash=job.report_hash,
                        tx_hash=anchor_result["tx_hash"],
                        provider=anchor_result["provider"],
                        network=anchor_result["network"],
                        status="submitted",
                        submitted_by=job.requested_by,
                        created_at=now_iso,
                        updated_at=now_iso,
                    )
                )
            job.status = "submitted"
            job.tx_hash = anchor_result["tx_hash"]
            job.last_error = None
            submitted += 1
        except Exception as exc:
            job.last_error = str(exc)
            if job.attempts < 3:
                job.status = "retry"
                retried += 1
            else:
                job.status = "failed"
                failed += 1
        job.updated_at = datetime.now(UTC).isoformat()
    db.commit()
    remaining = (
        db.query(ChainAnchorJobModel)
        .filter(
            ChainAnchorJobModel.status.in_(["queued", "retry"]),
            ChainAnchorJobModel.tenant_id == tenant_id if tenant_id else True,
        )
        .count()
    )
    return {
        "processed": processed,
        "submitted": submitted,
        "failed": failed,
        "retried": retried,
        "remaining": remaining,
    }
