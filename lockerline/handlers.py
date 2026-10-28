"""The one place that turns every error into application/problem+json, and the OpenAPI entries that show
each refusal with an example body."""
import logging
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .errors import (
    HTTP,
    INTERNAL,
    METHOD_NOT_ALLOWED,
    NOT_FOUND,
    PROBLEM,
    VALIDATION_BODY,
    VALIDATION_PARAMS,
    DomainError,
)

log = logging.getLogger("lockerline.errors")


def problem(status: int, type_: str, title: str, detail: str, headers: dict | None = None, **extra) -> JSONResponse:
    body = {"type": type_, "title": title, "status": status, "detail": detail, **extra}
    return JSONResponse(status_code=status, content=body, media_type=PROBLEM, headers=headers)


def example(cls: type[DomainError], detail: str, **extra) -> dict:
    """An OpenAPI `responses` entry for one refusal, so /docs shows how each endpoint can say no."""
    return {
        "description": cls.title,
        "content": {
            PROBLEM: {
                "example": {
                    "type": cls.type,
                    "title": cls.title,
                    "status": cls.status,
                    "detail": detail,
                    **extra,
                }
            }
        },
    }


def responses(*entries: tuple[type[DomainError], str] | tuple[type[DomainError], str, dict]) -> dict:
    """Refusals that share a status are shown as one entry with every example, so none is hidden from /docs."""
    out: dict[int | str, dict] = {}
    for entry in entries:
        cls, detail = entry[0], entry[1]
        extra = entry[2] if len(entry) == 3 else {}
        item = example(cls, detail, **extra)
        if cls.status in out:
            existing = out[cls.status]
            examples = existing["content"][PROBLEM].setdefault("examples", {})
            if "example" in existing["content"][PROBLEM]:
                first = existing["content"][PROBLEM].pop("example")
                examples[first["type"]] = {"value": first}
            examples[cls.type] = {"value": item["content"][PROBLEM]["example"]}
            existing["description"] = existing["description"] + " / " + cls.title
        else:
            out[cls.status] = item
    return out


def _fixed(status: int, type_: str, title: str, detail: str, **extra) -> dict:
    return {
        "description": title,
        "content": {PROBLEM: {"example": {"type": type_, "title": title, "status": status, "detail": detail, **extra}}},
    }


# a body that fails validation (POST /drops, POST /pickups)
VALIDATION_RESPONSE = {422: _fixed(*VALIDATION_BODY, "1 field(s) failed validation", errors=[{"field": "size_class", "message": "Input should be 'S', 'M' or 'L'"}])}
# a query parameter outside its enum (the wall's size and state filters)
FILTER_RESPONSE = {400: _fixed(*VALIDATION_PARAMS, "1 field(s) failed validation", errors=[{"field": "size", "message": "Input should be 'S', 'M' or 'L'"}])}
# every operation can fail unexpectedly; the body is generic
INTERNAL_RESPONSE = {500: _fixed(*INTERNAL, "The request could not be completed", request_id="3f9a1c2b7d4e")}


def install_handlers(app: FastAPI) -> None:
    @app.exception_handler(DomainError)
    async def _domain(_request: Request, exc: DomainError):
        return problem(exc.status, exc.type, exc.title, exc.detail, **exc.extra)

    @app.exception_handler(RequestValidationError)
    async def _validation(_request: Request, exc: RequestValidationError):
        raw = exc.errors()
        errors = [{"field": ".".join(str(p) for p in e["loc"] if p not in ("body", "query", "path")), "message": e["msg"]}
                  for e in raw]
        in_body = any(e["loc"] and e["loc"][0] == "body" for e in raw)
        status, type_, title = VALIDATION_BODY if in_body else VALIDATION_PARAMS
        return problem(status, type_, title, f"{len(errors)} field(s) failed validation", errors=errors)

    @app.exception_handler(StarletteHTTPException)
    async def _framework(request: Request, exc: StarletteHTTPException):
        """Errors raised by the framework itself (no such route, wrong method) get the same shape."""
        headers = dict(exc.headers) if exc.headers else None
        if exc.status_code == 404:
            status, type_, title = NOT_FOUND
            return problem(status, type_, title, f"Nothing is served at {request.url.path}", headers)
        if exc.status_code == 405:
            status, type_, title = METHOD_NOT_ALLOWED
            return problem(status, type_, title, f"{request.method} is not allowed on {request.url.path}", headers)
        try:
            phrase = HTTPStatus(exc.status_code).phrase
        except ValueError:
            phrase = "HTTP error"
        return problem(exc.status_code, HTTP, phrase, str(exc.detail), headers)

    @app.exception_handler(Exception)
    async def _unexpected(request: Request, exc: Exception):
        request_id = getattr(request.state, "request_id", "-")
        log.exception("unhandled error path=%s request_id=%s", request.url.path, request_id)
        status, type_, title = INTERNAL
        return problem(status, type_, title, "The request could not be completed", request_id=request_id)
