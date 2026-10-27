"""One parcel, with the only history the wall keeps — its events, in order."""
import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..errors import NoSuchParcel
from ..models import Door, Event, Parcel
from ..schemas import EventOut, ParcelOut
from .drops import parse_parcel_id, parcel_public_id


def get_parcel(session: Session, public_id: str) -> ParcelOut:
    numeric_id = parse_parcel_id(public_id)
    parcel = None if numeric_id is None else session.get(Parcel, numeric_id)
    if parcel is None:
        raise NoSuchParcel(f"Parcel {public_id!r} does not exist")

    door = session.get(Door, parcel.door_id)
    # A valid parcel should always point to a door.
    if door is None:
        raise NoSuchParcel(f"Parcel {public_id!r} does not exist")

    rows = session.scalars(select(Event).where(Event.parcel_id == parcel.id).order_by(Event.at, Event.id))
    events = [EventOut(at=row.at, kind=row.kind, **json.loads(row.data)) for row in rows]

    return ParcelOut(
        parcel_id=parcel_public_id(parcel.id),
        door=door.no,
        size_class=parcel.size_class,
        flat=parcel.flat,
        state=parcel.state,
        dropped_at=parcel.dropped_at,
        events=events,
    )
