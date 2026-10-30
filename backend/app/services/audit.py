import hashlib
import json
import threading
from datetime import datetime
from typing import Any

from sqlalchemy import text
from sqlalchemy.orm import Session

from ..clock import Clock, as_utc
from ..models import AuditEvent


GENESIS_HASH = "0" * 64
_audit_lock = threading.Lock()


def canonical_json(value: dict[str, Any]) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def append_event(
    db: Session,
    actor_id: int | None,
    action: str,
    entity_type: str,
    entity_id: str,
    before: dict[str, Any] | None = None,
    after: dict[str, Any] | None = None,
    reason: str | None = None,
    request_id: str = "",
) -> AuditEvent:
    with _audit_lock:
        previous = db.query(AuditEvent).order_by(AuditEvent.id.desc()).first()
        prev_hash = previous.hash if previous else GENESIS_HASH
        occurred_at = Clock.now()
        payload = {
            "action": action,
            "actor_id": actor_id,
            "after": after,
            "before": before,
            "entity_id": entity_id,
            "entity_type": entity_type,
            "occurred_at": occurred_at.isoformat(timespec="microseconds").replace("+00:00", "Z"),
            "reason": reason,
            "request_id": request_id,
        }
        event_hash = hashlib.sha256(bytes.fromhex(prev_hash) + canonical_json(payload)).hexdigest()
        event = AuditEvent(
            actor_id=actor_id,
            action=action,
            entity_type=entity_type,
            entity_id=entity_id,
            before_json=json.dumps(before, sort_keys=True) if before is not None else None,
            after_json=json.dumps(after, sort_keys=True) if after is not None else None,
            reason=reason,
            occurred_at=occurred_at,
            request_id=request_id,
            prev_hash=prev_hash,
            hash=event_hash,
        )
        db.add(event)
        db.flush()
        return event


def verify_chain(db: Session) -> dict[str, Any]:
    expected_previous = GENESIS_HASH
    events = db.query(AuditEvent).order_by(AuditEvent.id.asc()).all()
    for index, event in enumerate(events):
        payload = {
            "action": event.action,
            "actor_id": event.actor_id,
            "after": json.loads(event.after_json) if event.after_json else None,
            "before": json.loads(event.before_json) if event.before_json else None,
            "entity_id": event.entity_id,
            "entity_type": event.entity_type,
            "occurred_at": as_utc(event.occurred_at).isoformat(timespec="microseconds").replace("+00:00", "Z"),
            "reason": event.reason,
            "request_id": event.request_id,
        }
        calculated = hashlib.sha256(bytes.fromhex(expected_previous) + canonical_json(payload)).hexdigest()
        if event.prev_hash != expected_previous or event.hash != calculated:
            return {"valid": False, "first_bad_index": index, "event_id": event.id, "checked": index + 1}
        expected_previous = event.hash
    return {"valid": True, "first_bad_index": None, "event_id": None, "checked": len(events)}


def tamper_first_event(db: Session) -> int:
    first = db.query(AuditEvent).order_by(AuditEvent.id.asc()).first()
    if first is None:
        raise ValueError("There are no audit events to tamper with")
    db.execute(text("UPDATE audit_events SET action = :action WHERE id = :id"), {"action": first.action + "_TAMPERED", "id": first.id})
    db.flush()
    return first.id
