"""Engine, sessions and the database dependency. SQLite; the schema is created at start-up."""
from collections.abc import Iterator

from fastapi import Request
from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.orm import Session, sessionmaker

from .models import Base

# The events table is append-only. These triggers make the database refuse an UPDATE or DELETE,
# so immutability is enforced, not assumed.
EVENT_TRIGGERS = [
    ("CREATE TRIGGER IF NOT EXISTS events_no_update BEFORE UPDATE ON events "
     "BEGIN SELECT RAISE(ABORT, 'events are append-only'); END;"),
    ("CREATE TRIGGER IF NOT EXISTS events_no_delete BEFORE DELETE ON events "
     "BEGIN SELECT RAISE(ABORT, 'events are append-only'); END;"),
]


def make_engine(database_url: str) -> Engine:
    connect_args = {"check_same_thread": False} if database_url.startswith("sqlite") else {}
    engine = create_engine(database_url, connect_args=connect_args)
    if database_url.startswith("sqlite"):
        @event.listens_for(engine, "connect")
        def _fk_on(dbapi_conn, _record):
            dbapi_conn.execute("PRAGMA foreign_keys=ON")
    return engine


def init_db(engine: Engine) -> None:
    Base.metadata.create_all(engine)
    with engine.begin() as conn:
        for ddl in EVENT_TRIGGERS:
            conn.execute(text(ddl))


def make_sessionmaker(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def get_session(request: Request) -> Iterator[Session]:
    session: Session = request.app.state.sessionmaker()
    try:
        yield session
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()