"""Health answers when the process is up and can reach its database; the Dockerfile is the one the ticket names
and it keeps that contract. (docker build and run themselves are checked by hand: see the README.)"""
import re

from lockerline.db import get_session, make_engine, make_sessionmaker
from lockerline.errors import PROBLEM
from tests.conftest import ROOT


def test_health_is_200_ok(client):
    r = client.get("/healthz")
    assert r.status_code == 200 and r.json() == {"status": "ok"}


def test_health_fails_when_the_database_cannot_be_reached(app, client, tmp_path):
    """/healthz runs SELECT 1 through the session: a database it cannot open is the one 500 handler's answer."""
    unreachable = make_sessionmaker(make_engine(f"sqlite:///{(tmp_path / 'no-such-folder' / 'x.db').as_posix()}"))

    def broken_session():
        session = unreachable()
        try:
            yield session
        finally:
            session.close()

    app.dependency_overrides[get_session] = broken_session
    r = client.get("/healthz")
    assert r.status_code == 500 and r.headers["content-type"].startswith(PROBLEM)
    assert r.json()["type"] == "/errors/internal" and "no-such-folder" not in r.text


def test_dockerfile_matches_the_contract():
    text = (ROOT / "Dockerfile").read_text(encoding="utf-8")
    assert text.startswith("# The app as an image.") and "FROM python:3.12-slim" in text
    assert "RUN pip install --no-cache-dir -r requirements.lock" in text
    assert re.search(r"ENV HOST=0\.0\.0\.0 \\\n\s+PORT=8080 \\", text)
    assert 'CMD ["sh", "-c", "exec uvicorn lockerline.app:app --host \\"$HOST\\" --port \\"$PORT\\""]' in text
    assert "EXPOSE 8080" in text
