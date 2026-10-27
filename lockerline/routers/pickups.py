"""Pickup endpoint: collect a parcel and free its door."""
from fastapi import APIRouter

from ..ids import parcel_public
from ..schemas import PickupOut, PickupRequest
from ..services.pickups import pickup
from . import ClockDep, SessionDep, SettingsDep

router = APIRouter(tags=["pickups"])

@router.post("/pickups", response_model=PickupOut)
def collect_pickup(body: PickupRequest, session: SessionDep, clock: ClockDep, settings: SettingsDep) -> PickupOut:
    parcel, door = pickup(session, body, clock, settings.code_secret)
    return PickupOut(
        parcel_id=parcel_public(parcel.id),
        door=door.no,
        opened_at=parcel.collected_at,
        dwell_seconds=parcel.dwell_seconds,
    )
