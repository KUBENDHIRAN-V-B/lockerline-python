
"""Pickup-code validation endpoint."""

from fastapi import APIRouter

from ..schemas import PickupRequest
from ..services.pickups import validate_pickup_code
from . import ClockDep, SessionDep, SettingsDep

router = APIRouter(tags=["pickups"])


@router.post("/pickups")
def validate_pickup(
    body: PickupRequest,
    session: SessionDep,
    clock: ClockDep,
    settings: SettingsDep,
):
    # IMPORTANT: use the same secret configured for POST /drops.
    parcel = validate_pickup_code(
        session=session,
        request=body,
        clock=clock,
        code_secret=settings.code_secret,
    )

    # Ticket 4 validates only; it does not collect the parcel.
    return {
        "valid": True,
        "parcel_id": f"P{parcel.id:03d}",
    }
