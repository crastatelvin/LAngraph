from dataclasses import dataclass
from datetime import datetime, UTC


@dataclass
class AuditEvent:
    timestamp: str
    tenant_id: str
    actor_id: str
    action: str
    resource: str
    payload: dict


class AuditStore:
    def __init__(self) -> None:
        self._events: list[AuditEvent] = []

    def append(
        self,
        tenant_id: str,
        actor_id: str,
        action: str,
        resource: str,
        payload: dict,
    ) -> None:
        self._events.append(
            AuditEvent(
                timestamp=datetime.now(UTC).isoformat(),
                tenant_id=tenant_id,
                actor_id=actor_id,
                action=action,
                resource=resource,
                payload=payload,
            )
        )

    def list_for_tenant(self, tenant_id: str) -> list[AuditEvent]:
        return [event for event in self._events if event.tenant_id == tenant_id]
