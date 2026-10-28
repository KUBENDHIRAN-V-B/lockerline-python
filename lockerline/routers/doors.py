from fastapi import APIRouter

from ..errors import NoSuchDoor, NoSuchTower
from ..handlers import FILTER_RESPONSE, responses
from ..schemas import DoorOut, DoorsOut, DoorState, SizeClass
from ..services import doors
from . import ClockDep, SessionDep

router = APIRouter(prefix="/towers/{tower}/doors", tags=["doors"])


@router.get(
    "", response_model=DoorsOut, response_model_exclude_none=True,
    summary="The wall: every door with its derived state",
    responses={**FILTER_RESPONSE, **responses((NoSuchTower, "There is no tower 'Z'"))},
)
def list_doors(tower: str, session: SessionDep, clock: ClockDep, size: SizeClass | None = None,
               state: DoorState | None = None) -> DoorsOut:
    return doors.list_doors(session, tower, size, state, clock)


@router.get(
    "/{no}", response_model=DoorOut, response_model_exclude_none=True,
    summary="One door",
    responses=responses(
        (NoSuchDoor, "There is no door 'D99' in tower A"),
        (NoSuchTower, "There is no tower 'Z'"),
    ),
)
def get_door(tower: str, no: str, session: SessionDep, clock: ClockDep) -> DoorOut:
    return doors.get_door(session, tower, no, clock)
