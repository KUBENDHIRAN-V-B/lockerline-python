"""The clock is a dependency: every time-based rule reads it, so a test can move time instead of waiting."""
from datetime import datetime, timedelta, timezone


class Clock:
    def now(self) -> datetime:  # pragma: no cover - interface
        raise NotImplementedError


class SystemClock(Clock):
    def now(self) -> datetime:
        return datetime.now(timezone.utc)


class FixedClock(Clock):
    """A clock a test controls. `advance` moves it; `set` pins it."""

    def __init__(self, at: datetime):
        self._at = at

    def now(self) -> datetime:
        return self._at

    def set(self, at: datetime) -> None:
        self._at = at

    def advance(self, **delta) -> datetime:
        self._at = self._at + timedelta(**delta)
        return self._at


def get_clock() -> Clock:
    return SystemClock()


def as_utc(dt: datetime) -> datetime:
    """SQLite hands naive datetimes back; everything the app stores is UTC."""
    return dt if dt.tzinfo is not None else dt.replace(tzinfo=timezone.utc)