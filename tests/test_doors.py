"""48 doors seeded once, filters, derived state, both refusals."""
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from lockerline.app import create_app
from lockerline.clock import get_clock
from lockerline.models import Door, Resident
from tests.conftest import drop


def test_seed_is_idempotent(settings, clock):
    for _ in range(2):  # start the app twice against the same database file
        app = create_app(settings)
        app.dependency_overrides[get_clock] = lambda: clock
        with TestClient(app) as c:
            assert c.get("/towers/A/doors").json()["free"] == 48
    with app.state.sessionmaker() as s:
        assert s.scalar(select(func.count()).select_from(Door)) == 48
        assert s.scalar(select(func.count()).select_from(Resident)) == 16


def test_wall_has_48_doors_all_free(client):
    r = client.get("/towers/A/doors")
    assert r.status_code == 200
    body = r.json()
    assert body["tower"] == "A" and body["free"] == 48 and len(body["doors"]) == 48
    sizes = [d["size"] for d in body["doors"]]
    assert sizes.count("S") == 20 and sizes.count("M") == 20 and sizes.count("L") == 8
    assert all(d["state"] == "free" for d in body["doors"])
    # a free door carries exactly no, size and state — no null keys, and a wall item never carries `flat`
    assert all(set(d) == {"no", "size", "state"} for d in body["doors"])


def test_filters(client):
    large = client.get("/towers/A/doors?size=L").json()
    assert len(large["doors"]) == 8 and all(d["size"] == "L" for d in large["doors"])
    assert client.get("/towers/A/doors?state=holding").json()["doors"] == []


def test_free_counts_the_filtered_doors(client):
    """ac_user: 'I filter to large, I see exactly 8 doors and the count says how many of those are free'."""
    drop(client, "L", "302")
    assert client.get("/towers/A/doors").json()["free"] == 47
    large = client.get("/towers/A/doors?size=L").json()
    assert len(large["doors"]) == 8 and large["free"] == 7
    assert client.get("/towers/A/doors?size=S").json()["free"] == 20
    holding = client.get("/towers/A/doors?state=holding").json()
    assert len(holding["doors"]) == 1 and holding["free"] == 0


def test_holding_door_shows_parcel_and_dwell(client, clock):
    d = drop(client)
    clock.advance(hours=3, minutes=30)
    body = client.get("/towers/A/doors?state=holding").json()
    assert len(body["doors"]) == 1
    door = body["doors"][0]
    assert door == {"no": d["door"], "size": "M", "state": "holding", "parcel_id": d["parcel_id"], "dwell_seconds": 12600}


def test_state_is_derived_not_stored():
    assert "state" not in Door.__table__.columns


def test_bad_filter_is_400_validation(client):
    for query, field in (("size=XL", "size"), ("state=open", "state")):
        r = client.get(f"/towers/A/doors?{query}")
        assert r.status_code == 400 and r.headers["content-type"].startswith("application/problem+json")
        assert r.json()["type"] == "/errors/validation"
        assert [e["field"] for e in r.json()["errors"]] == [field]


def test_unknown_door_and_tower(client):
    r = client.get("/towers/A/doors/D99")
    assert r.status_code == 404 and r.json()["type"] == "/errors/no-such-door"
    r = client.get("/towers/Z/doors")
    assert r.status_code == 404 and r.json()["type"] == "/errors/no-such-tower"
    r = client.get("/towers/Z/doors/D01")
    assert r.status_code == 404 and r.json()["type"] == "/errors/no-such-tower"


def test_one_door(client, clock):
    d = drop(client, "S", "104")
    clock.advance(hours=3, minutes=30)
    body = client.get(f"/towers/A/doors/{d['door']}").json()
    assert body == {"no": d["door"], "size": "S", "state": "holding", "parcel_id": d["parcel_id"], "flat": "104", "dwell_seconds": 12600}
    assert client.get("/towers/A/doors/D02").json() == {"no": "D02", "size": "S", "state": "free"}