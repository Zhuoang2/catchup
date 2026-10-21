"""HTTP application entry point."""

import hashlib
import logging
from contextlib import asynccontextmanager
from pathlib import Path
from urllib.parse import urlsplit

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.exc import OperationalError
from sqlalchemy.orm import sessionmaker
from starlette.concurrency import run_in_threadpool

from catchup.api.settings import router as settings_router
from catchup.api.sources import router as sources_router
from catchup.api.runs import router as runs_router
from catchup.api.digests import router as digests_router
from catchup.api.extension import router as extension_router
from catchup.config import Settings, validate_user_agent_contact
from catchup.db import make_engine, migrate
from catchup.digest.runner import recover_runs
from catchup.errors import register_error_handlers
from catchup.llm.client import ModelClient
from catchup.models import ExtensionToken, utc_now
from catchup.net.feed_cache import FeedCache

logger = logging.getLogger(__name__)


def _lookup_extension_token(factory: sessionmaker, token: str) -> int | None:
    with factory() as session:
        return session.scalar(select(ExtensionToken.id).where(
            ExtensionToken.token_hash == hashlib.sha256(token.encode()).hexdigest()
        ))


def _touch_extension_token(factory: sessionmaker, token_id: int) -> None:
    with factory() as session:
        row = session.get(ExtensionToken, token_id)
        if row is not None:
            row.last_used_at = utc_now()
            session.commit()


def _extension_operation(method: str, path: str) -> bool:
    return (
        (method == "POST" and path in {"/api/sources", "/api/sources/preview", "/api/captures"})
        or (method == "GET" and path in {"/api/captures", "/api/extension/status"})
        or (method == "DELETE" and path.startswith("/api/captures/") and path.count("/") == 3)
    )


def _cross_site_response() -> JSONResponse:
    return JSONResponse(
        status_code=403,
        content={"error": {
            "code": "cross_site_request",
            "message": "This request came from another site and was refused.",
        }},
    )



def _origin_matches_host(origin: str, host: str) -> bool:
    try:
        parsed = urlsplit(origin)
        address = urlsplit(f"//{host}")
        return (
            origin == origin.strip()
            and parsed.scheme in ("http", "https")
            and parsed.hostname is not None
            and parsed.username is None and parsed.password is None
            and not parsed.path and not parsed.query and not parsed.fragment
            and parsed.hostname.lower() == address.hostname.lower()
            and (parsed.port or (443 if parsed.scheme == "https" else 80))
            == (address.port or (443 if parsed.scheme == "https" else 80))
        )
    except (ValueError, AttributeError):
        return False


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
    app.include_router(extension_router)

    # Starlette runs the last registered middleware first; host validation must run before this check.
    @app.middleware("http")
    async def cross_site_writes(request: Request, call_next):
        authorization = request.headers.get("authorization", "")
        if authorization.startswith("Bearer "):
            token_id = await run_in_threadpool(
                _lookup_extension_token, request.app.state.session_factory, authorization[7:]
            )
            if token_id is None:
                return JSONResponse(status_code=401, content={"error": {
                    "code": "invalid_token",
                    "message": "This browser is not connected to CatchUp. Connect it in Settings.",
                }})
            if not _extension_operation(request.method, request.url.path):
                return _cross_site_response()
            request.state.extension_token_id = token_id
            try:
                await run_in_threadpool(_touch_extension_token, request.app.state.session_factory, token_id)
            except OperationalError:
                logger.warning("Could not update browser connection's last use", exc_info=True)
            return await call_next(request)
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            origin = request.headers.get("origin")
            fetch_site = request.headers.get("sec-fetch-site", "").lower()
            if ((origin is not None and not _origin_matches_host(origin, request.headers["host"]))
                    or fetch_site in {"cross-site", "same-site"}):
                return _cross_site_response()
        return await call_next(request)

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
