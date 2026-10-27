"""A code opens its door once. Accept, collect, free the door and stamp dwell — one transaction."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..clock import Clock, as_utc
from ..errors import CodeExpired, CodeUsed, NoSuchCode, NoSuchTower
from ..models import Door, Parcel, Tower
from ..schemas import PickupRequest
from .drops import hash_pickup_code

def pickup(
    session: Session, request: PickupRequest, clock: Clock, code_secret: str, tower_code: str = "A"
) -> tuple[Parcel, Door]:
    """Collect a parcel and release its door atomically."""
    try:
        tower = session.scalar(select(Tower).where(Tower.code == tower_code))
        if tower is None:
            raise NoSuchTower(f"There is no tower {tower_code!r}")

        submitted_hash = hash_pickup_code(request.code, code_secret)
        # Prefer an uncollected parcel when a six-digit code has been reused.
        parcel = session.scalar(
            select(Parcel).where(
                Parcel.tower_id == tower.id, Parcel.code_hash == submitted_hash
            ).order_by(Parcel.code_used_at.is_not(None), Parcel.id.desc()).limit(1)
        )
        if parcel is None:
            raise NoSuchCode(f"The pickup code does not exist in tower {tower_code}")
        if parcel.code_used_at is not None:
            raise CodeUsed("That code has already opened its door")

        now = as_utc(clock.now())
        if now >= as_utc(parcel.code_expires_at):
            raise CodeExpired("The pickup code has expired")

        door = session.get(Door, parcel.door_id)
        if door is None:
            raise NoSuchCode("The pickup code does not identify an available parcel")

        dwell = max(0, int((now - as_utc(parcel.dropped_at)).total_seconds()))
        parcel.state = "collected"
        parcel.collected_at = now
        parcel.dwell_seconds = dwell
        parcel.code_used_at = now
        door.current_parcel_id = None
        session.commit()
        return parcel, door
    except Exception:
        session.rollback()
        raise

# Backwards-compatible service name used by earlier Ticket 4 callers.
def validate_pickup_code(session: Session, request: PickupRequest, clock: Clock, code_secret: str, tower_code: str = "A") -> Parcel:
    parcel, _door = pickup(session, request, clock, code_secret, tower_code)
    return parcel
