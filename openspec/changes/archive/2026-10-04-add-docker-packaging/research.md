# Research: Docker packaging, GHCR publishing, local deployment (#7)

- Date: 2026-10-04
- Query: How does CatchUp start today, how does it locate its frontend build, migrations, and data, and what does CI do? What current external facts govern building a single Docker image with uv and Node and publishing it to GHCR?
- Git ref: main @ 7457b10
- Change: `add-docker-packaging`
- Issue: [#7](https://github.com/Zhuoang2/catchup/issues/7) (scope set by D-011: local deployment only, no hosted instance)

## Summary

CatchUp is a FastAPI app (`backend/`, uv-managed, src layout, hatchling build) that serves a React/Vite build (`frontend/dist`) from the same process. It is started with `uv run uvicorn catchup.main:app` from `backend/`.

The app locates three things by relative position, with no environment override:
- the frontend build, by walking up from `main.py` to the repository root
- the Alembic migrations, by walking up from `db.py` to `backend/alembic`, which is outside the Python package that hatch builds
- the data directory, which defaults to `./data` relative to the working directory

Startup runs migrations and recovers interrupted runs. Configuration comes only from `CATCHUP_*` environment variables. `CATCHUP_SECRET_KEY` is needed to save a model key, and `CATCHUP_ALLOWED_HOSTS` defaults to local host names. CI runs backend tests (Python 3.12) and frontend tests and build (Node 20) on every push and PR, with no image build or publish. The repository has no Dockerfile or `.dockerignore`. The working copy contains gitignored files (course PDF, `work/`, possibly `.env`, `.venv`, `node_modules`, `data/`) that a build context would include by default.

## Detailed Findings

### Application start and process model
- `create_app(settings=None, dist_dir=None)` builds the app — `backend/src/catchup/main.py:24`.
- Startup lifespan, in order — `main.py:28-38`:
  1. creates the engine
  2. runs `migrate(engine)`
  3. creates the session factory
  4. calls `recover_runs`
- A module-level `app = create_app()` is created at import time from environment settings — `main.py:103`. The README's run command is `uv run uvicorn catchup.main:app --reload` from `backend/` — `README.md:29`.
- Background digest runs execute in a daemon thread inside the same process, with a module-level lock enforcing one active run (`backend/src/catchup/digest/runner.py`; `add-core-digest-flow` design D2). The preview cache is per app instance (`main.py:42`).

### Frontend build location
- `frontend_dist = dist_dir or Path(__file__).resolve().parents[3] / "frontend" / "dist"` — `main.py:83`. From `backend/src/catchup/main.py`, `parents[3]` is the repository root.
- The frontend is served only if `index.html` exists there: `/assets` is mounted as static files and an SPA fallback middleware handles other paths — `main.py:84-98`.
- `dist_dir` is used by tests (`backend/tests/test_static.py:11`). No environment variable sets it.
- The frontend build is `tsc --noEmit && vite build` — `frontend/package.json:8`. The output is `frontend/dist/` (gitignored, `.gitignore:26`).
- Frontend tooling: Vite 8.3.2, TypeScript 7, React 19 — `frontend/package.json:11-26`. There is no `engines` field. The README requires Node 20.19+ or 22.12+ for Vite 8 (`README.md:14-15`).

### Migrations location and packaging
- `migrate()` points Alembic at `Path(__file__).resolve().parents[2] / "alembic"`, i.e. `backend/alembic` — `backend/src/catchup/db.py:32-36`.
- Alembic files: `backend/alembic/env.py`, `script.py.mako`, `versions/0001_initial.py`.
- The hatch wheel target packages only `src/catchup` — `backend/pyproject.toml:31-32` — so `backend/alembic` is not in a built wheel. The relative-path lookups in `main.py:83` and `db.py:34` resolve correctly only when the code runs from the source tree (including uv's default editable install).

### Data and configuration
- `Settings.from_env()` reads all configuration from the environment — `backend/src/catchup/config.py:26-42`:
  - `CATCHUP_DATA_DIR` (default `./data`, relative to the current working directory)
  - `CATCHUP_SECRET_KEY` (optional at startup; required to save a model key)
  - first-add and text limits
  - `CATCHUP_ALLOWED_HOSTS` (default `localhost,127.0.0.1,[::1]`)
  - `CATCHUP_USER_AGENT_CONTACT` (validated)
- The SQLite file is `<data_dir>/catchup.sqlite3`; the directory is created if missing; WAL mode is on — `db.py:17-29`. WAL creates `-wal`/`-shm` files next to the database and requires all processes on the same host (`add-core-digest-flow` research).
- Host check: a request is rejected with 400 unless its Host header's hostname is in `allowed_hosts`. The port is ignored — `main.py:50-77`. A browser opening `http://localhost:<port>` therefore sends hostname `localhost`.
- `.env.example` lists all variables, with `CATCHUP_DATA_DIR=./data` — `.env.example:1-13`. The README loads `.env` with `set -a; . ../.env` before `uvicorn` (`README.md` "Development setup").

### Python and Node versions
- `requires-python = ">=3.11"` — `backend/pyproject.toml:9`. There is no `.python-version`. CI uses Python 3.12 (`.github/workflows/ci.yml:10-12`). Local development used Python 3.11.4, and uv created a 3.12 venv in review worktrees.
- `backend/uv.lock` is committed. `frontend/package-lock.json` is committed.

### CI today
- One workflow, `.github/workflows/ci.yml`, triggered `on: [push, pull_request]`:
  - Job `backend`: `actions/checkout@v4`, `astral-sh/setup-uv@v6` (Python 3.12), `uv run pytest` in `backend/` — `ci.yml:6-15`.
  - Job `frontend`: `actions/checkout@v4`, `actions/setup-node@v4` (Node 20, npm cache), `npm ci`, `npm test -- --run`, `npm run build` — `ci.yml:17-34`.
- No job builds or publishes an image. The workflow has no `permissions:` block, no tags trigger, and no release trigger.
- Branch protection on `main` requires the `backend` and `frontend` checks (D-010).

### Build context contents
- The repository has no `Dockerfile` or `.dockerignore`.
- At the repo root, the working copy also contains gitignored or local-only items:
  - `CS146S Final Project Description.pdf` (D-003, course staff material)
  - `work/` (agent memory)
  - `.DS_Store`
  - possibly `.env` (secrets), `backend/.venv`, `frontend/node_modules`, `frontend/dist`, `data/`
- `.gitignore:1-29` excludes these from git, but Docker's build context uses `.dockerignore`, not `.gitignore`.

## Code References
- `backend/src/catchup/main.py:24-38,83-103` — app factory, lifespan, frontend dist path, module-level app
- `backend/src/catchup/db.py:17-36` — data dir and SQLite file; Alembic script location
- `backend/src/catchup/config.py:26-42` — environment configuration and defaults
- `backend/pyproject.toml:9,31-32` — Python requirement; wheel packages only `src/catchup`
- `frontend/package.json:6-26` — build script and tool versions
- `.github/workflows/ci.yml:1-34` — current CI
- `.gitignore:1-29`, `.env.example:1-13`, `README.md:12-50`

## Current Specs
- No current spec covers installation, packaging, or deployment.
- Related constraints in `model-settings`:
  - "Protect the stored API key": encryption needs an instance secret
  - "Accept requests only for allowed hosts": default local hosts only

## External facts (verified 2026-10-04)

**uv in Docker** (https://docs.astral.sh/uv/guides/integration/docker/)
- Install by copying the binary from the uv image: `COPY --from=ghcr.io/astral-sh/uv:0.12.23 /uv /uvx /bin/`. Latest uv is 0.12.23 (2026-10-03); digest pinning is also documented.
- Documented caching pattern:
  1. `uv sync --locked --no-install-project`, with a cache mount on `/root/.cache/uv` and bind mounts for `uv.lock` and `pyproject.toml`
  2. copy the project
  3. `uv sync --locked`
- Recommended environment variables:
  - `UV_COMPILE_BYTECODE=1` ("typically desirable for production images")
  - `UV_LINK_MODE=copy` (with cache mounts)
  - `UV_NO_DEV=1` (the official example uses this)
  - `UV_PYTHON_DOWNLOADS=0` (builder)
- The multi-stage example (https://github.com/astral-sh/uv-docker-example/blob/main/multistage.Dockerfile):
  - Builder is `ghcr.io/astral-sh/uv:python3.12-trixie-slim`; final image is `python:3.12-slim-trixie`. The base Python must match.
  - Creates a `nonroot` user (uid/gid 999), copies `/app` with `--chown`, sets `PATH=/app/.venv/bin:$PATH` and `PYTHONUNBUFFERED=1`, then switches to `USER nonroot`.
  - Uses an exec-form `CMD`.
- `--no-editable` is documented for multi-stage builds that copy only `.venv` without the source.

**FastAPI in containers** (https://fastapi.tiangolo.com/deployment/docker/)
- Use an exec-form `CMD` for graceful shutdown and lifespan events.
- Add `--proxy-headers` behind a TLS-terminating proxy.
- With a cluster, run one process per container (no `--workers`); on a single server, workers are fine.
- No HEALTHCHECK or non-root guidance on that page.

**Base images** (docker-library official images)
- Python: `3.12-slim` = 3.12.15 and `3.13-slim` = 3.13.16. Bare `-slim` tags are Debian **trixie**; `-slim-bookworm` tags still exist.
- Node: current LTS is **24.21.0 "Krypton"**, with tags `24-slim` / `lts-slim` (bookworm) and `24-trixie-slim`. Node 26 is "current".

**GitHub Actions, latest releases**

| Action | Latest | Released |
| --- | --- | --- |
| `actions/checkout` | v7.0.1 | 2026-07-20 |
| `actions/setup-node` | v7.0.0 | 2026-07-14 |
| `astral-sh/setup-uv` | v10.2.0 | 2026-09-21 |
| `docker/build-push-action` | v7.4.0 | 2026-09-15 |
| `docker/login-action` | v4.6.0 | 2026-07-29 |
| `docker/metadata-action` | v6.2.0 | 2026-07-02 |
| `docker/setup-buildx-action` | v4.4.1 | 2026-09-16 |
| `docker/setup-qemu-action` | v4.4.0 | 2026-09-15 |
| `actions/attest-build-provenance` | v4.2.2 | 2026-08-06 |

The current CI uses `checkout@v4`, `setup-uv@v6`, and `setup-node@v4` (`ci.yml`).

**GHCR with `GITHUB_TOKEN`** (GitHub Packages docs)
- The documented permissions are `contents: read`, `packages: write`, `attestations: write`, and `id-token: write`. The image name format is `ghcr.io/NAMESPACE/IMAGE_NAME`, conventionally `${{ github.repository }}`.
- `docker/metadata-action` lowercases image names; registry name components must be lowercase.
- A package published by a workflow is linked to that repository automatically. The `org.opencontainers.image.source` label also links it.
- The docs disagree on default visibility: one page says the package inherits the repository's visibility, another says a first publish is private until changed in package settings. Unverified which applies here.

**Multi-architecture**
- Linux arm64 runners (`ubuntu-24.04-arm` etc.) are available, and standard runners are free and unlimited on public repositories (https://docs.github.com/en/actions/reference/runners/github-hosted-runners).
- Docker's docs show two approaches (https://docs.docker.com/build/ci/github-actions/multi-platform/):
  - QEMU emulation with `setup-qemu-action@v4` + `setup-buildx-action@v4` + `build-push-action@v7` for `linux/amd64,linux/arm64`
  - native multi-runner builds via the reusable workflow `docker/github-builder` (v1.17.0)

## Related History
- `2a179d7` MIT license; `168dc13` branch protection (D-010); `7457b10` local-only deployment (D-011); issue #7 rescoped the same day.
- Proposal commitment (`docs/proposal.md:26`): "setup documentation", and originally a deployed demo, now local (D-011).
- #13 (clean-environment install test) is related; it is not part of this change's scope unless the proposal includes it.
