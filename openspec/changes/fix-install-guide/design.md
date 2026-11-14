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
- With `requires-python = ">=3.12"`, `uv lock` re-resolves with no version changes. The only package it reports is `Removed tomli v2.4.1`, and with the version bump also `Updated catchup v0.1.0 -> v0.2.0`. `uv lock --offline` works once uv's cache has the index data; on an empty cache it fails, and `uv lock` needs PyPI. The lock diff is larger than the package list (225 lines removed, 4 added):
  - the `resolution-markers` block is deleted;
  - the 3.11 wheel lines (`cp311`, `pp311`, `graalpy311`) are dropped;
  - coverage's `toml` extra is dropped, so pytest-cov depends on `coverage` instead of `coverage[toml]`;
  - httpx2's `httpx2-jsfetch` marker becomes `sys_platform == 'emscripten'`.
- `npm install --package-lock-only --offline` after a version bump changes only the two root `version` fields of each `package-lock.json`.
- `docker compose create` with the build override builds a missing image, so it needs the Dockerfile and the sources (a clone). With only `compose.yaml`, `compose.build.yaml`, and `.env`, it fails with "open Dockerfile: no such file or directory".
- The base images (`node:24-slim`, the uv image, `python:3.12-slim-trixie`) are not stored as local images, only as BuildKit cache. A build still contacts Docker Hub and GHCR to resolve their tags. When the package files change, as the version bump does, the Dockerfile's `npm ci` downloads the frontend packages from the npm registry (it has no cache mount), and `uv sync` fetches the build backend `hatchling` from PyPI. Droid run 1 found this on 2026-11-13, when a build with `--network none` failed.
- This Mac's default `node` is v20.19.0. Node v22.17.1 is installed under nvm.

Review of the first implementation (2026-11-14): a clean-install re-run on `debian:12` and a spec review found that these plan decisions were wrong or incomplete. The decisions below are revised.
- With no `.python-version`, uv does not prefer the lowest allowed Python. When no installed interpreter satisfies `>=3.12`, it downloads the newest one: 3.15.2 with uv 0.13.8 on Debian. When it may choose among system interpreters (`UV_PYTHON_PREFERENCE=system`), it picks 3.14.6 over 3.12 on this Mac. `pydantic-core` 2.46.5 has no wheel for 3.15, so `uv sync` fails on a clean machine. Every earlier check set `UV_PYTHON=3.12`, which hid this.
- `debian:12` has no `python3` by default. The development secret command then wrote `CATCHUP_SECRET_KEY=` with an empty value and exited 0. The frontend test `src/install.test.ts` runs `python3` (any Python 3).
- The restore emptied the volume before it read the backup. With a missing, empty, or damaged backup it then started CatchUp on an empty volume and exited 0. A failed backup truncated the previous backup at the fixed path, and "make a backup first" overwrote the backup that the user wanted to restore.
- `curl` right after `docker compose up -d` can fail with an empty reply, because the server is not listening yet.
- On a new machine, `docker compose create` with the override first printed "pull access denied" for `catchup:local`, then built it. Probe, 2026-11-14, with a throwaway image built from `scratch`: with `pull_policy: never`, `create` builds a missing image without trying to pull and does not rebuild an existing one. With `pull_policy: build`, it rebuilds on every `create`.
- Fresh-eyes check of the fix plan (2026-11-14), probed in the image's Python 3.12.16:
  - Reading a backup as a `r|gz` stream and passing each member through `tarfile.data_filter` misses some truncated files. A cut inside the second member's header (29 of 2387 cut lengths of a real backup) reads as a shorter, valid archive, and `extractall` then extracts nothing. Wrapping the input in `gzip.GzipFile`, reading the tar with `mode="r|"`, and then reading the gzip stream to its end rejects every cut length, because gzip checks the length and CRC at the end.
  - With `COMPOSE_PROJECT_NAME` set, Compose finds the project's containers from any directory. `docker compose config -q` fails outside the installation directory ("no configuration file provided"), so it is a cheap first check.
  - Pasted into interactive zsh or bash, a `#` comment line inside `( … )` and a `!` inside double quotes break the block. Running the block as a file does not show this.
  - The `COMPOSE_FILE` lines create a 644 `.env` without a secret when `.env` is missing.
  - `openssl` is in macOS and in most Linux installs, but a minimal Debian may lack it.

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

