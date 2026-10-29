"""Rows proven in-process: the plain code never reaches a log line, log lines carry public ids, settings
really do come from an env-file, and the files that hand the container over say what the ticket asks.
The container itself (volume, env-file restart, docker logs, docker diff) was run for real — see the README."""
import logging
import re
from pathlib import Path

from fastapi.testclient import TestClient

from lockerline.app import create_app
from lockerline.clock import get_clock
from lockerline.settings import Settings
from tests.conftest import ROOT, drop


def test_no_log_line_ever_contains_the_code(client, caplog):
    caplog.set_level(logging.INFO)
    body = drop(client)
    client.post("/pickups", json={"code": body["code"]})
    client.post("/pickups", json={"code": body["code"]})   # the refusal path logs too
    client.get(f"/parcels/{body['parcel_id']}")
    lines = [r.getMessage() for r in caplog.records]
    assert any("event kind=dropped" in line for line in lines)
    assert any("request method=POST path=/drops" in line for line in lines)
    assert all(body["code"] not in line for line in lines)


def test_log_lines_carry_public_ids_one_line_per_request_and_event(client, caplog):
    caplog.set_level(logging.INFO)
    body = drop(client)
    client.post("/pickups", json={"code": body["code"]})
    lines = [r.getMessage() for r in caplog.records if r.name.startswith("lockerline")]
    events = [line for line in lines if line.startswith("event ")]
    assert events == [
        f"event kind=dropped parcel_id={body['parcel_id']} door={body['door']}",
        f"event kind=code_issued parcel_id={body['parcel_id']} expires_at={body['expires_at']}",
        f"event kind=opened parcel_id={body['parcel_id']} door={body['door']} dwell_seconds=0",
    ]
    requests = [line for line in lines if line.startswith("request ")]
    assert [line.split(" request_id=")[0] for line in requests] == [
        "request method=POST path=/drops status=201",
        "request method=POST path=/pickups status=200",
    ]
    assert not any(re.search(r"(parcel_id|tower_id|door_id)=\d", line) for line in lines), "no database integer ids"


def test_settings_come_from_an_env_file(tmp_path, clock):
    env = tmp_path / ".env"
    db = (tmp_path / "env.db").as_posix()
    env.write_text(
        f"DATABASE_URL=sqlite:///{db}\nFREE_WINDOW_HOURS=24\nCODE_HASH_KEY=from-env-file\nSEED_DIR={ROOT / 'seed'}\n"
        "HOST=127.0.0.2\nPORT=9090\n",
        encoding="utf-8",
    )
    settings = Settings(_env_file=env)
    assert settings.free_window_hours == 24 and settings.code_hash_key == "from-env-file"
    assert (settings.host, settings.port) == ("127.0.0.2", 9090)
    app = create_app(settings)
    app.dependency_overrides[get_clock] = lambda: clock
    with TestClient(app) as c:
        assert c.get("/settings").json()["free_window_hours"] == 24
        assert c.get("/towers/A/doors").json()["free"] == 48
    assert Path(db).exists()


def test_env_example_lists_every_setting_the_app_reads():
    keys = {
        line.split("=", 1)[0]
        for line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines()
        if line and not line.startswith("#")
    }
    assert keys == {name.upper() for name in Settings.model_fields}


def test_dockerignore_keeps_tests_databases_and_caches_out_of_the_image():
    ignore = (ROOT / ".dockerignore").read_text(encoding="utf-8").split()
    assert ignore == [
        ".git", ".venv", "venv", "**/__pycache__", "**/*.pyc", "**/.pytest_cache",
        ".ruff_cache", "tests", "sandbox", "**/*.db", ".env", "build", "dist", "*.egg-info",
    ]


def test_readme_hands_the_container_over():
    readme = (ROOT / "README.md").read_text(encoding="utf-8")
    assert "docker build -t lockerline ." in readme
    assert re.search(r"docker run [^\n]*-v lockerline-data:/data [^\n]*--env-file \.env lockerline", readme)
    curls = [line for line in readme.splitlines() if line.lstrip().startswith("curl ")]
    assert len(curls) >= 6 and all("http://localhost:8080/" in line for line in curls), curls
    for path in ("/drops", "/pickups", "/parcels/"):
        assert any(path in line for line in curls), path
    assert "## Verified on this build" in readme
