"""Parcel lookup endpoint."""
from fastapi import APIRouter

from ..schemas import ParcelOut
from ..services import parcels
from . import SessionDep

router = APIRouter(tags=["parcels"])


@router.get("/parcels/{parcel_id}", response_model=ParcelOut, response_model_exclude_none=True)
def get_parcel(parcel_id: str, session: SessionDep) -> ParcelOut:
    return parcels.get_parcel(session, parcel_id)
