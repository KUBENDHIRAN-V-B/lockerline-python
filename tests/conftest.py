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
    values = {"database_url": f"sqlite:///{db}", "seed_dir": str(ROOT / "seed"), "free_window_hours": 48,
              "code_hash_key": "test-key"}
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


@pytest.fixture
def db(app):
    """A fresh session factory for looking at rows the API wrote."""
    return app.state.sessionmaker


def drop(client, size="M", flat="302"):
    r = client.post("/drops", json={"size_class": size, "flat": flat})
    assert r.status_code == 201, r.text
    return r.json()


def fill(client, size, flat="302"):
    """Take every free door of one size."""
    while True:
        r = client.post("/drops", json={"size_class": size, "flat": flat})
        if r.status_code == 409:
            return
        assert r.status_code == 201, r.text