### D1. Python 3.12 is the minimum, and the backend uses 3.12

- `requires-python = ">=3.12"`, and `uv lock` is regenerated, without `--upgrade`.
- A new `backend/.python-version` contains `3.12`. uv reads it in `backend/`, so `uv sync` and `uv run` use Python 3.12, the version CI and the image use, and download it when it is missing. The Dockerfile copies `backend/` into the builder stage, where uv's own Python 3.12 already matches.
- The README says "Python 3.12 or newer", and that uv installs and uses Python 3.12 for the backend, as `backend/.python-version` names, so the user does not need to install it.
- **Alternative: keep 3.11.** Rewrite the f-string and add a 3.11 CI job. Rejected: CI would get slower, the container never runs 3.11, and uv makes 3.12 effortless.
- **Alternative: an upper bound in `requires-python`.** Rejected: it would block newer Pythons for everyone, and uv would still pick the newest allowed version, which CI does not test.

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
    pull_policy: never
```

`pull_policy: never` stops Compose from trying to pull `catchup:local` from a registry. A missing image is built, and an existing one is reused unless `--build` is given (probe in "Context").

For a source build, the README says:
1. Clone the repository and change into it.
2. Create `.env`.
3. Add `COMPOSE_FILE=compose.yaml:compose.build.yaml` to `.env`, only if it is not there yet, and on a line of its own. This is a block of its own:
   ```sh
   (
     set -e
     [ -s .env ] || { echo 'Create .env with the instance secret first.' >&2; exit 1; }
     grep -qx 'COMPOSE_FILE=compose.yaml:compose.build.yaml' .env ||
       printf '\nCOMPOSE_FILE=compose.yaml:compose.build.yaml\n' >> .env
   )
   ```
   The check refuses to create `.env` without a secret. The leading newline keeps the line separate when `.env` does not end with one. A blank line in `.env` is harmless (fresh-eyes probe: Compose, `env_file`, `docker run --env-file`, and `set -a; . ./.env` accept it).
4. In a separate block, run `docker compose up -d --build --wait`. `--wait` returns once the container's health check passes, so the health command that follows answers at once.

To upgrade a source build later, run `git pull`, then `docker compose up -d --build --wait`. Before that upgrade block, the README tells existing source-build users to run step 3 first. Without the line, `up -d --build` silently keeps running their previous build. After their first build as `catchup:local`, they can remove the old local tag with `docker image rm ghcr.io/zhuoang2/catchup:latest`, so that a later switch to the published image pulls the real one.

Because Compose reads `COMPOSE_FILE` from `.env`, every later command uses `catchup:local`, including `stop`, `ps`, `create`, and `up` in the backup and restore steps.

For the published image, the README still needs only `compose.yaml` and `.env`, either from a clone or by downloading `compose.yaml`. The commands are `docker compose up -d --wait`, and to upgrade, `docker compose pull && docker compose up -d --wait`. The plain `docker run` equivalent stays next to the published-image start command and says that it is for the published image.

The `.env` file is also passed to the container (`env_file`). The `COMPOSE_FILE` variable inside the container is unused and harmless.

- **Alternative: an image variable** (`image: ${CATCHUP_IMAGE:-…}`). Rejected: it needs the same `.env` line, and a missing variable silently falls back to the published name.
- **Alternative: `compose.override.yaml`,** which Compose loads automatically. Rejected: shipping it would turn on source builds for everyone.
- **Alternative: default to `edge`.** Rejected by the user (2026-11-13). A release instead makes `latest` current.
- **Alternative: `pull_policy: build`.** Rejected: it rebuilds the image on every `create` and `up`, including in the backup and restore blocks.

### D5. Backup and restore commands

The README's backup and restore section has three blocks. Each block is one subshell that starts with `set -e`, so it stops at the first failing command without closing the user's terminal. Its first command is `docker compose config -q`, which fails outside the installation directory. Each block derives `container`, `volume`, and `image` itself. The blocks have no `#` comment lines and no `!` inside double quotes, so they also work when pasted into an interactive zsh or bash. Above the blocks, the README says: run each block from the installation directory; if the backup stops with an error, fix the cause and start CatchUp again with `docker compose up -d --wait`; if a restore stops after it emptied the volume, run the restore again with a good backup instead of starting CatchUp.

