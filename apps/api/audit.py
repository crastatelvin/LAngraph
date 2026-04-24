from dataclasses import dataclass
from datetime import datetime, UTC
import json

from sqlalchemy.orm import Session

from apps.api.models import AuditEventModel

@dataclass
class AuditEvent:
    timestamp: str
    tenant_id: str
    actor_id: str
    action: str
    resource: str
    payload: dict


class AuditStore:
    def append(
        self,
        db: Session,
        tenant_id: str,
        actor_id: str,
        action: str,
        resource: str,
        payload: dict,
    ) -> None:
        event = AuditEvent(
            timestamp=datetime.now(UTC).isoformat(),
            tenant_id=tenant_id,
            actor_id=actor_id,
            action=action,
            resource=resource,
            payload=payload,
        )
        db.add(
            AuditEventModel(
                tenant_id=event.tenant_id,
                actor_id=event.actor_id,
                action=event.action,
                resource=event.resource,
                payload_json=json.dumps(event.payload),
                timestamp=event.timestamp,
            )
        )
        db.commit()

    def list_for_tenant(self, db: Session, tenant_id: str) -> list[AuditEvent]:
        rows = (
            db.query(AuditEventModel)
            .filter(AuditEventModel.tenant_id == tenant_id)
            .order_by(AuditEventModel.id.asc())
            .all()
        )
        return [
            AuditEvent(
                timestamp=row.timestamp,
                tenant_id=row.tenant_id,
                actor_id=row.actor_id,
                action=row.action,
                resource=row.resource,
                payload=json.loads(row.payload_json),
            )
            for row in rows
        ]
