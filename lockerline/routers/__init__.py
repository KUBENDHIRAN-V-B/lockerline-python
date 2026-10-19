"""Engine, sessions and the database dependency. SQLite; the schema is created at start-up."""
"""Dependencies for the routers."""
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from ..clock import Clock, get_clock
from ..db import get_session

SessionDep = Annotated[Session, Depends(get_session)]
ClockDep = Annotated[Clock, Depends(get_clock)]