Backups are kept as separate, timestamped files in `"$HOME/catchup-backups"`, outside the checkout. A backup never writes over another one: the block stops if a file with its name already exists.

- **Back up:**
  1. `umask 077`, then `mkdir -p "$HOME/catchup-backups"` (a new directory gets mode 700);
  2. set `backup="$HOME/catchup-backups/catchup-$(date -u +%Y%m%dT%H%M%SZ).tar.gz"`, and stop unless `[ ! -e "$backup" ]`;
  3. `docker compose stop catchup`, then derive the names;
  4. write the archive to `"$backup.partial"` with the existing `tarfile` command, then `mv "$backup.partial" "$backup"`. A failed write leaves only the `.partial` file, which no restore reads;
  5. `docker compose up -d --wait`, then print the backup's path.
- **Restore into this installation:**
  1. set `backup=` to the file to restore. The block shows an example name, and the README says to replace it with a file from `ls "$HOME/catchup-backups"`;
  2. check the file with `[ -s "$backup" ]`, and stop with a message otherwise;
  3. derive the names (this works while the service runs);
  4. check the whole archive in the image, with `--network none`, before anything is stopped or deleted. The check reads the gzip stream to its end and passes every member through `tarfile.data_filter(member, "/data")`, the filter the extraction uses:
     ```sh
     docker run --rm --network none -i --entrypoint python "$image" \
       -c 'import gzip, shutil, sys, tarfile; f = gzip.GzipFile(fileobj=sys.stdin.buffer); t = tarfile.open(fileobj=f, mode="r|"); [tarfile.data_filter(m, "/data") for m in t]; shutil.copyfileobj(f, open("/dev/null", "wb"))' \
       < "$backup"
     ```
     A missing, empty, truncated, or unsafe archive fails here;
  5. `docker compose stop catchup`;
  6. empty the volume, including hidden files, with the existing one-line Python command;
  7. extract with the existing `tarfile` command;
  8. `docker compose up -d --wait`.

  "Make a backup first" stays above the block. It is now safe, because the new backup gets its own name.
- **Restore on a new machine:** set up the same install path as in "Run with Docker", but skip the secret step: copy the same `.env` (mode 600) instead. For the published image, that is `compose.yaml`. For a source build, it is a clone, because `create` builds the image. Copy the backup into `"$HOME/catchup-backups"`. Then:
  1. set `backup=` and check the file with `[ -s "$backup" ]`, as in the restore block;
  2. `docker compose create`;
  3. derive the names;
  4. check the archive with the same command as the restore block;
  5. check in the image that `/data` in the volume is empty (`any(Path("/data").iterdir())` is false), and stop with a message that points to "Restore into this installation" otherwise;
  6. extract;
  7. `docker compose up -d --wait`.

The text keeps the warnings that apply: back up `.env` separately, keep the same secret, and bind mounts must be writable by UID 999.

- **Alternative: keep one fixed backup path, and tell users to rename the file before restoring.** Rejected: a forgotten rename loses the backup, and a failed backup still has to avoid truncating it.
- **Alternative: check the archive on the host with `tar -tzf`.** Rejected: the extraction's `data` filter can reject members that `tar` accepts. Checking in the image uses the same Python and the same filter.
- **Alternative: check with a plain `r|gz` stream.** Rejected: some truncated archives pass it (fresh-eyes probe in "Context").

### D6. Smaller README fixes

