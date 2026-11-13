# Design

## Context

The motivation is in proposal.md ("Why"). Claude Code verified these facts on 2026-11-13:
- `backend/pyproject.toml` has `requires-python = ">=3.11"`, and the README says "Install Python 3.11 or newer". CI (`.github/workflows/ci.yml`) and the Dockerfile use 3.12. Under Python 3.11.4, every file in `backend/src` parses, but `backend/tests/test_discovery.py` raises `SyntaxError: f-string expression part cannot include a backslash`.
- `create_app()` checks for `frontend/dist/index.html` once, at startup (`backend/src/catchup/main.py:183-188`).
- `compose.yaml` has `image: ghcr.io/zhuoang2/catchup:latest` and `build: .`. Registry metadata shows that `latest` is v0.1.0 (revision `b5fec1a`, 2026-10-04) and `edge` is `064d3a9`.
- The release workflow (`.github/workflows/release.yml`) tags images `edge` on `main`. On a `v*.*.*` tag it adds `{{version}}` and `{{major}}.{{minor}}`, and `docker/metadata-action` adds `latest` by default.
- Every version field is `0.1.0`: `backend/pyproject.toml`, `frontend/package.json`, `extension/package.json`, and `extension/public/manifest.json`. The README's User-Agent example also says `0.1.0`.
- The Dockerfile's health check requests `http://127.0.0.1:8000/api/health`. The README names no health address, and it says that `localhost` and `127.0.0.1` are both needed "for the container health check".
- Existing docs tests read the README: `backend/tests/test_readme_context.py` and `extension/src/test/docs.test.ts`.

Probes on 2026-11-13 (Docker Compose v5.5.1; a dummy project built from a local image; nothing was downloaded):
- `COMPOSE_FILE=compose.yaml:compose.build.yaml` in the project's `.env` is read by `docker compose config`, `up --build`, `ps`, and `stop`.
- With the override, the build tags only the override's image name, and the base file's image tag is not created. Without the line, the base file's image is used.
- `docker compose create` creates the service's named volume and a container in the "created" state. The volume and image names can then be read with `docker inspect`, so a new machine can restore into an empty volume before the first start.
- `umask 077` before writing `.env` gives mode 600.
- Without a `build` section, `docker compose up -d --build` starts from the locally tagged image without any warning.
- With `requires-python = ">=3.12"`, `uv lock` re-resolves with no version changes. The only package it reports is `Removed tomli v2.4.1`, and with the version bump also `Updated catchup v0.1.0 -> v0.2.0`. `uv lock --offline` works once uv's cache has the index data; on an empty cache it fails, and `uv lock` needs PyPI. The lock diff is larger than the package list (226 lines removed, 5 added):
  - the `resolution-markers` block is deleted;
  - the 3.11 wheel lines (`cp311`, `pp311`, `graalpy311`) are dropped;
  - coverage's `toml` extra is dropped, so pytest-cov depends on `coverage` instead of `coverage[toml]`;
  - httpx2's `httpx2-jsfetch` marker becomes `sys_platform == 'emscripten'`.
- `npm install --package-lock-only --offline` after a version bump changes only the two root `version` fields of each `package-lock.json`.
- `docker compose create` with the build override builds a missing image, so it needs the Dockerfile and the sources (a clone). With only `compose.yaml`, `compose.build.yaml`, and `.env`, it fails with "open Dockerfile: no such file or directory".
- The base images (`node:24-slim`, the uv image, `python:3.12-slim-trixie`) are not stored as local images, only as BuildKit cache. A build still contacts Docker Hub and GHCR to resolve their tags.
- This Mac's default `node` is v20.19.0. Node v22.17.1 is installed under nvm.

## Goals / Non-Goals

**Goals:**
- The README's two install paths, and its backup and restore, work for a new user on a clean machine.
- The stated minimum versions are the versions the project actually tests.
- A source build never takes the published image's name.

**Non-Goals:**
- Any change to application code, the Dockerfile, CI, or the release workflow.
- Serving a frontend that is built after startup without a restart. The README's order fixes this for users. A code change would add a per-request file check for a development-only case.
- The browser extension and "Install as an app" sections.
- `docs/alpha-release.md`, a submitted course document.

## Decisions

### D1. Python 3.12 is the minimum

- `requires-python = ">=3.12"`, and `uv lock` is regenerated, without `--upgrade`.
- The README says "Python 3.12 or newer". It adds that uv downloads a suitable Python when the system's is older.
- **Alternative: keep 3.11.** Rewrite the f-string and add a 3.11 CI job. Rejected: CI would get slower, the container never runs 3.11, and uv makes 3.12 effortless.

### D2. Node.js 22.12 or newer

The README states "Node.js 22.12 or newer". It adds that CI and the image use Node.js 24, and that distribution packages can be older (Debian 12 has 18.20), so users can install Node.js from nodejs.org or with a version manager.

Vite 8 accepts 20.19+ as well. But Node.js 20 reached end of life on 2026-04-30, so the README stops recommending it.

### D3. Build the frontend first

- The README's source steps install and build the frontend (`npm ci`, `npm run build`) before starting the backend.
- It says that the backend serves `frontend/dist` only if `dist` existed when the backend started, so a later build needs a backend restart.
- The Vite dev server path (`npm run dev`) stays as an alternative for frontend work.

### D4. Source builds use `catchup:local` through a Compose override

`compose.yaml` drops `build: .` and keeps `image: ghcr.io/zhuoang2/catchup:latest`. A new `compose.build.yaml` contains only:

```yaml
services:
  catchup:
    image: catchup:local
    build: .
```

