"""HTTP application entry point."""

from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy.orm import sessionmaker

from catchup.api.settings import router as settings_router
from catchup.api.sources import router as sources_router
from catchup.api.runs import router as runs_router
from catchup.api.digests import router as digests_router
from catchup.config import Settings, validate_user_agent_contact
from catchup.db import make_engine, migrate
from catchup.digest.runner import recover_runs
from catchup.errors import register_error_handlers
from catchup.llm.client import ModelClient
from catchup.net.feed_cache import FeedCache


def create_app(settings: Settings | None = None, dist_dir: Path | None = None) -> FastAPI:
    instance_settings = settings or Settings.from_env()
    validate_user_agent_contact(instance_settings.user_agent_contact)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        engine = make_engine(instance_settings.data_dir)
        try:
            migrate(engine)
            app.state.engine = engine
            app.state.session_factory = sessionmaker(engine, expire_on_commit=False)
            recover_runs(app.state.session_factory)
            yield
        finally:
            engine.dispose()

    app = FastAPI(lifespan=lifespan)
    app.state.settings = instance_settings
    app.state.feed_cache = FeedCache()
    app.state.model_client_factory = ModelClient
    register_error_handlers(app)
    app.include_router(settings_router)
    app.include_router(sources_router)
    app.include_router(runs_router)
    app.include_router(digests_router)

    @app.middleware("http")
    async def allowed_host(request: Request, call_next):
        raw_host = request.headers.get("host", "")
        try:
            parsed = urlsplit(f"//{raw_host}")
            hostname = parsed.hostname
            port = parsed.port
            valid = (
                hostname is not None
                and sum(key.lower() == b"host" for key, _ in request.scope["headers"]) == 1
                and raw_host == raw_host.strip()
                and not raw_host.endswith(":")
                and not parsed.path and not parsed.query and not parsed.fragment
                and parsed.username is None and parsed.password is None
                and (port is None or 1 <= port <= 65535)
                and hostname.lower() in {
                    host[1:-1] if host.startswith("[") and host.endswith("]") else host
                    for host in instance_settings.allowed_hosts
                }
            )
        except ValueError:
            valid = False
        if not valid:
            return JSONResponse(
                status_code=400,
                content={"error": {"code": "invalid_host", "message": "Host is not allowed."}},
            )
        return await call_next(request)

    @app.get("/api/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    frontend_dist = (
        dist_dir if dist_dir is not None else
        instance_settings.frontend_dist if instance_settings.frontend_dist is not None else
        Path(__file__).resolve().parents[3] / "frontend" / "dist"
    )
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
