"""Load the tower, its 48 doors and the residents once, before the first request. Idempotent."""
import csv
import logging
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Door, Resident, Tower

log = logging.getLogger("lockerline.seed")


def seed(session: Session, seed_dir: str) -> None:
    root = Path(seed_dir)
    tower = session.scalar(select(Tower).where(Tower.code == "A"))
    if tower is None:
        tower = Tower(code="A", name="Tower A")
        session.add(tower)
        session.flush()
    if session.scalar(select(Door.id).where(Door.tower_id == tower.id).limit(1)) is None:
        with (root / "doors.csv").open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                session.add(Door(tower_id=tower.id, no=row["no"], size_class=row["size_class"]))
    if session.scalar(select(Resident.id).where(Resident.tower_id == tower.id).limit(1)) is None:
        with (root / "residents.csv").open(newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                session.add(Resident(tower_id=tower.id, flat=row["flat"], name=row["name"]))
    session.commit()
    doors = session.scalar(select(Door.id).where(Door.tower_id == tower.id).limit(1))
    log.info("seed complete tower=%s doors_present=%s", tower.code, doors is not None)