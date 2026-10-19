"""48 doors seeded once, filters, derived state, both refusals."""
from fastapi.testclient import TestClient
from sqlalchemy import func, select

from lockerline.app import create_app
from lockerline.clock import get_clock
from lockerline.models import Door, Resident


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


def test_twenty_small_twenty_medium_eight_large_all_free(client):
    r = client.get("/towers/A/doors")
    body = r.json()
    sizes = [d["size"] for d in body["doors"]]
    assert sizes.count("S") == 20 and sizes.count("M") == 20 and sizes.count("L") == 8
    assert all(d["state"] == "free" for d in body["doors"])


def test_exact_three_keys(client):
    # and a `free door carries exactly no, size and state` — no null keys, and a wall item never carries `flat`
    r = client.get("/towers/A/doors")
    body = r.json()
    assert all(set(d) == {"no", "size", "state"} for d in body["doors"])


def test_filters(client):
    large = client.get("/towers/A/doors?size=L").json()
    assert len(large["doors"]) == 8 and all(d["size"] == "L" for d in large["doors"])
    assert client.get("/towers/A/doors?state=holding").json()["doors"] == []



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


def test_door_in_unknown_tower(client):
    r = client.get("/towers/Z/doors/D01")
    assert r.status_code == 404 and r.json()["type"] == "/errors/no-such-tower"