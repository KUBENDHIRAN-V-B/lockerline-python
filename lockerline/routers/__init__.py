"""Routes parse and delegate; they hold no rules. The request-scoped dependencies
(session, clock, settings) are declared here so the services never see the web framework."""
from typing import Annotated

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from ..clock import Clock, get_clock
from ..db import get_session
from ..settings import Settings


def get_settings(request: Request) -> Settings:
    return request.app.state.settings


SessionDep = Annotated[Session, Depends(get_session)]
ClockDep = Annotated[Clock, Depends(get_clock)]
SettingsDep = Annotated[Settings, Depends(get_settings)]