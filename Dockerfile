# syntax=docker/dockerfile:1
FROM --platform=$BUILDPLATFORM node:24-slim AS frontend
WORKDIR /app
COPY frontend/package*.json ./
RUN npm ci
COPY frontend/ ./
RUN npm run build

FROM ghcr.io/astral-sh/uv:python3.12-trixie-slim AS builder
ENV UV_COMPILE_BYTECODE=1 UV_LINK_MODE=copy UV_NO_DEV=1 UV_PYTHON_DOWNLOADS=0
WORKDIR /app
RUN --mount=type=cache,target=/root/.cache/uv \
    --mount=type=bind,source=backend/pyproject.toml,target=/app/pyproject.toml \
    --mount=type=bind,source=backend/uv.lock,target=/app/uv.lock \
    uv sync --locked --no-install-project --no-editable
COPY backend/ ./
RUN --mount=type=cache,target=/root/.cache/uv uv sync --locked --no-editable

FROM python:3.12-slim-trixie
RUN groupadd --gid 999 catchup && useradd --uid 999 --gid 999 --no-create-home catchup \
    && mkdir /data && chown 999:999 /data
COPY --from=builder /app/.venv /app/.venv
COPY --from=frontend /app/dist /app/frontend
ENV PATH="/app/.venv/bin:$PATH" PYTHONUNBUFFERED=1 \
    CATCHUP_DATA_DIR=/data CATCHUP_FRONTEND_DIST=/app/frontend
VOLUME /data
EXPOSE 8000
USER catchup
HEALTHCHECK --interval=30s --timeout=5s --start-period=20s \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/api/health', timeout=3).close()"
CMD ["catchup", "serve", "--host", "0.0.0.0", "--port", "8000"]
