"""The wall. A door's state is derived from current_parcel_id."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..clock import Clock, as_utc
from ..errors import NoSuchDoor, NoSuchTower
from ..models import Door, Parcel, Tower
from ..schemas import DoorListItem, DoorOut, DoorsOut
from .drops import parcel_public_id

SIZES = ("S", "M", "L")


def get_tower(session: Session, code: str) -> Tower:
    tower = session.scalar(select(Tower).where(Tower.code == code))
    if tower is None:
        raise NoSuchTower(f"There is no tower {code!r}")
    return tower


def door_state(door: Door) -> str:
    return "holding" if door.current_parcel_id is not None else "free"


def _parcel_for_door(session: Session, door: Door) -> Parcel | None:
    if door.current_parcel_id is None:
        return None
    return session.get(Parcel, door.current_parcel_id)


def _dwell_seconds(parcel: Parcel, clock: Clock) -> int:
    return max(0, int((as_utc(clock.now()) - as_utc(parcel.dropped_at)).total_seconds()))


def list_doors(session: Session, tower_code: str, size: str | None, state: str | None, clock: Clock) -> DoorsOut:
    tower = get_tower(session, tower_code)
    query = select(Door).where(Door.tower_id == tower.id).order_by(Door.no)
    if size is not None:
        query = query.where(Door.size_class == size)
    doors = list(session.scalars(query))
    if state is not None:
        doors = [door for door in doors if door_state(door) == state]

    items = []
    for door in doors:
        parcel = _parcel_for_door(session, door)
        if parcel is None:
            items.append(DoorListItem(no=door.no, size=door.size_class, state="free"))
        else:
            items.append(
                DoorListItem(
                    no=door.no,
                    size=door.size_class,
                    state="holding",
                    parcel_id=parcel_public_id(parcel.id),
                    dwell_seconds=_dwell_seconds(parcel, clock),
                )
            )

    free = sum(1 for door in doors if door.current_parcel_id is None)
    return DoorsOut(tower=tower.code, free=free, doors=items)


def get_door(session: Session, tower_code: str, no: str, clock: Clock) -> DoorOut:
    tower = get_tower(session, tower_code)
    door = session.scalar(
        select(Door).where(Door.tower_id == tower.id, Door.no == no)
    )
    if door is None:
        raise NoSuchDoor(f"There is no door {no!r} in tower {tower_code}")

    parcel = _parcel_for_door(session, door)
    if parcel is None:
        return DoorOut(no=door.no, size=door.size_class, state="free")

    return DoorOut(
        no=door.no,
        size=door.size_class,
        state="holding",
        parcel_id=parcel_public_id(parcel.id),
        flat=parcel.flat,
        dwell_seconds=_dwell_seconds(parcel, clock),
    )
