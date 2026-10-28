"""Read-only current policy settings."""
from fastapi import APIRouter
from sqlalchemy import text

from ..schemas import HealthOut, SettingsOut
from ..services.doors import SIZES
from . import SessionDep, SettingsDep

router = APIRouter(tags=["settings"])


@router.get("/settings", response_model=SettingsOut, summary="The rules in force (read-only)")
def get_settings_(settings: SettingsDep) -> SettingsOut:
    return SettingsOut(free_window_hours=settings.free_window_hours, sizes=list(SIZES))



@router.get("/healthz", response_model=HealthOut, summary="The process is up and can reach its database")
def health(session: SessionDep) -> HealthOut:
    session.execute(text("SELECT 1"))          # a database that cannot be reached is the one 500 handler's answer
    return HealthOut(status="ok")