For a source build, the README says:
1. Clone the repository and change into it.
2. Create `.env`.
3. Add `COMPOSE_FILE=compose.yaml:compose.build.yaml` to `.env`.
4. Run `docker compose up -d --build`. To upgrade later, run `git pull`, then `docker compose up -d --build`.

Because Compose reads `COMPOSE_FILE` from `.env`, every later command uses `catchup:local`, including `stop`, `ps`, `create`, and `up` in the backup and restore steps.

For the published image, the README still needs only `compose.yaml` and `.env`, either from a clone or by downloading `compose.yaml`. The commands stay the same: `docker compose up -d`, and to upgrade, `docker compose pull && docker compose up -d`.

The `.env` file is also passed to the container (`env_file`). The `COMPOSE_FILE` variable inside the container is unused and harmless.

- **Alternative: an image variable** (`image: ${CATCHUP_IMAGE:-…}`). Rejected: it needs the same `.env` line, and a missing variable silently falls back to the published name.
- **Alternative: `compose.override.yaml`,** which Compose loads automatically. Rejected: shipping it would turn on source builds for everyone.
- **Alternative: default to `edge`.** Rejected by the user (2026-11-13). A release instead makes `latest` current.

### D5. Backup and restore commands

The README's backup and restore section gets three blocks. Each block derives `container`, `volume`, and `image` itself, the way the current backup lines do.
- **Back up:**
  1. `docker compose stop catchup`;
  2. derive the names;
  3. write the backup with `umask 077` to `"$HOME/catchup-data.tar.gz"`, outside the checkout;
  4. `docker compose up -d`.
- **Restore into this installation:**
  1. `docker compose stop catchup`;
  2. derive the names;
  3. empty the volume, including hidden files, with a one-line command in the image, for example Python that removes every entry under `/data`, run with `--network none`;
  4. restore with the existing `tarfile` command;
  5. `docker compose up -d`.
- **Restore on a new machine:** set up the same install path as in "Run with Docker", with the same `.env` and the same secret. For the published image, that is `compose.yaml`. For a source build, it is a clone, because `create` builds the image. Then:
  1. `docker compose create`;
  2. derive the names;
  3. restore (the new volume is empty);
  4. `docker compose up -d`.

The text keeps the warnings that apply: back up `.env` separately, keep the same secret, and bind mounts must be writable by UID 999.

### D6. Smaller README fixes

- **Health address.** Show `curl http://localhost:8000/api/health`, which answers `{"status":"ok"}`, in "Run with Docker". In the source steps, use `http://127.0.0.1:8000/api/health`.
- **Allowed hosts wording.** Say that `127.0.0.1` must stay in `CATCHUP_ALLOWED_HOSTS` for the container health check, and that `localhost` must stay for local browser access.
- **Docker secret.** Run the existing `printf … > .env` line under `umask 077`, for example in a subshell `(umask 077; printf …)`.
- **Development secret.** Replace "copy, generate, paste" with commands that write `.env` from `.env.example`, set the generated secret, and print nothing, under `umask 077`. For example, `grep -v '^CATCHUP_SECRET_KEY=' .env.example > .env`, then append `CATCHUP_SECRET_KEY=…` with `printf` and Python's `secrets`.
- **Database path.** The source checkout keeps its database at `backend/data/catchup.sqlite3` (the default `CATCHUP_DATA_DIR=./data`, relative to `backend/`). The text that moves a source-checkout database into the volume names this path.

### D7. Version 0.2.0, and the release after the merge

- **Version fields.** Set `0.2.0` in:
  - `backend/pyproject.toml`, then refresh `uv.lock`, where the `catchup` package entry changes;
  - `frontend/package.json` and `extension/package.json`, then refresh their `package-lock.json` files with `npm install --package-lock-only`;
  - `extension/public/manifest.json`;
  - the README's User-Agent example.
- **Release.** The tag and the GitHub release are not part of the implementation. After the merge, Claude Code asks the user to confirm. It then pushes `v0.2.0` on the merge commit and creates a release whose notes summarize the changes since v0.1.0. It checks once that the release workflow published `0.2.0` and `latest` for both platforms.

### D8. Test seams

A new `backend/tests/test_install_docs.py` reads the README and the configuration files, as `test_readme_context.py` does. It checks:
- that the stated minimum versions match the configuration;
- that the Compose files are split as in D4;
- that the README names that setup and the health address;
- that the version fields agree.

The command blocks themselves are checked by running them, not by unit tests: tasks 3.1 and the review re-run (design "Migration Plan").

## Risks / Trade-offs

- [A user on Python 3.11 without uv] → The README requires uv. With uv, a 3.12 interpreter is fetched automatically.
- [Existing source-build users of `docker compose up -d --build`] → Without the new `.env` line, `up -d --build` has nothing to build. It starts silently, with no warning, from the image already tagged `ghcr.io/zhuoang2/catchup:latest` on that machine, which is their previous source build (probe, 2026-11-13). So the upgrade does not happen. The README's upgrade text tells source-build users to add the line first. The data volume is unaffected either way.
- [`uv lock` needs network access] → It is a one-time step in the implementation. The task records the package diff, which must show only the `tomli` removal and the version change.
- [The emptying command deletes data] → It runs only in the restore block, after a stop, and the README tells the user to make a backup first.

## Migration Plan

- No data migration.
- Users who build from source with Docker add `COMPOSE_FILE=compose.yaml:compose.build.yaml` to `.env`.
- To roll back, revert the commit. A published release stays published.

At review, Claude Code runs:
- the Docker smoke script;
- a second clean-install run by a fresh sub-agent that sees only the new README, on a clean `debian:12` container and with Docker on the host. It checks every scenario of the two new requirements, including a restore in a new shell and a new-machine restore into an empty volume. All resources are deleted afterwards.
