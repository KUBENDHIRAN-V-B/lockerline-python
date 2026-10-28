"""A parametrised table of the wall's refusal rules."""
import csv
import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from lockerline.app import create_app
from lockerline.clock import get_clock
from tests.conftest import fill, make_settings

ROWS = list(csv.DictReader((Path(__file__).parent / "rules.csv").open(encoding="utf-8")))


def run_case(client, clock, row):
    last_code = None
    for step in filter(None, row["setup"].split(";")):
        verb, *args = step.split()
        if verb == "fill":
            fill(client, args[0])
        elif verb == "drop":
            last_code = client.post("/drops", json={"size_class": "M", "flat": "302"}).json()["code"]
        elif verb == "pickup":
            client.post("/pickups", json={"code": last_code})
        elif verb == "advance":
            clock.advance(hours=int(args[0]))

    verb, *args = row["action"].split()
    if verb == "drop":
        return client.post("/drops", json={"size_class": args[0], "flat": args[1]})
    return client.post("/pickups", json={"code": args[0] if args else last_code})


@pytest.mark.parametrize("window", [48, 24])
@pytest.mark.parametrize("row", ROWS, ids=[r["case"] for r in ROWS])
def test_rule_table(tmp_path, clock, row, window):
    app = create_app(make_settings(tmp_path, free_window_hours=window))
    app.dependency_overrides[get_clock] = lambda: clock
    with TestClient(app, raise_server_exceptions=False) as client:
        r = run_case(client, clock, row)
    assert r.status_code == int(row[f"status_{window}"]), (row["case"], window, r.text)
    expected_type = row[f"type_{window}"]
    if expected_type:
        assert r.json()["type"] == expected_type


def test_only_window_rows_move_when_the_window_changes():
    moved = {r["case"] for r in ROWS if r["status_48"] != r["status_24"]}
    assert moved and all(r["tag"] == "window" for r in ROWS if r["case"] in moved)


def test_every_refusal_type_has_a_row():
    types = {r["type_48"] for r in ROWS} | {r["type_24"] for r in ROWS}
    assert types >= {
        "/errors/no-door-free", "/errors/no-such-flat", "/errors/validation",
        "/errors/code-used", "/errors/no-such-code", "/errors/code-expired",
    }


def test_settings_endpoint_shows_the_live_window(tmp_path, clock):
    app = create_app(make_settings(tmp_path, free_window_hours=24))
    with TestClient(app, raise_server_exceptions=False) as client:
        assert client.get("/settings").json() == {"free_window_hours": 24, "sizes": ["S", "M", "L"]}


def test_the_rule_book_shows_the_rows_the_tests_run():
    """The Rule book screen renders a copy of tests/rules.csv; the copy must equal the
    file: same cases, tags, setup, action and expected status/type at both windows, in the same order."""
    source = (Path(__file__).resolve().parent.parent / "lockerline" / "static" / "app.js").read_text(encoding="utf-8")
    block = re.search(r"var RULES = (\[.*?\n  \]);", source, re.DOTALL)
    assert block, "app.js declares var RULES = [...]"
    shown = json.loads(block.group(1))
    columns = ["case", "tag", "setup", "action", "status_48", "type_48", "status_24", "type_24"]
    assert shown == [[row[c] for c in columns] for row in ROWS]
