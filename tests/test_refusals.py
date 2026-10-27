
import ast
from pathlib import Path

from tests.conftest import drop, fill

ROUTERS = Path(__file__).resolve().parent.parent / "lockerline" / "routers"

FORBIDDEN = {
    "HTTPException",
    "JSONResponse",
    "ORJSONResponse",
    "PlainTextResponse",
}


def test_no_door_free(client):
    fill(client, "L")
    r = client.post(
        "/drops",
        json={"size_class": "L", "flat": "302"},
    )
    assert (r.status_code, r.json()["type"]) == (
        409,
        "/errors/no-door-free",
    )


def test_code_used(client):
    code = drop(client)["code"]
    first = client.post("/pickups", json={"code": code})
    assert first.status_code == 200
    second = client.post("/pickups", json={"code": code})
    assert (second.status_code, second.json()["type"]) == (409, "/errors/code-used")


def test_no_such_code(client):
    r = client.post("/pickups", json={"code": "000000"})
    assert (r.status_code, r.json()["type"]) == (
        404,
        "/errors/no-such-code",
    )


def test_code_expired_shares_the_status_but_not_the_type(client, clock):
    code = drop(client)["code"]
    clock.advance(hours=49)

    r = client.post("/pickups", json={"code": code})

    assert (r.status_code, r.json()["type"]) == (
        404,
        "/errors/code-expired",
    )


def test_problem_body_has_only_the_documented_fields(client):
    r = client.post("/pickups", json={"code": "000000"})

    assert set(r.json()) == {"type", "title", "status", "detail"}
    assert r.json()["status"] == 404 and "Traceback" not in r.text

    fill(client, "L")
    r = client.post(
        "/drops",
        json={"size_class": "L", "flat": "302"},
    )
    body = r.json()

    assert set(body) == {
        "type", "title", "status", "detail", "free_sizes"
    }, "the one field the ticket names"
    assert (
        body["status"] == 409
        and body["free_sizes"] == ["S", "M"]
        and "Traceback" not in r.text
    )


def test_routes_never_build_error_responses():
    """No route raises HTTPException or builds a response body of its own — by bare name or as an attribute
    (`fastapi.HTTPException`, `responses.JSONResponse`)."""
    for path in ROUTERS.glob("*.py"):
        tree = ast.parse(path.read_text(encoding="utf-8"))
        names = {
            n.id
            for n in ast.walk(tree)
            if isinstance(n, ast.Name)
        }
        attrs = {
            n.attr
            for n in ast.walk(tree)
            if isinstance(n, ast.Attribute)
        }
        imported = {
            a.asname or a.name
            for n in ast.walk(tree)
            if isinstance(n, ast.ImportFrom)
            for a in n.names
        }

        assert not FORBIDDEN & (names | attrs | imported), (
            path.name,
            FORBIDDEN & (names | attrs | imported),
        )


def test_the_route_check_catches_both_spellings():
    """The check above is not vacuous: it flags a bare name, an attribute call and a JSONResponse."""
    for source in (
        "from fastapi import HTTPException\nraise HTTPException(404)",
        "import fastapi\nraise fastapi.HTTPException(404)",
        "from fastapi.responses import JSONResponse\ndef f():\n    return JSONResponse({})",
    ):
        tree = ast.parse(source)
        found = (
            {
                n.id
                for n in ast.walk(tree)
                if isinstance(n, ast.Name)
            }
            | {
                n.attr
                for n in ast.walk(tree)
                if isinstance(n, ast.Attribute)
            }
            | {
                a.asname or a.name
                for n in ast.walk(tree)
                if isinstance(n, ast.ImportFrom)
                for a in n.names
            }
        )

        assert FORBIDDEN & found, source