- **Health address.** Show `curl http://localhost:8000/api/health`, which answers `{"status":"ok"}`, in "Run with Docker", after a start with `--wait`. In the source steps, use `http://127.0.0.1:8000/api/health`.
- **Allowed hosts wording.** Say that `127.0.0.1` must stay in `CATCHUP_ALLOWED_HOSTS` for the container health check, and that `localhost` must stay for local browser access.
- **Secrets.** Both paths generate the secret with `openssl rand -hex 32` and write `.env` once. Both prerequisite lists name `openssl`: macOS and most Linux installs include it, and on Debian or Ubuntu it is `apt install openssl`. The commands:
  - Docker: `(umask 077; set -C; key="$(openssl rand -hex 32)" && printf 'CATCHUP_SECRET_KEY=%s\n' "$key" > .env)`;
  - development: in the same kind of subshell, `{ grep -v '^CATCHUP_SECRET_KEY=' .env.example; printf 'CATCHUP_SECRET_KEY=%s\n' "$key"; } > .env`.

  `set -C` (noclobber) makes the redirect fail when `.env` already exists, so a repeated command never replaces a secret. When `openssl` is missing or fails, `&&` stops before anything is written. The README says both things, and that an existing `.env` should be kept, or moved away on purpose, because a new secret makes saved model keys unreadable.
- **Development prerequisites.** "Development setup" starts with `git clone https://github.com/Zhuoang2/catchup` and `cd catchup`, and lists git, uv, and Node.js. It says that the frontend tests run `python3` from `PATH` (any Python 3).
- **Database path.** The source checkout keeps its database at `backend/data/catchup.sqlite3`: the default `CATCHUP_DATA_DIR=./data`, relative to the directory the backend starts in, which is `backend/` in these steps. The text that moves a source-checkout database into the volume names this path, and says to stop the development backend first so that the database file is complete.

### D7. Version 0.2.0, and the release after the merge

- **Version fields.** Set `0.2.0` in:
  - `backend/pyproject.toml`, then refresh `uv.lock`, where the `catchup` package entry changes;
  - `frontend/package.json` and `extension/package.json`, then refresh their `package-lock.json` files with `npm install --package-lock-only`;
  - `extension/public/manifest.json`;
  - the README's User-Agent example.
- **Release.** The tag and the GitHub release are not part of the implementation. After the merge, Claude Code asks the user to confirm. It then pushes `v0.2.0` on the merge commit and creates a release whose notes summarize the changes since v0.1.0. It checks once that the release workflow published `0.2.0` and `latest` for both platforms.

### D8. Test seams

A new `backend/tests/test_install_docs.py` reads the README and the configuration files, as `test_readme_context.py` does. It checks:
- that the stated minimum versions match the configuration, including `backend/.python-version`;
- that the Compose files are split as in D4;
- that the README names that setup and the health address;
- that the version fields agree;
- for the review fixes, the shape of the command blocks: for example `set -C` and `openssl` in both secret blocks, `set -e` and the order "check, stop, empty, extract" in the restore block.

The command blocks themselves are checked by running them, including their failure paths, not by unit tests: tasks 3.1 and 4.3, and the review re-run (design "Migration Plan").

## Risks / Trade-offs

- [A user on Python 3.11, or on a Python newer than CI tests] → The README requires uv. `backend/.python-version` makes uv use Python 3.12, and download it when it is missing.
- [Existing source-build users of `docker compose up -d --build`] → Without the new `.env` line, `up -d --build` has nothing to build. It starts silently, with no warning, from the image already tagged `ghcr.io/zhuoang2/catchup:latest` on that machine, which is their previous source build (probe, 2026-11-13). So the upgrade does not happen. The README's upgrade text tells source-build users to add the line first. The data volume is unaffected either way.
- [`uv lock` needs network access] → It is a one-time step in the implementation. The task records the package diff, which must show only the `tomli` removal and the version change.
- [The emptying command deletes data] → It runs only in the restore block, after the whole backup was checked and the service stopped. A new backup made first gets its own file.
- [`set -e` inside a subshell] → A failing step stops the block and may leave CatchUp stopped. The README says how to start it again.

## Migration Plan

- No data migration.
- Users who build from source with Docker add `COMPOSE_FILE=compose.yaml:compose.build.yaml` to `.env`.
- To roll back, revert the commit. A published release stays published.

At review, Claude Code runs:
- the Docker smoke script;
- a second clean-install run by a fresh sub-agent that sees only the new README, on a clean `debian:12` container and with Docker on the host. It checks every scenario of the two new requirements, including a restore in a new shell and a new-machine restore into an empty volume. All resources are deleted afterwards.
