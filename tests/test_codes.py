"""Pickup codes are hashed, expire, and may be reused after collection."""
from sqlalchemy import select

from lockerline.models import Parcel
from lockerline.services import drops as drop_service
from tests.conftest import drop


def test_code_can_be_reused_after_previous_parcel_is_collected(client, monkeypatch, db):
    # Force deterministic code issuance so the same code can be reused after collection.
    monkeypatch.setattr(drop_service.secrets, "randbelow", lambda _n: 333333)
    first = drop(client, "S", "101")
    assert client.post("/pickups", json={"code": first["code"]}).status_code == 200
    second = drop(client, "M", "302")
    assert second["code"] == first["code"]
    picked = client.post("/pickups", json={"code": second["code"]})
    assert picked.status_code == 200, picked.text
    assert picked.json()["parcel_id"] == second["parcel_id"]
    refused = client.post("/pickups", json={"code": second["code"]})
    assert (refused.status_code, refused.json()["type"]) == (409, "/errors/code-used")
    with db() as session:
        parcels = list(session.scalars(select(Parcel).order_by(Parcel.id)))
        assert len(parcels) == 2
