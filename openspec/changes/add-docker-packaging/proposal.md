# Proposal

## Why

CatchUp is meant to be downloaded and run by its users (open source, self-hosted; D-011 confirms local deployment is the delivery model). Today it only runs from a source checkout with Python, uv, and Node installed, because it finds its frontend build and migrations by relative paths that work only inside the repository (`research.md`, "Frontend build location", "Migrations location and packaging"). A published Docker image gives users a one-command start. Release automation also supplies the course's "CI/CD or deployment automation" evidence (issue #7).

## What Changes

- The backend package becomes self-contained:
  - Database migrations move into the package.
  - The frontend build location is configurable with `CATCHUP_FRONTEND_DIST`, keeping the source-tree default for development.
  - A `catchup serve` command starts the server.
- A multi-stage Dockerfile builds the frontend and a non-editable backend environment into a slim image. The image runs as a non-root user, keeps data on a `/data` volume, and has a health check.
- An allowlist `.dockerignore` keeps local secrets, course material, and build artifacts out of the build context.
- A `compose.yaml` starts CatchUp with one command, reachable only from the local machine (port bound to `127.0.0.1`).
- CI builds and smoke-tests the image on every push and pull request. A release workflow publishes multi-architecture images (`linux/amd64`, `linux/arm64`) to `ghcr.io/zhuoang2/catchup`: `edge` from `main`, plus version tags from `vX.Y.Z` git tags.
- The README gains a "Run with Docker" guide covering start, upgrade, backup, and the local-only design.

## Capabilities

### New Capabilities
- `local-deployment`: Running CatchUp from a published container image on the user's own machine, with persistent data, local-only access by default, a non-root process, a health check, and a package that does not depend on the source tree.

### Modified Capabilities
- None.

## Impact

- Code:
  - `backend/alembic/` moves to `backend/src/catchup/migrations/`
  - `backend/src/catchup/db.py` (migration location)
  - `config.py` and `main.py` (`CATCHUP_FRONTEND_DIST`)
  - new `backend/src/catchup/cli.py`
  - `pyproject.toml` (`[project.scripts]`)
- New files: `Dockerfile`, `.dockerignore`, `compose.yaml`, `scripts/docker-smoke.sh`, `.github/workflows/release.yml`.
- Changed files: `.github/workflows/ci.yml` (Docker smoke job; actions at current majors; Node 24), `README.md`, `AGENTS.md`, `.env.example`.
- Development: `uv run uvicorn catchup.main:app` keeps working; `uv run catchup serve` is added.
- Publishing: the first image goes to GHCR after merge to `main`. Package visibility may need to be set to public once, in the GitHub UI (research: the docs disagree on the default).
