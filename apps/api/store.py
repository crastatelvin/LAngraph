from dataclasses import dataclass, field
from uuid import uuid4

from packages.schemas.debate import DebateEvent, DebateRecord
from packages.graph_engine.workflow import run_debate_workflow


@dataclass
class DebateData:
    record: DebateRecord
    events: list[DebateEvent] = field(default_factory=list)


class DebateStore:
    def __init__(self) -> None:
        self._db: dict[str, DebateData] = {}
        self._tenant_index: dict[str, set[str]] = {}

    def create(self, proposal: str, tenant_id: str) -> DebateRecord:
        debate_id = str(uuid4())
        workflow = run_debate_workflow(proposal)
        record = DebateRecord(
            debate_id=debate_id,
            proposal=workflow["proposal"],
            status=workflow["status"],
        )
        events = [
            DebateEvent(
                seq=1,
                event_type="debate_created",
                payload={"proposal": workflow["proposal"], "tenant_id": tenant_id},
            ),
        ]
        for idx, item in enumerate(workflow["events"], start=2):
            events.append(DebateEvent(seq=idx, event_type=item["event_type"], payload=item["payload"]))
        self._db[debate_id] = DebateData(record=record, events=events)
        self._tenant_index.setdefault(tenant_id, set()).add(debate_id)
        return record

    def get(self, debate_id: str, tenant_id: str) -> DebateRecord | None:
        if debate_id not in self._tenant_index.get(tenant_id, set()):
            return None
        data = self._db.get(debate_id)
        if data is None:
            return None
        return data.record

    def get_events(self, debate_id: str, tenant_id: str) -> list[DebateEvent] | None:
        if debate_id not in self._tenant_index.get(tenant_id, set()):
            return None
        data = self._db.get(debate_id)
        if data is None:
            return None
        return data.events

    def approve(self, debate_id: str, tenant_id: str) -> DebateRecord | None:
        if debate_id not in self._tenant_index.get(tenant_id, set()):
            return None
        data = self._db.get(debate_id)
        if data is None:
            return None
        data.record.status = "approved"
        seq = len(data.events) + 1
        data.events.append(
            DebateEvent(seq=seq, event_type="human_approved", payload={"status": "approved"})
        )
        return data.record
