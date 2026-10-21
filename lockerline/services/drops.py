"""Parcel booking rules for Ticket 2."""
from datetime import datetime
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..clock import Clock
from ..errors import NoDoorFree, NoSuchFlat, NoSuchTower
from ..models import Door, Parcel, Resident, Tower
from ..schemas import DropOut, DropRequest

SIZE_ORDER = ("S", "M", "L")


def parcel_public_id(parcel_id: int) -> str:
    return f"P{parcel_id:03d}"


def _tower(session: Session, code: str) -> Tower:
    tower = session.scalar(select(Tower).where(Tower.code == code))
    if tower is None:
        raise NoSuchTower(f"There is no tower {code!r}")
    return tower


def _free_sizes(session: Session, tower_id: int) -> list[str]:
    rows = session.scalars(
        select(Door.size_class)
        .where(Door.tower_id == tower_id, Door.current_parcel_id.is_(None))
        .distinct()
    )
    found = set(rows)
    return [size for size in SIZE_ORDER if size in found]


def create_drop(session: Session, request: DropRequest, clock: Clock, tower_code: str = "A") -> DropOut:
    """Validate first, then save parcel and door assignment in one transaction."""
    try:
        tower = _tower(session, tower_code)

        resident = session.scalar(
            select(Resident).where(
                Resident.tower_id == tower.id,
                Resident.flat == request.flat,
            )
        )
        if resident is None:
            raise NoSuchFlat(f"Flat {request.flat!r} does not exist in tower {tower_code}")

        door = session.scalar(
            select(Door)
            .where(
                Door.tower_id == tower.id,
                Door.size_class == request.size_class,
                Door.current_parcel_id.is_(None),
            )
            .order_by(Door.no.asc())
            .limit(1)
        )
        if door is None:
            raise NoDoorFree(
                f"No free door of size {request.size_class}",
                free_sizes=_free_sizes(session, tower.id),
            )

        # Stamp the time once; the response and database use the same value.
        dropped_at = clock.now()
        parcel = Parcel(
            tower_id=tower.id,
            flat=request.flat,
            size_class=request.size_class,
            door_id=door.id,
            state="holding",
            dropped_at=dropped_at,
        )
        session.add(parcel)
        session.flush()  # obtain parcel.id before linking it to the door

        # Set the door only after the parcel insert succeeded.
        door.current_parcel_id = parcel.id
        session.commit()

        return DropOut(
            parcel_id=parcel_public_id(parcel.id),
            door=door.no,
            size_class=parcel.size_class,
            flat=parcel.flat,
            dropped_at=dropped_at,
        )
    except Exception:
        # Also handles failures injected after flush: neither row nor door link remains.
        session.rollback()
        raise


def parse_parcel_id(value: str) -> int | None:
    """Accept public IDs such as P017; malformed IDs simply cannot match a parcel."""
    match = re.fullmatch(r"P(\d+)", value)
    return int(match.group(1)) if match else None
