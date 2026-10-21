from fastapi import APIRouter

from ..schemas import DoorOut, DoorsOut, DoorState, SizeClass
from ..services import doors
from . import ClockDep, SessionDep

router = APIRouter(prefix="/towers/{tower}/doors")


@router.get(
    "", response_model=DoorsOut, response_model_exclude_none=True,
)
def list_doors(tower: str, session: SessionDep, clock: ClockDep, size: SizeClass | None = None,
               state: DoorState | None = None) -> DoorsOut:
    return doors.list_doors(session, tower, size, state, clock)


@router.get(
    "/{no}", response_model=DoorOut, response_model_exclude_none=True,
)
def get_door(tower: str, no: str, session: SessionDep, clock: ClockDep) -> DoorOut:
    return doors.get_door(session, tower, no, clock)