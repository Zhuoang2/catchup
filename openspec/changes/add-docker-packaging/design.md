# Design

Status: Proposal 2 chosen by the user on 2026-10-04 (self-contained package with a slim image).

## Context

See `proposal.md` for motivation. Today CatchUp runs only from a source checkout:
- `main.py:83` finds `frontend/dist` via `Path(__file__).parents[3]`.
- `db.py:34` finds `backend/alembic` via `parents[2]`.
- `pyproject.toml:31-32` packages only `src/catchup`, so migrations are not in a wheel.

The data directory defaults to `./data`. Configuration is environment-only, and the allowed-hosts check ignores the port. CI runs tests and builds only, using `checkout@v4`, `setup-uv@v6`, `setup-node@v4`, and Node 20. The working copy contains gitignored secrets and course material that a Docker build context would include by default. External facts come from `research.md` ("External facts").

## Goals / Non-Goals

**Goals:**
- `docker compose up` gives a working, local-only CatchUp with persistent data.
- The backend package runs outside the source tree.
- CI proves the image works on every PR; `main` and version tags publish multi-architecture images to GHCR.

**Non-Goals:**
- A hosted instance or authentication (D-011).
- Publishing the wheel to PyPI or GitHub Releases. The package becomes ready for it, but that is not done here.
- Creating the first `vX.Y.Z` tag. The user decides when to cut a release.
- Making the `docker` CI job a required check (can be added to branch protection later).

## Decisions

### D1. Self-contained package (chosen over mirroring the source tree)
- Migrations move from `backend/alembic/` to `backend/src/catchup/migrations/` (`env.py`, `script.py.mako`, `versions/`), with history preserved via `git mv`. `migrate()` points Alembic at `Path(__file__).parent / "migrations"`. Hatch includes all files under the package, so the wheel carries them.
- `CATCHUP_FRONTEND_DIST` (new `Settings.frontend_dist: Path | None`). Precedence:
  1. the `create_app(dist_dir=…)` argument (tests)
  2. the setting
  3. the current source-tree fallback (`parents[3]/frontend/dist`)
- A missing or invalid directory keeps today's behavior: the API runs and no frontend is served.
- `catchup` console script (`[project.scripts] catchup = "catchup.cli:main"`). `catchup serve [--host 127.0.0.1] [--port 8000]` calls `uvicorn.run(create_app(), host=…, port=…)`. The default host is loopback; the image passes `--host 0.0.0.0`. The module-level `app` in `main.py` stays for `uvicorn catchup.main:app`.
- **Alternative considered (Proposal 1):** an image that mirrors the source tree under `/app` so the `parents[]` lookups resolve unchanged, with no code changes. It was rejected because the lookups stay fragile, the image carries the source and an editable install, and CatchUp still could not be installed as a package. It remains the fallback if the move proves troublesome.

### D2. Dockerfile (multi-stage, repo root)
1. **`frontend` stage:** `FROM --platform=$BUILDPLATFORM node:24-slim`. It runs `npm ci && npm run build` using `frontend/package*.json` and sources. The output is architecture-independent, so it runs natively even when building arm64 under emulation.
2. **`builder` stage:** `FROM ghcr.io/astral-sh/uv:python3.12-trixie-slim`, with `UV_COMPILE_BYTECODE=1`, `UV_LINK_MODE=copy`, `UV_NO_DEV=1`, and `UV_PYTHON_DOWNLOADS=0`. It works in `/app` in two steps:
   - `uv sync --locked --no-install-project --no-editable` with a cache mount, bind-mounting `backend/uv.lock` and `backend/pyproject.toml`
   - copy `backend/` and run `uv sync --locked --no-editable`
3. **Final stage:** `FROM python:3.12-slim-trixie`. It:
   - creates user and group `catchup` (uid/gid 999) and `/data` owned by them
   - copies `/app/.venv` from the builder and `dist/` from `frontend` to `/app/frontend`
   - sets `PATH=/app/.venv/bin:$PATH`, `PYTHONUNBUFFERED=1`, `CATCHUP_DATA_DIR=/data`, `CATCHUP_FRONTEND_DIST=/app/frontend`
   - declares `VOLUME /data`, `EXPOSE 8000`, and `USER catchup`
   - defines `HEALTHCHECK --interval=30s --timeout=5s --start-period=20s` running a `python -c` urllib request to `http://127.0.0.1:8000/api/health` (the image has no curl; Host `127.0.0.1` is allowed by default)
   - runs `CMD ["catchup", "serve", "--host", "0.0.0.0", "--port", "8000"]`
- The final image contains no source tree and no build tools.

### D3. `.dockerignore` as an allowlist
- `*`, then re-include:
  - `backend/pyproject.toml`, `backend/uv.lock`, `backend/src/**`
  - `frontend/package.json`, `frontend/package-lock.json`, `frontend/index.html`, `frontend/tsconfig*.json`, `frontend/vite.config.ts`, `frontend/src/**`, `frontend/public/**` (if present)
