"""Read-only current policy settings."""
from fastapi import APIRouter

from ..schemas import SettingsOut
from ..services.doors import SIZES
from . import SettingsDep

router = APIRouter(tags=["settings"])


@router.get("/settings", response_model=SettingsOut, summary="The rules in force (read-only)")
def get_settings_(settings: SettingsDep) -> SettingsOut:
    return SettingsOut(free_window_hours=settings.free_window_hours, sizes=list(SIZES))
