
"""Pickup-code validation service."""

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..clock import Clock, as_utc
from ..errors import CodeExpired, NoSuchCode, NoSuchTower
from ..models import Parcel, Tower
from ..schemas import PickupRequest
from .drops import hash_pickup_code


def validate_pickup_code(
    session: Session,
    request: PickupRequest,
    clock: Clock,
    code_secret: str,
    tower_code: str = "A",
) -> Parcel:
    tower = session.scalar(
        select(Tower).where(Tower.code == tower_code)
    )

    if tower is None:
        raise NoSuchTower(f"There is no tower {tower_code!r}")

    submitted_hash = hash_pickup_code(
        request.code,
        code_secret,
    )

    parcel = session.scalar(
        select(Parcel).where(
            Parcel.tower_id == tower.id,
            Parcel.code_hash == submitted_hash,
        )
    )

    if parcel is None:
        raise NoSuchCode(
            f"The pickup code does not exist in tower {tower_code}"
        )

    now = as_utc(clock.now())
    expires_at = as_utc(parcel.code_expires_at)

    if now >= expires_at:
        raise CodeExpired("The pickup code has expired")

    return parcel
