"""Courier parcel drop endpoint."""
from fastapi import APIRouter, Response, status

from ..schemas import DropOut, DropRequest
from ..services import drops
from . import ClockDep, SessionDep

router = APIRouter(tags=["drops"])


@router.post("/drops", response_model=DropOut, status_code=status.HTTP_201_CREATED)
def create_drop(body: DropRequest, response: Response, session: SessionDep, clock: ClockDep) -> DropOut:
    result = drops.create_drop(session, body, clock)
    response.headers["Location"] = f"/parcels/{result.parcel_id}"
    return result
