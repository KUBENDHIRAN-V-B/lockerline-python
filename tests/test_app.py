"""Modular routers, docs that list every documented error (and nothing an operation cannot answer), one handler
for every error body — domain refusals, validation, the framework's own 404/405, and the unexpected."""
import logging
import subprocess
import sys
from pathlib import Path

from lockerline.errors import PROBLEM

ROOT = Path(__file__).resolve().parent.parent
PKG = ROOT / "lockerline"

# operation -> (its one tag, every status it can answer)
OPERATIONS = {
    ("get", "/towers/{tower}/doors"): ("doors", {"200", "400", "404", "500"}),
    ("get", "/towers/{tower}/doors/{no}"): ("doors", {"200", "404", "500"}),
    ("post", "/drops"): ("drops", {"201", "400", "409", "422", "500"}),
    ("post", "/pickups"): ("pickups", {"200", "404", "409", "422", "500"}),
    ("get", "/parcels/{parcel_id}"): ("parcels", {"200", "404", "500"}),
    ("get", "/settings"): ("settings", {"200", "500"}),
    ("get", "/healthz"): ("settings", {"200", "500"}),
}


def _examples(response: dict) -> list[dict]:
    content = response["content"][PROBLEM]
    return [content["example"]] if "example" in content else [v["value"] for v in content["examples"].values()]


def test_docs_render_and_list_every_endpoint(client):
    assert client.get("/docs").status_code == 200
    spec = client.get("/openapi.json").json()
    served = {(m, p) for p, ops in spec["paths"].items() for m in ops}
    assert served == set(OPERATIONS)
    assert {t["name"] for t in spec["tags"]} == {"doors", "drops", "pickups", "parcels", "settings"}
    for (method, path), (tag, _) in OPERATIONS.items():
        op = spec["paths"][path][method]
        assert op["summary"], (method, path)
        assert op["tags"] == [tag], (method, path, op["tags"])


def test_every_refusal_is_documented_with_a_problem_example(client):
    spec = client.get("/openapi.json").json()
    drops = spec["paths"]["/drops"]["post"]["responses"]
    assert [e["type"] for e in _examples(drops["400"])] == ["/errors/no-such-flat"]
    assert [e["type"] for e in _examples(drops["409"])] == ["/errors/no-door-free"]
    assert _examples(drops["409"])[0]["free_sizes"] == ["S", "M"]
    validation = _examples(drops["422"])
    assert [e["type"] for e in validation] == ["/errors/validation"] and validation[0]["errors"][0]["field"] == "size_class"
    assert set(drops["422"]["content"]) == {PROBLEM}                  # not FastAPI's stock HTTPValidationError

    pickups = spec["paths"]["/pickups"]["post"]["responses"]
    assert {e["type"] for e in _examples(pickups["404"])} == {"/errors/no-such-code", "/errors/code-expired"}
    assert [e["type"] for e in _examples(pickups["409"])] == ["/errors/code-used"]
    wall = spec["paths"]["/towers/{tower}/doors"]["get"]["responses"]
    assert [e["type"] for e in _examples(wall["400"])] == ["/errors/validation"]
    assert [e["type"] for e in _examples(wall["404"])] == ["/errors/no-such-tower"]
    door = spec["paths"]["/towers/{tower}/doors/{no}"]["get"]["responses"]
    assert {e["type"] for e in _examples(door["404"])} == {"/errors/no-such-door", "/errors/no-such-tower"}


def test_spec_documents_exactly_what_each_operation_can_answer(client):
    spec = client.get("/openapi.json").json()
    for (method, path), (_, statuses) in OPERATIONS.items():
        answers = spec["paths"][path][method]["responses"]
        assert set(answers) == statuses, (method, path, set(answers))
        for status, response in answers.items():
            if status.startswith("2"):
                continue
            for ex in _examples(response):
                assert {"type", "title", "status", "detail"} <= set(ex), (method, path, status, ex)
                assert str(ex["status"]) == status and ex["type"].startswith("/errors/")
    assert _examples(spec["paths"]["/settings"]["get"]["responses"]["500"])[0]["type"] == "/errors/internal"
    schemas = spec["components"]["schemas"]
    assert "HTTPValidationError" not in schemas and "ValidationError" not in schemas


def test_unexpected_exception_is_a_generic_problem_with_request_id(app, client, caplog):
    @app.get("/boom", include_in_schema=False)
    def boom():
        raise RuntimeError("secret detail")

    caplog.set_level(logging.INFO)
    r = client.get("/boom")
    assert r.status_code == 500 and r.headers["content-type"].startswith(PROBLEM)
    body = r.json()
    assert set(body) == {"type", "title", "status", "detail", "request_id"}
    assert body["type"] == "/errors/internal" and "secret detail" not in r.text and "Traceback" not in r.text
    assert len(body["request_id"]) == 12
    lines = [rec.getMessage() for rec in caplog.records]
    assert any(body["request_id"] in line and "unhandled error path=/boom" in line for line in lines), "the error is logged with its id"


def test_framework_errors_are_problem_json_too(client):
    """One handler produces every error body — the framework's own 404 (no such route) and 405 (wrong method) too."""
    r = client.get("/nope")
    assert r.status_code == 404 and r.headers["content-type"].startswith(PROBLEM)
    assert r.json() == {"type": "/errors/not-found", "title": "No such resource", "status": 404, "detail": "Nothing is served at /nope"}
    r = client.delete("/towers/A/doors")
    assert r.status_code == 405 and r.headers["content-type"].startswith(PROBLEM)
    assert r.json()["type"] == "/errors/method-not-allowed" and r.json()["title"] == "Method not allowed"
    assert r.headers["allow"] == "GET"                        # the header the framework's exception carries is kept


def test_services_import_nothing_from_fastapi_even_indirectly():
    """Import every service module in a fresh interpreter: neither FastAPI nor Starlette may end up loaded."""
    modules = sorted(f"lockerline.services.{p.stem}" for p in (PKG / "services").glob("*.py") if p.stem != "__init__")
    assert len(modules) >= 6
    code = (
        "import importlib, sys\n"
        f"for m in {modules!r}: importlib.import_module(m)\n"
        "bad = sorted(k for k in sys.modules if k.split('.')[0] in ('fastapi', 'starlette'))\n"
        "print(bad)\n"
        "sys.exit(1 if bad else 0)\n"
    )
    done = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, check=False)
    assert done.returncode == 0, done.stdout + done.stderr
