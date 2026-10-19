"""The wall. State is derived on read — `holding` when a parcel sits in the door, `free` otherwise.
The size and state filters arrive already validated (typed query parameters); `free` counts the doors after them."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from ..clock import Clock
from ..errors import NoSuchDoor, NoSuchTower
from ..models import Door, Tower
from ..schemas import DoorListItem, DoorOut, DoorsOut

SIZES = ("S", "M", "L")


def get_tower(session: Session, code: str) -> Tower:
    tower = session.scalar(select(Tower).where(Tower.code == code))
    if tower is None:
        raise NoSuchTower(f"There is no tower {code!r}")
    return tower


def door_state(door: Door) -> str:
    return "holding" if door.current_parcel_id is not None else "free"


def list_doors(session: Session, tower_code: str, size: str | None, state: str | None, clock: Clock) -> DoorsOut:
    tower = get_tower(session, tower_code)
    query = select(Door).where(Door.tower_id == tower.id).order_by(Door.no)
    if size is not None:
        query = query.where(Door.size_class == size)
    doors = list(session.scalars(query))
    if state is not None:
        doors = [d for d in doors if door_state(d) == state]
    items = []
    for d in doors:
        item = DoorListItem(no=d.no, size=d.size_class, state=door_state(d))
        items.append(item)
    free = sum(1 for d in doors if d.current_parcel_id is None)       # of the doors shown, how many are free
    return DoorsOut(tower=tower.code, free=free, doors=items)


def get_door(session: Session, tower_code: str, no: str, clock: Clock) -> DoorOut:
    tower = get_tower(session, tower_code)
    door = session.scalar(select(Door).where(Door.tower_id == tower.id, Door.no == no))
    if door is None:
        raise NoSuchDoor(f"There is no door {no!r} in tower {tower_code}")
    out = DoorOut(no=door.no, size=door.size_class, state=door_state(door))
    return out

    