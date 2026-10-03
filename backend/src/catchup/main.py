"""HTTP application entry point."""

from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from sqlalchemy.orm import sessionmaker

from catchup.config import Settings
from catchup.db import make_engine, migrate


class AppError(Exception):
    def __init__(self, code: str, message: str, status_code: int = 400, **details: object):
        self.code = code
        self.message = message
        self.status_code = status_code
        self.details = details


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

    @app.exception_handler(AppError)
    def app_error_handler(_request: Request, exc: AppError) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": exc.code, "message": exc.message, **exc.details}},
        )

    @app.exception_handler(StarletteHTTPException)
    def http_error_handler(_request: Request, exc: StarletteHTTPException) -> JSONResponse:
        return JSONResponse(
            status_code=exc.status_code,
            content={"error": {"code": "not_found" if exc.status_code == 404 else "http_error", "message": str(exc.detail)}},
        )

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
