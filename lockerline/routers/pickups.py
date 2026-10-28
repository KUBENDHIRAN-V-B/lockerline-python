"""Pickup endpoint: collect a parcel and free its door."""
from fastapi import APIRouter

from ..errors import CodeExpired, CodeUsed, NoSuchCode
from ..handlers import VALIDATION_RESPONSE, responses
from ..ids import parcel_public
from ..schemas import PickupOut, PickupRequest
from ..services.pickups import pickup
from . import ClockDep, SessionDep, SettingsDep

router = APIRouter(tags=["pickups"])


@router.post(
    "/pickups", response_model=PickupOut,
    summary="Open a door with a pickup code",
    responses={**responses(
        (CodeUsed, "That code has already opened its door"),
        (NoSuchCode, "That code does not exist in this tower"),
        (CodeExpired, "That code's window has passed"),
    ), **VALIDATION_RESPONSE},
)
def collect_pickup(body: PickupRequest, session: SessionDep, clock: ClockDep, settings: SettingsDep) -> PickupOut:
    parcel, door = pickup(session, body, clock, settings.code_secret)
    return PickupOut(
        parcel_id=parcel_public(parcel.id),
        door=door.no,
        opened_at=parcel.collected_at,
        dwell_seconds=parcel.dwell_seconds,
    )
