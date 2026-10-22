"""FastAPI application factory."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .db import init_db, make_engine, make_sessionmaker
from .handlers import install_handlers
from .routers import doors
from .routers import drops as drops_router
from .routers import parcels as parcels_router
from .routers import pickups as pickups_router
from .services.seed import seed
from .settings import Settings

STATIC = Path(__file__).parent / "static"


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
    )

    app.state.settings = settings
    app.state.engine = engine
    app.state.sessionmaker = make_sessionmaker(engine)

    # Register the shared domain and HTTP exception handlers.
    install_handlers(app)

    # Register API routers, including Ticket 4 pickup validation.
    for router in (
        doors.router,
        drops_router.router,
        parcels_router.router,
        pickups_router.router,
    ):
        app.include_router(router)

    # Serve frontend assets.
    app.mount(
        "/static",
        StaticFiles(directory=STATIC),
        name="static",
    )

    @app.get("/", include_in_schema=False)
    def index():
        return FileResponse(STATIC / "index.html")

    return app


app = create_app()
