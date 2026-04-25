import json
from uuid import uuid4

from sqlalchemy.orm import Session

from apps.api.models import DebateEventModel, DebateModel
from packages.schemas.debate import DebateEvent, DebateRecord
from packages.graph_engine.workflow import run_debate_workflow


class DebateStore:
    def create(
        self,
        db: Session,
        proposal: str,
        tenant_id: str,
        request_id: str,
    ) -> tuple[DebateRecord, dict]:
        debate_id = str(uuid4())
        workflow_result = run_debate_workflow(proposal)
        workflow = workflow_result["state"]
        record = DebateRecord(
            debate_id=debate_id,
            proposal=workflow["proposal"],
            status=workflow["status"],
        )
        events = [
            DebateEvent(
                seq=1,
                event_type="debate_created",
                payload={
                    "proposal": workflow["proposal"],
                    "tenant_id": tenant_id,
                    "request_id": request_id,
                },
            ),
        ]
        for idx, item in enumerate(workflow["events"], start=2):
            events.append(DebateEvent(seq=idx, event_type=item["event_type"], payload=item["payload"]))

        db.add(
            DebateModel(
                debate_id=record.debate_id,
                tenant_id=tenant_id,
                proposal=record.proposal,
                status=record.status,
            )
        )
        for event in events:
            db.add(
                DebateEventModel(
                    debate_id=record.debate_id,
                    tenant_id=tenant_id,
                    seq=event.seq,
                    event_type=event.event_type,
                    payload_json=json.dumps(event.payload),
                )
            )
        db.commit()
        return record, workflow_result["metrics"]

    def get(self, db: Session, debate_id: str, tenant_id: str) -> DebateRecord | None:
        row = (
            db.query(DebateModel)
            .filter(DebateModel.debate_id == debate_id, DebateModel.tenant_id == tenant_id)
            .first()
        )
        if row is None:
            return None
        return DebateRecord(debate_id=row.debate_id, proposal=row.proposal, status=row.status)

    def get_events(self, db: Session, debate_id: str, tenant_id: str) -> list[DebateEvent] | None:
        debate_exists = (
            db.query(DebateModel)
            .filter(DebateModel.debate_id == debate_id, DebateModel.tenant_id == tenant_id)
            .first()
        )
        if debate_exists is None:
            return None
        rows = (
            db.query(DebateEventModel)
            .filter(DebateEventModel.debate_id == debate_id, DebateEventModel.tenant_id == tenant_id)
            .order_by(DebateEventModel.seq.asc())
            .all()
        )
        return [
            DebateEvent(seq=row.seq, event_type=row.event_type, payload=json.loads(row.payload_json))
            for row in rows
        ]

    def approve(self, db: Session, debate_id: str, tenant_id: str) -> DebateRecord | None:
        debate = (
            db.query(DebateModel)
            .filter(DebateModel.debate_id == debate_id, DebateModel.tenant_id == tenant_id)
            .first()
        )
        if debate is None:
            return None
        debate.status = "approved"
        seq = (
            db.query(DebateEventModel)
            .filter(DebateEventModel.debate_id == debate_id, DebateEventModel.tenant_id == tenant_id)
            .count()
            + 1
        )
        db.add(
            DebateEventModel(
                debate_id=debate_id,
                tenant_id=tenant_id,
                seq=seq,
                event_type="human_approved",
                payload_json=json.dumps({"status": "approved"}),
            )
        )
        db.commit()
        return DebateRecord(debate_id=debate.debate_id, proposal=debate.proposal, status=debate.status)

    def reject(self, db: Session, debate_id: str, tenant_id: str) -> DebateRecord | None:
        debate = (
            db.query(DebateModel)
            .filter(DebateModel.debate_id == debate_id, DebateModel.tenant_id == tenant_id)
            .first()
        )
        if debate is None:
            return None
        debate.status = "rejected"
        seq = (
            db.query(DebateEventModel)
            .filter(DebateEventModel.debate_id == debate_id, DebateEventModel.tenant_id == tenant_id)
            .count()
            + 1
        )
        db.add(
            DebateEventModel(
                debate_id=debate_id,
                tenant_id=tenant_id,
                seq=seq,
                event_type="human_rejected",
                payload_json=json.dumps({"status": "rejected"}),
            )
        )
        db.commit()
        return DebateRecord(debate_id=debate.debate_id, proposal=debate.proposal, status=debate.status)
