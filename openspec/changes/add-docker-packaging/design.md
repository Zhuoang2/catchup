# Design: add-docker-packaging

Status: awaiting user choice

## Solution Proposals

Context:
- Request: package CatchUp as one Docker image (FastAPI serving the built React app, SQLite on a persistent volume), publish it to GHCR with GitHub Actions, and document local deployment. There is no hosted instance (D-011, issue #7).
- Research Source: `research.md`, sections "Frontend build location", "Migrations location and packaging", "Data and configuration", "CI today", "Build context contents", and "External facts".

### Shared by both proposals

- **Multi-stage Dockerfile** at the repo root:
  - A Node stage on `node:24-slim` (current LTS) runs `npm ci && npm run build`.
  - A uv stage on `ghcr.io/astral-sh/uv:python3.12-trixie-slim` uses the documented cache pattern (`uv sync --locked --no-install-project`, then the project), with `UV_COMPILE_BYTECODE=1`, `UV_NO_DEV=1`, and `UV_PYTHON_DOWNLOADS=0`.
  - The final stage is `python:3.12-slim-trixie`, the base the uv example says must match the builder (`research.md`, "External facts").
- **Final image:**
  - It runs as a non-root user (uid 999).
  - `CATCHUP_DATA_DIR=/data` points at a declared volume. The SQLite and WAL files must live on one host volume (research, "Data and configuration").
  - It exposes port 8000 and starts uvicorn with an exec-form `CMD` on `0.0.0.0`.
  - Its `HEALTHCHECK` calls `/api/health` with `Host: localhost`, which the allowed-hosts check accepts (`main.py:50-77`).
- **`.dockerignore` as an allowlist** (ignore everything, then re-include `backend/` and `frontend/` sources and lockfiles). This keeps the course PDF, `work/`, `.env`, `.venv`, `node_modules`, and `data/` out of the build context (research, "Build context contents").
- **`compose.yaml`** for one-command local use:
  - The port is published as `127.0.0.1:8000:8000`, so the instance, which has no login, is reachable only from the user's own machine.
  - Data is a named volume.
  - Settings come from `.env` (`env_file`).
  - The README shows how to generate `CATCHUP_SECRET_KEY` first.
- **Publish workflow** `.github/workflows/release.yml`:
  - It builds `linux/amd64` and `linux/arm64` (Apple Silicon users) and pushes `ghcr.io/zhuoang2/catchup` (lowercase).
  - Tags: `edge` on pushes to `main`; `X.Y.Z`, `X.Y`, and `latest` on `vX.Y.Z` git tags (`docker/metadata-action@v6`).
  - Permissions: `contents: read`, `packages: write`.
  - Actions at current majors: `build-push-action@v7`, `login-action@v4`, `setup-buildx-action@v4`, `setup-qemu-action@v4`.
- **Image smoke test on every PR:** CI builds the image without pushing, runs it, and checks:
  - `/api/health` answers 200
  - `/` serves the frontend
  - the database file is created on the volume
  - a restart keeps the data
- **README "Run with Docker"** section: commands for `docker compose up` and plain `docker run`, how to back up the volume, the note that collected content is sent to the model provider, and the note that the instance is local-only by design.
- **Spec capability (new): `local-deployment`**. It covers:
  - starting with one command from a published image
  - data persisting across container restarts and upgrades
  - reachability from the local machine only by default
  - running as non-root
  - a health check

---

### Proposal 1 — Image that mirrors the source tree (no application code changes)

- Overview: The final image recreates the repository layout under `/app`:
  - `/app/backend` holds the source, `alembic/`, and an editable `.venv`.
  - `/app/frontend/dist` holds the built frontend.

  The existing relative-path lookups (`main.py:83` → `parents[3]/frontend/dist`; `db.py:34` → `parents[2]/alembic`) resolve unchanged, so the application code stays as it is.
- Key Changes:
  - New files: `Dockerfile`, `.dockerignore`, `compose.yaml`, `.github/workflows/release.yml`, plus a smoke-test job in `ci.yml`.
  - README section.
  - Spec: new `local-deployment`.
  - No Python or TypeScript changes.
- Trade-offs:
  - Benefits:
    - Smallest and fastest change, with the least risk to the code that 197 tests cover.
    - The image behaves exactly like a source checkout, which is easy to reason about.
  - Costs:
    - The image depends on the source layout. The `parents[]` lookups stay fragile: moving a file breaks the image, and only the smoke test would catch it.
    - The final image carries the full backend source and an editable install.
    - CatchUp still cannot be installed as a normal Python package (e.g. `uvx`/`pip`), because migrations stay outside the package.
- Validation:
  - The CI smoke test (health check, frontend served, database created on the volume, data kept across a restart).
  - `docker compose up` on the developer's Mac (arm64) with a real model key, running one digest.
  - Inspecting that the image has none of the files excluded by `.dockerignore`.
- Open Questions:
  - None blocking.

---

### Proposal 2 — Self-contained package, with a slim image built from it

- Overview: Make the backend package locate its own resources, then build a final image that contains only the installed environment and the built frontend.
  - Migrations move into the package.
  - The frontend location becomes configurable.
  - A `catchup` command starts the server.
  - The image installs the project non-editable and copies only `.venv` and the frontend build.
- Key Changes:
  - Move `backend/alembic/` to `backend/src/catchup/migrations/`. `db.py` points Alembic at the package-relative path, and the wheel then includes migrations automatically (`pyproject.toml:31-32`).
  - New `CATCHUP_FRONTEND_DIST` setting. When it is unset, the current source-tree path (`main.py:83`) is the fallback, so `uv run uvicorn` in development keeps working.
  - New console script `catchup = "catchup.cli:main"` (`catchup serve --host --port`), which wraps uvicorn so the image and future `uvx catchup` use one entry point.
  - Dockerfile: `uv sync --locked --no-editable` in the builder; the final stage copies only `/app/.venv` and the frontend `dist` (set via `CATCHUP_FRONTEND_DIST=/app/frontend`).
  - Plus all shared items. Specs: new `local-deployment`.
- Trade-offs:
  - Benefits:
    - Removes the fragile `parents[]` coupling that #7 already flagged.
    - Smaller image without the source tree.
    - Opens the door to `pip`/`uvx` installs later without more restructuring.
    - A cleaner story for the "deployment automation" evidence in the course report.
  - Costs:
    - Touches working code: the migration location, the frontend path resolution, and a new CLI. Tests for migrations and static serving need updating.
    - The development command and README change slightly (`catchup serve` alongside `uvicorn`).
    - More Droid work than Proposal 1.
- Validation:
  - Everything in Proposal 1.
  - Plus: a test that builds the wheel and checks that it contains `catchup/migrations/versions/0001_initial.py`.
  - A test that `CATCHUP_FRONTEND_DIST` overrides the path while the source-tree fallback still works.
  - A test that `catchup serve --help` runs.
  - The existing migration and static tests still pass.
- Open Questions:
  - Whether to also publish the wheel (e.g. to GitHub Releases or PyPI). Not in scope here; the package would be ready for it.

---

Recommendation: **Proposal 2.** The `parents[]` lookups are the one real obstacle to packaging, and research shows they only work from a source checkout. Fixing them once makes the image smaller and the package installable, with a contained, well-tested change: one moved folder, one setting, one small CLI. Proposal 1 is a reasonable fallback if time is tight, since it ships the same user-facing result with no code changes.
