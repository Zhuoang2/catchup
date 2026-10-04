# Tasks

Implementer notes:
- Read `proposal.md`, `design.md` (D1–D6), `specs/local-deployment/spec.md`, and `research.md` first. Follow them; if something looks wrong, stop and report rather than redesigning.
- Treat these rules as verification criteria, not notes:
  - pytest makes no real network calls, uses no real API key, writes nothing outside temp dirs, and uses no real sleeps (the autouse sandbox in `backend/tests/conftest.py`)
  - Docker-based checks use only local images, throwaway named volumes, and loopback ports, and clean up after themselves
- Docker is required for groups 2–3. Run `docker info` first. If the daemon is not available, finish group 1, then stop and report.
- Backend commands run from `backend/` with uv; frontend commands run from `frontend/` with npm; Docker commands run from the repo root.
- Commit after each task group. Do not edit `proposal.md`, `design.md`, or `specs/`.

## 1. Self-contained backend package

- [x] 1.1 Move `backend/alembic/` to `backend/src/catchup/migrations/` with `git mv` (keep `env.py`, `script.py.mako`, `versions/0001_initial.py`), and point `migrate()` in `backend/src/catchup/db.py` at the package-relative directory per design.md D1. Verify:
  - the existing migration and startup tests pass
  - a new test asserts the migrations directory lives inside the `catchup` package
  - a new test migrates a database created with the old revision table and checks it is unchanged and still at head
- [x] 1.2 Add `CATCHUP_FRONTEND_DIST` (`Settings.frontend_dist`) in `backend/src/catchup/config.py` and use it in `create_app` (`backend/src/catchup/main.py`) with the precedence in design.md D1 (argument > setting > source-tree fallback). Add it, commented out, to `.env.example`. Verify: tests for each precedence level, for a missing directory (API still works, no frontend), and that `backend/tests/test_static.py` still passes.
- [x] 1.3 Add `backend/src/catchup/cli.py` with `catchup serve [--host] [--port]` (defaults `127.0.0.1`, `8000`) that calls `uvicorn.run(create_app(), host=…, port=…)`, and `[project.scripts] catchup = "catchup.cli:main"` in `backend/pyproject.toml`. Verify: tests for `--help` (exit 0), the defaults, and custom values, with `uvicorn.run` patched and asserted; `uv run catchup serve --help` works.
- [x] 1.4 Update the README "Development setup" section and the `AGENTS.md` "Commands" section to mention `uv run catchup serve` alongside `uvicorn`. Verify: the documented commands run (`--help` for serve).

## 2. Container image and local run

- [ ] 2.1 Add `.dockerignore` (allowlist, design.md D3) and the multi-stage `Dockerfile` (design.md D2). Verify:
  - `docker build -t catchup:local .` succeeds
  - `docker run --rm catchup:local id -u` is not `0`
  - the image has no `/app/backend`, and `/app/.env` is absent even when a dummy `.env` exists in the working copy at build time
  - `docker image inspect` shows the `HEALTHCHECK`, `VOLUME /data`, and `EXPOSE 8000`
  - record the image size in the test report
- [ ] 2.2 Add `compose.yaml` per design.md D4. Verify:
  - `docker compose config` is valid
  - after `docker compose up -d --build`, the service becomes healthy
  - `docker compose port catchup 8000` (or `docker inspect`) shows the host binding `127.0.0.1`
  - `docker compose down` cleans up; remove the volume only if the test created it
- [ ] 2.3 Add `scripts/docker-smoke.sh` per design.md D5 (executable, `set -euo pipefail`, trap cleanup, image tag argument). Verify: `scripts/docker-smoke.sh catchup:local` passes locally and prints each check; a deliberately broken health URL makes it fail (try once, then revert).

## 3. CI and release automation

- [ ] 3.1 Update `.github/workflows/ci.yml` per design.md D6:
  - actions at current majors and Node 24, keeping the job names `backend` and `frontend`
  - a wheel content check in `backend`
  - a new `docker` job (buildx, `load: true`, `linux/amd64`, GitHub Actions cache, run `scripts/docker-smoke.sh`)

  Verify: lint the workflow with `actionlint` (e.g. `docker run --rm -v "$PWD:/repo" -w /repo rhysd/actionlint:latest`); the wheel check passes locally (`uv build --wheel`, then inspect the zip).
- [ ] 3.2 Add `.github/workflows/release.yml` per design.md D6 (triggers `main` plus `v*.*.*` tags; permissions `contents: read`, `packages: write`; QEMU + buildx; metadata tags `edge`/semver/`latest`; push to `ghcr.io/zhuoang2/catchup`; OCI labels). Verify:
  - `actionlint` passes
  - a local multi-platform build without push succeeds: `docker buildx build --platform linux/amd64,linux/arm64 .`, or, if the local builder cannot do multi-platform, the native platform only, noting this in the report
  - the workflow has no trigger on `pull_request`

## 4. Documentation and test report

- [ ] 4.1 Add a README "Run with Docker" section:
  - generating `CATCHUP_SECRET_KEY` into `.env`
  - `docker compose up -d` (published image) and `--build` (from source)
  - an equivalent `docker run` command
  - opening `http://localhost:8000`
  - upgrading (`docker compose pull && docker compose up -d`)
  - backing up and restoring the `catchup-data` volume
  - minimum Docker Compose version (2.24)
  - local-only by design, with the no-login risk stated before any instructions to expose it
  - bind-mount permissions (uid 999)
  - collected content being sent to the model provider

  Verify: every command in the section matches `compose.yaml` and `Dockerfile` (names, ports, volume, env vars).
- [ ] 4.2 Write `docs/process/test-report-add-docker-packaging.md`:
  - commands and results, including the image size and the smoke script output
  - a table mapping every scenario in `specs/local-deployment/spec.md` to its test or check; list any scenario verified only manually
  - a placeholder "Manual verification" section

  Create `openspec/changes/add-docker-packaging/review-notes.md` and append a short entry to `docs/process/ai-usage-log.md`. Verify: every scenario appears in the table.

Manual verification (`docker compose up --build` on the user's Mac with a real model key, one digest, data kept across a restart) and checking the first GHCR publish after merge are done by Claude Code with the user, not by the implementer.
