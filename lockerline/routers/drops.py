"""Courier parcel drop endpoint."""
from fastapi import APIRouter, Request, Response, status

from ..errors import NoDoorFree, NoSuchFlat
from ..handlers import VALIDATION_RESPONSE, responses
from ..schemas import DropOut, DropRequest
from ..services import drops
from . import ClockDep, SessionDep

router = APIRouter(tags=["drops"])

CREATED = {
    201: {"description": "A door was chosen; the parcel is at the Location given",
          "headers": {"Location": {"schema": {"type": "string"}, "description": "The new parcel, e.g. /parcels/P017"}}}}


@router.post(
    "/drops", response_model=DropOut, status_code=status.HTTP_201_CREATED,
    summary="Book a door for a parcel",
    responses={
        **CREATED,
        **responses(
            (NoSuchFlat, "Flat '999' does not exist in tower A"),
            (NoDoorFree, "No free L door", {"free_sizes": ["S", "M"]}),
        ),
        **VALIDATION_RESPONSE,
    },
)
def create_drop(
    body: DropRequest,
    response: Response,
    request: Request,
    session: SessionDep,
    clock: ClockDep,
) -> DropOut:
    settings = request.app.state.settings
    result = drops.create_drop(
        session,
        body,
        clock,
        free_window_hours=settings.free_window_hours,
        code_secret=settings.code_secret,
    )
    response.headers["Location"] = f"/parcels/{result.parcel_id}"
    return result
