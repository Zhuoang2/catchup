"""HTTP application entry point."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import sessionmaker

from catchup.api.settings import router as settings_router
from catchup.config import Settings
from catchup.db import make_engine, migrate
from catchup.errors import register_error_handlers


def create_app(settings: Settings | None = None, dist_dir: Path | None = None) -> FastAPI:
    instance_settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        engine = make_engine(instance_settings.data_dir)
        try:
            migrate(engine)
            app.state.engine = engine
            app.state.session_factory = sessionmaker(engine, expire_on_commit=False)
            yield
        finally:
            engine.dispose()

    app = FastAPI(lifespan=lifespan)
    app.state.settings = instance_settings
    register_error_handlers(app)
    app.include_router(settings_router)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    frontend_dist = dist_dir if dist_dir is not None else Path(__file__).resolve().parents[3] / "frontend" / "dist"
    if (frontend_dist / "index.html").is_file():
        assets = frontend_dist / "assets"
        if assets.is_dir():
            app.mount("/assets", StaticFiles(directory=assets), name="assets")

        @app.middleware("http")
        async def spa_fallback(request: Request, call_next):
            response = await call_next(request)
            path = request.url.path
            if response.status_code != 404 or path == "/api" or path.startswith(("/api/", "/assets/")):
                return response
            candidate = (frontend_dist / path.lstrip("/")).resolve()
            if candidate.is_relative_to(frontend_dist.resolve()) and candidate.is_file():
                return FileResponse(candidate)
            return FileResponse(frontend_dist / "index.html")

    return app


app = create_app()
