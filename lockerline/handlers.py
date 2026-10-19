"""The one place that turns every error into application/problem+json.

Services raise the exceptions in errors.py; routes never build error responses; the handlers below map them.
"""
from http import HTTPStatus

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from .errors import (
    HTTP,
    METHOD_NOT_ALLOWED,
    NOT_FOUND,
    PROBLEM,
    VALIDATION_BODY,
    VALIDATION_PARAMS,
    DomainError,
)


def problem(status: int, type_: str, title: str, detail: str, headers: dict | None = None, **extra) -> JSONResponse:
    body = {"type": type_, "title": title, "status": status, "detail": detail, **extra}
    return JSONResponse(status_code=status, content=body, media_type=PROBLEM, headers=headers)


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