- Then re-exclude `**/__pycache__`, `**/node_modules`, `**/.venv`, `**/dist`, and `**/*.test.tsx` only if the build does not need them. Tests are not needed for `vite build`, but `tsc --noEmit` type-checks them, so keep them unless the build passes without.
- Everything else is excluded by default: `.env`, `data/`, `work/`, PDFs, `.git`, `openspec/`, `docs/`, `.claude/`, `.factory/`.

### D4. `compose.yaml`
- One service, `catchup`, with both `image: ghcr.io/zhuoang2/catchup:latest` and `build: .`, so it can pull a published image or build locally.
- `ports: ["127.0.0.1:8000:8000"]` (local only).
- `volumes: ["catchup-data:/data"]` (named volume).
- `env_file` set to `.env` with `required: false` (Compose ≥ 2.24).
- `restart: unless-stopped`.

### D5. Smoke test script (`scripts/docker-smoke.sh`)
- It is used both locally and in CI. With an image tag argument, a fresh named volume, and a free port, it checks:
  1. The container becomes `healthy` within 60 s.
  2. `GET /api/health` with `Host: localhost` returns 200.
  3. `GET /` returns HTML.
  4. `docker exec … id -u` is not 0.
  5. `/data/catchup.sqlite3` exists.
  6. `PUT /api/settings/preferences` to `zh-Hans`, then a container restart, then `GET` still returns `zh-Hans`.
  7. The image contains no `/app/.env` or `/app/backend`.
- It cleans up on exit (trap).

### D6. CI and release
- **`ci.yml`:**
  - Bump `actions/checkout@v7`, `astral-sh/setup-uv@v10`, `actions/setup-node@v7`, and Node `24`. Keep the job names `backend` and `frontend`, since branch protection requires them.
  - Add a `docker` job: `docker/setup-buildx-action@v4`, `docker/build-push-action@v7` with `load: true`, `push: false`, `platforms: linux/amd64`, and a GitHub Actions cache. Then run `scripts/docker-smoke.sh`.
  - Add a wheel check step in `backend`: `uv build --wheel`, then assert the wheel contains `catchup/migrations/versions/0001_initial.py`.
- **`release.yml`:**
  - Triggers: `push` to `main` and tags `v*.*.*`. Permissions: `contents: read`, `packages: write`.
  - Steps: `checkout@v7`, `setup-qemu-action@v4`, `setup-buildx-action@v4`, `login-action@v4` to `ghcr.io` with `GITHUB_TOKEN`, `metadata-action@v6`, then `build-push-action@v7` with `platforms: linux/amd64,linux/arm64` and `push: true`.
  - Image `ghcr.io/zhuoang2/catchup`. Tags: `type=edge,branch=main`, `type=semver,pattern={{version}}`, `type=semver,pattern={{major}}.{{minor}}`, and `latest` on semver tags only.
  - The OCI labels include `org.opencontainers.image.source`.
  - QEMU was chosen over native arm runners for one simple job. The Node stage runs on `$BUILDPLATFORM`, so only the Python stage is emulated.

## Risks / Trade-offs

- [Moving migrations breaks existing local databases] → Alembic tracks revision IDs, not file paths, so `0001` stays applied. A test migrates a database created before the move and checks that it is unchanged.
- [arm64 builds under QEMU are slow] → Only the Python install is emulated. Dependencies ship aarch64 wheels (`uv.lock`). This is accepted for a release-only job.
- [Named volume vs bind mount permissions] → The named volume inherits `/data` ownership (uid 999). The README warns that bind mounts must be writable by uid 999.
- [The instance has no login] → Loopback-only publishing by default. The README states the risk before explaining `CATCHUP_ALLOWED_HOSTS` and port changes.
- [GHCR visibility after the first publish is unclear] → The reviewer checks it after the first push to `main` and sets it to public in the GitHub UI if needed.
- [`env_file required: false` needs Compose ≥ 2.24] → The README states the minimum Docker Compose version.

## Migration Plan

- Existing source checkouts: pull, then `uv sync`. `uv run uvicorn catchup.main:app` keeps working, and so does `uv run catchup serve`. Existing `./data` databases keep working (same revision IDs).
- Docker users start fresh with a new named volume. There is no data migration from a source checkout in this change. The README explains copying `catchup.sqlite3` into the volume if wanted.
- Rollback: revert the commits. Published images can be deleted from GHCR.

## Testing Plan

- Unit and integration tests (pytest, existing sandbox rules):
  - migrations resolve inside the package, and migrating a pre-move database is a no-op
  - `CATCHUP_FRONTEND_DIST` precedence and fallback
  - `catchup serve --help`, argument parsing, and the `uvicorn.run` call (patched)
  - all existing tests still pass
- CI:
  - wheel content check
  - Docker build plus `scripts/docker-smoke.sh` on every push and PR
  - release workflow on `main` (verified after merge by checking that GHCR has `edge` for both architectures)
- Manual by the reviewer with the user:
  - `docker compose up --build` on the Mac (arm64)
  - open the UI, save model settings, run one digest with a real key
  - restart and confirm the data is kept

## Open Questions

- None blocking. Cutting the first release tag (`v0.1.0`) is left to the user after merge.
