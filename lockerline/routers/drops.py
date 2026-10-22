"""Courier parcel drop endpoint."""
from fastapi import APIRouter, Request, Response, status

from ..schemas import DropOut, DropRequest
from ..services import drops
from . import ClockDep, SessionDep

router = APIRouter(tags=["drops"])

@router.post("/drops", response_model=DropOut, status_code=status.HTTP_201_CREATED)
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
