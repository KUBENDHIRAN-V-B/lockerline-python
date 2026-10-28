"""Create the API: one error handler, a request id on every request."""
import copy
import json
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.openapi.utils import get_openapi
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .db import init_db, make_engine, make_sessionmaker
from .handlers import (
    FILTER_RESPONSE,
    INTERNAL_RESPONSE,
    VALIDATION_RESPONSE,
    install_handlers,
)
from .routers import doors
from .routers import drops as drops_router
from .routers import parcels as parcels_router
from .routers import pickups as pickups_router
from .services.seed import seed
from .settings import Settings

STATIC = Path(__file__).parent / "static"
TAGS = [
    {"name": "doors", "description": "The wall — 48 doors and their derived state"},
    {"name": "drops", "description": "A courier books a door"},
    {"name": "pickups", "description": "A resident opens a door with a code"},
    {"name": "parcels", "description": "One parcel and its append-only history"},
    {"name": "settings", "description": "The rules in force, and health"},
]
DESCRIPTION = "A bank of 48 parcel lockers: couriers drop, residents collect with a code that expires."


def honest_openapi(app: FastAPI):
    """The spec documents exactly what each operation can answer: FastAPI's stock 422 goes where there is no
    body (a bad query value is the 400 validation problem), the 422 of a body is the app's own problem+json, and every
    operation can answer the generic 500."""

    def openapi() -> dict:
        if app.openapi_schema:
            return app.openapi_schema
        schema = get_openapi(
            title=app.title,
            version=app.version,
            description=app.description,
            routes=app.routes,
            tags=app.openapi_tags,
        )
        for ops in schema["paths"].values():
            for op in ops.values():
                answers = op.setdefault("responses", {})
                if "requestBody" in op:
                    answers["422"] = copy.deepcopy(VALIDATION_RESPONSE[422])
                else:
                    answers.pop("422", None)
                if any(p.get("in") == "query" for p in op.get("parameters", [])) and "400" not in answers:
                    answers["400"] = copy.deepcopy(FILTER_RESPONSE[400])
                answers["500"] = copy.deepcopy(INTERNAL_RESPONSE[500])
        components = schema.get("components", {}).get("schemas", {})
        for name in ("HTTPValidationError", "ValidationError"):       # the first references the second
            others = {k: v for k, v in components.items() if k != name}
            if f"#/components/schemas/{name}" not in json.dumps([schema["paths"], others]):
                components.pop(name, None)
        app.openapi_schema = schema
        return schema

    return openapi


def create_app(settings: Settings | None = None) -> FastAPI:
    """Create and configure the LockerLine application."""
    settings = settings or Settings()
    engine = make_engine(settings.database_url)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        """Initialize the database and seed initial data."""
        init_db(engine)
        with app.state.sessionmaker() as session:
            seed(session, settings.seed_dir)
        yield
        engine.dispose()

    app = FastAPI(
        title="LockerLine",
        version="0.3.0",
        lifespan=lifespan,
        openapi_tags=TAGS,
        description=DESCRIPTION,
    )
    app.state.settings = settings
    app.state.engine = engine
    app.state.sessionmaker = make_sessionmaker(engine)

    @app.middleware("http")
    async def request_id_and_log(request: Request, call_next):
        request.state.request_id = uuid.uuid4().hex[:12]
        response = await call_next(request)
        return response

    install_handlers(app)
    for router in (doors.router, drops_router.router, parcels_router.router, pickups_router.router):
        app.include_router(router)
    app.mount("/static", StaticFiles(directory=STATIC), name="static")

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(STATIC / "index.html")

    app.openapi = honest_openapi(app)
    return app


app = create_app()
