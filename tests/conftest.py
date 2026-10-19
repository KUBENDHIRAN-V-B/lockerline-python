"""Every test gets its own SQLite file, a fixed clock it can move, and the seed files from the repo."""
from datetime import datetime, timezone
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from lockerline.app import create_app
from lockerline.clock import FixedClock, get_clock
from lockerline.settings import Settings

ROOT = Path(__file__).resolve().parent.parent
T0 = datetime(2026, 9, 25, 13, 10, tzinfo=timezone.utc)


def make_settings(tmp_path: Path, **overrides) -> Settings:
    db = (tmp_path / "lockerline-test.db").as_posix()
    values = {"database_url": f"sqlite:///{db}", "seed_dir": str(ROOT / "seed"), "free_window_hours": 48}
    values.update(overrides)
    return Settings(_env_file=None, **values)


@pytest.fixture
def clock() -> FixedClock:
    return FixedClock(T0)


@pytest.fixture
def settings(tmp_path) -> Settings:
    return make_settings(tmp_path)


@pytest.fixture
def app(settings, clock):
    app = create_app(settings)
    app.dependency_overrides[get_clock] = lambda: clock
    return app


@pytest.fixture
def client(app):
    with TestClient(app, raise_server_exceptions=False) as c:
        yield c

        