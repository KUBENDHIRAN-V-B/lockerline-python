"""Append-only parcel history tests."""
import ast
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import delete, func, select, update
from sqlalchemy.exc import DBAPIError

from lockerline.models import Door, Event, Parcel
from lockerline.services.events import record as real_record
from tests.conftest import drop

PKG = Path(__file__).resolve().parent.parent / "lockerline"


def test_drop_writes_exactly_two_events(client, db):
    drop(client)
    with db() as s:
        kinds = list(s.scalars(select(Event.kind).order_by(Event.id)))
    assert kinds == ["dropped", "code_issued"]


def test_failed_drop_writes_no_event(client, db):
    """The failure comes on the second event (code_issued), after `dropped` was written in the same transaction:
    the rollback must take the `dropped` row, the parcel and the held door with it."""
    written = []

    def fail_on_code_issued(session, tower_id, parcel_id, kind, at, data=None):
        if kind == "code_issued":
            raise RuntimeError("boom")
        written.append(real_record(session, tower_id, parcel_id, kind, at, data))
        return written[-1]

    with patch("lockerline.services.drops.events.record", side_effect=fail_on_code_issued):
        r = client.post("/drops", json={"size_class": "M", "flat": "302"})
    assert r.status_code == 500 and len(written) == 1          # `dropped` was inserted before the failure
    with db() as s:
        assert s.scalar(select(func.count()).select_from(Event)) == 0
        assert s.scalar(select(func.count()).select_from(Parcel)) == 0
        assert s.scalar(select(func.count()).select_from(Door).where(Door.current_parcel_id.is_not(None))) == 0


def test_events_are_inserted_with_core_never_through_the_orm(client):
    """S18: the event row is a Core INSERT that returns the new id; no ORM Event object is added to a session,
    so no code path could later change one."""
    tree = ast.parse((PKG / "services" / "events.py").read_text(encoding="utf-8"))
    calls = {n.func.id if isinstance(n.func, ast.Name) else n.func.attr for n in ast.walk(tree) if isinstance(n, ast.Call)}
    assert "insert" in calls and "returning" in calls and "add" not in calls and "Event" not in calls
    assert isinstance(drop(client)["parcel_id"], str)


def test_events_are_append_only(client, db):
    drop(client)
    with db() as s, pytest.raises(DBAPIError):
        s.execute(update(Event).values(kind="edited"))
        s.commit()
    with db() as s, pytest.raises(DBAPIError):
        s.execute(delete(Event))
        s.commit()
    with db() as s:
        assert s.scalar(select(func.count()).select_from(Event)) == 2


def test_parcel_history_is_ordered_and_carries_no_code(client, clock):
    body = drop(client)
    clock.advance(hours=44)
    client.post("/pickups", json={"code": body["code"]})
    r = client.get(f"/parcels/{body['parcel_id']}")
    assert r.status_code == 200
    events = r.json()["events"]
    assert [e["kind"] for e in events] == ["dropped", "code_issued", "opened"]
    assert events[0]["door"] == body["door"] and events[1]["expires_at"] == body["expires_at"]
    assert events[2]["dwell_seconds"] == 44 * 3600
    # each event carries only the facts of its kind — declared fields, no null keys
    assert [set(e) for e in events] == [
        {"at", "kind", "door"}, {"at", "kind", "expires_at"},
        {"at", "kind", "door", "dwell_seconds"},
    ]
    assert body["code"] not in r.text
    assert [e["at"] for e in events] == sorted(e["at"] for e in events)
    assert events[0]["at"] == "2026-09-25T13:10:00Z", "event times are the clock, in UTC with a Z, never shifted to local time"


def test_unknown_parcel_is_404(client):
    r = client.get("/parcels/P999")
    assert r.status_code == 404 and r.json()["type"] == "/errors/no-such-parcel"
