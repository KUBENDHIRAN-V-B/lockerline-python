"""Pickup collects a parcel, releases the door and stamps dwell atomically."""
from sqlalchemy import select, text

from lockerline.models import Door, Parcel
from tests.conftest import drop


def test_pickup_collects_and_stamps_dwell(client, clock, db):
    dropped = drop(client)
    clock.advance(days=1, hours=20, minutes=2)

    response = client.post("/pickups", json={"code": dropped["code"]})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body == {
        "parcel_id": dropped["parcel_id"],
        "door": dropped["door"],
        "opened_at": "2026-09-27T09:12:00Z",
        "dwell_seconds": 158520,
    }

    with db() as session:
        parcel = session.scalar(select(Parcel).where(Parcel.id == int(dropped["parcel_id"][1:])))
        door = session.scalar(select(Door).where(Door.no == dropped["door"]))
        assert parcel.state == "collected"
        assert parcel.collected_at is not None
        assert parcel.dwell_seconds == 158520
        assert parcel.code_used_at is not None
        assert door.current_parcel_id is None


def test_failed_door_release_rolls_back_collection(client, db):
    dropped = drop(client)
    with db() as session:
        session.execute(text("""CREATE TRIGGER fail_door_release BEFORE UPDATE OF current_parcel_id ON doors WHEN NEW.current_parcel_id IS NULL BEGIN SELECT RAISE(ABORT, 'forced door failure'); END"""))
        session.commit()

    response = client.post("/pickups", json={"code": dropped["code"]})
    assert response.status_code == 500
    with db() as session:
        parcel = session.scalar(select(Parcel).where(Parcel.id == int(dropped["parcel_id"][1:])))
        door = session.scalar(select(Door).where(Door.no == dropped["door"]))
        assert parcel.state == "holding"
        assert parcel.collected_at is None
        assert parcel.code_used_at is None
        assert parcel.dwell_seconds is None
        assert door.current_parcel_id == parcel.id


def test_reused_code_refuses_second_pickup(client):
    code = drop(client)["code"]
    first = client.post("/pickups", json={"code": code})
    assert first.status_code == 200
    second = client.post("/pickups", json={"code": code})
    assert (second.status_code, second.json()["type"]) == (409, "/errors/code-used")
