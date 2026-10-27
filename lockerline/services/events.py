"""Append-only event recording."""
import json
from datetime import datetime

from sqlalchemy import insert
from sqlalchemy.orm import Session

from ..models import Event


def record(session: Session, tower_id: int, parcel_id: int, kind: str, at: datetime, data: dict | None = None) -> int:
    facts = data or {}
    event_id = session.execute(
        insert(Event).values(tower_id=tower_id, parcel_id=parcel_id, kind=kind, at=at, data=json.dumps(facts)).returning(Event.id)
    ).scalar_one()
    return event_id
