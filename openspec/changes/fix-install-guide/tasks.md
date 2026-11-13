# Tasks

Implementer notes:
- **Read first.** Read `proposal.md`, `design.md` (D1–D8, including the probe results under "Context"), and `specs/local-deployment/spec.md`. If something looks wrong or contradictory, stop and report instead of redesigning.
- **Work test-first with the `tdd` skill** (D-016). For each group, first write its tests and watch them fail, then make the change. The seams count as agreed:
  - `backend/tests/test_install_docs.py`, which reads files as `backend/tests/test_readme_context.py` does;
  - running the README's commands (task 3.1).
- **Test rules.**
  - Find files from the repository root: `Path(__file__).resolve().parents[2]`.
  - Use `tomllib` for `pyproject.toml` and `json` for the JSON files. For YAML, use plain text checks; do not add a YAML dependency.
  - The README is hard-wrapped. Before matching a phrase, collapse runs of whitespace in the README text to single spaces.
  - When a file the test needs does not exist yet, the test fails with an assertion message, not a `FileNotFoundError`.
  - No network in tests.
  - Some checks already pass today. Mark them as *guard* in a comment and in the test report.
- **Network.**
  - Lock refreshes in 1.2 may use PyPI and the npm registry, but only if the offline form fails.
  - Docker builds in 3.1 and 3.2 may contact Docker Hub, GHCR, PyPI, and the npm registry. Build normally, with the network on; do not try an offline build first.
    - The base images exist only as BuildKit cache, so their tags are resolved online.
    - The version bump changes the package files, so the Dockerfile's `npm ci` downloads the frontend packages again (about 108 MB unpacked), and `uv sync` fetches the build backend `hatchling` from PyPI. This happens once; later builds reuse the layer cache.
  - Nothing else may use the network.
- **Deleting.** Do not delete files, directories, or Docker images yourself. The only removal command you run is `docker compose down -v` for the `readme-check` project, as 3.1 says. In the test report, list everything else you created that should be removed (the temporary directories, the `catchup:local` and `catchup:fix-install-guide-local` images). Claude Code removes them at review.
- **Node.js.** This machine's default `node` is v20.19.0, below the new minimum. Run every `npm` command under Node 22, for example `source ~/.nvm/nvm.sh && nvm use 22` (v22.17.1), and record `node --version` in the test report.
- **Never touch these:**
  - the containers `catchup-e2e` (port 8800) and `catchup-e2e-d034789`;
  - the volumes `catchup-e2e` and `catchup-e2e-bak-d034789`;
  - the images `catchup:main-064d3a9` and `catchup:main-d034789`.

  Never run `docker system prune`, `docker volume prune`, `docker image prune`, or `docker builder prune`. Do not write to the real `$HOME`, except for tool caches.
- **Out of scope:**
  - application code (`backend/src/`, `frontend/src/`, `extension/src/`);
  - the Dockerfile and `.github/workflows/`;
  - `docs/alpha-release.md`;
  - every README section other than "Development setup" and "Run with Docker", apart from the User-Agent example (task 2.2).

  `backend/tests/test_readme_context.py` checks phrases in "Supported sources". `extension/src/test/docs.test.ts` splits the README at `## Browser extension` and `## X accounts`, and needs `](#x-accounts)`. Do not rename or reorder headings.
- **Commits.** Commit after each task group. Do not push, tag, or create a release.

## 1. Configuration: Python minimum, Compose files, version

- [x] 1.1 In the new `backend/tests/test_install_docs.py`, add these failing tests:
  1. **Python minimum matches the build.** The minimum in `requires-python` (the version after `>=`) equals three other versions, and all of them are `3.12`:
     - the version `.github/workflows/ci.yml` installs (`python-version`);
     - the version in the Dockerfile's final `FROM python:<version>-…` line;
     - the `requires-python` value at the top of `backend/uv.lock`.
  2. **Compose split.** Check that:
     - `compose.yaml` contains `image: ghcr.io/zhuoang2/catchup:latest`, and no line whose stripped text starts with `build:`;
     - `compose.build.yaml` exists and contains `image: catchup:local` and `build: .`, under `services:` → `catchup:`.
  3. **One version everywhere.** These are all `0.2.0`:
     - the `version` in `backend/pyproject.toml`, `frontend/package.json`, `extension/package.json`, and `extension/public/manifest.json`;
     - the top-level `version` and `packages[""].version` in `frontend/package-lock.json` and `extension/package-lock.json`;
     - the `version` of the `catchup` package entry in `backend/uv.lock`.

  Verify: all three fail before 1.2 on an assertion: 3.11 instead of 3.12, the `build:` line or the missing file, and `0.1.0`.
- [x] 1.2 Make the changes (design D1, D4, D7). Bump the versions first, then refresh each lock file once:
  - in `backend/pyproject.toml`, set `requires-python = ">=3.12"` and `version = "0.2.0"`. Then run `UV_PYTHON=3.12 uv lock --offline` in `backend/`. If that fails, run `UV_PYTHON=3.12 uv lock` without `--upgrade`;
  - set the `"version"` key, and only that key, to `0.2.0` in `frontend/package.json`, `extension/package.json`, and `extension/public/manifest.json`. Do not touch dependency ranges such as `"vitest-axe": "^0.1.0"`. Then run `npm install --package-lock-only --offline` in `frontend/` and in `extension/`, or without `--offline` if that fails;
  - remove `build: .` from `compose.yaml`;
  - add `compose.build.yaml` exactly as in D4.

  Verify:
  - the 1.1 tests pass;
  - uv reports only `Updated catchup v0.1.0 -> v0.2.0` and `Removed tomli v2.4.1`. The `uv.lock` diff matches the list under design "Context": the version, `requires-python`, the deleted `resolution-markers` block, the dropped 3.11 wheels, the `tomli` and coverage-`toml` removals, and the `httpx2-jsfetch` marker;
  - each `package-lock.json` diff changes only its two root `version` fields.

    If uv reports any other package change, or an npm lock changes anything else, stop and report. Record the diff stats in the test report.
  - `UV_PYTHON=3.12 uv run pytest` passes in `backend/`.
  - `docker compose -f compose.yaml config --images` prints `ghcr.io/zhuoang2/catchup:latest`.
  - `docker compose -f compose.yaml -f compose.build.yaml config --images` prints `catchup:local`.

## 2. README

- [x] 2.1 In `backend/tests/test_install_docs.py`, add these failing tests on `README.md`, with whitespace collapsed:
  1. **Versions.** The README:
     - states "Python X.Y or newer", where X.Y is the minimum from `requires-python`;
     - states "Node.js 22.12 or newer" and links `https://nodejs.org`;
     - does not contain "3.11" in the "Development setup" section.

     *Guard:* the Node.js major version that `.github/workflows/ci.yml` installs is at least 22.
  2. **Source steps.** The "Development setup" section:
     - names `backend/data/catchup.sqlite3`;
     - runs `npm run build` before the first command that starts the backend (`uv run catchup serve` or `uv run uvicorn`).
  3. **Docker source build.** The README contains:
     - `COMPOSE_FILE=compose.yaml:compose.build.yaml`;
     - `catchup:local`;
     - a `git clone https://github.com/Zhuoang2/catchup` line.
  4. **Health address.** The README contains `/api/health` and `{"status":"ok"}`.
  5. **Private files.** The README contains:
     - `umask 077` in the same command as the Docker `.env` `printf` line;
     - `umask 077` in the development `.env` commands;
     - `umask 077` in the backup block;
     - the backup path `"$HOME/catchup-data.tar.gz"`;
     - `docker compose create`.
  6. **Version example.** The User-Agent example reads `CatchUp/<version>`, with the version from `backend/pyproject.toml`.

  Verify: every test except the guard fails before 2.2 on an assertion, for missing or old text.
- [x] 2.2 Rewrite the README sections "Development setup" and "Run with Docker" (design D1–D6, and the source-build upgrade note under design "Risks"), and update the User-Agent example (D7). The new text must say:
  - **D1:** uv fetches Python 3.12 when the system's Python is older.
  - **D4:**
    - how to get `compose.yaml` for the published image;
    - the clone, the `COMPOSE_FILE` line, and `docker compose up -d --build` for a source build;
    - for a source-build upgrade, `git pull`, then `docker compose up -d --build`;
    - that existing source-build users must add the line first, or `up -d --build` silently keeps running their previous build.
  - **D5:** for a source build, the new-machine restore needs a clone.

  Keep the rest of the README unchanged.

  Verify:
  - the 2.1 tests pass;
  - `UV_PYTHON=3.12 uv run pytest` passes in `backend/`;
  - `npm test -- --run` passes in `extension/` under Node 22 (its docs test reads the README; run `npm ci` there first if needed).

## 3. Run the commands, checks, and report

- [ ] 3.1 Run the README's Docker commands as a user would, from a clone of the branch:
  - **Clone.** Clone your committed branch into a temporary directory outside the repository: `git clone <worktree path> <tmp>/readme-check`.
  - **Run each block in a new shell.** First save `REAL_DOCKER_CONFIG="$HOME/.docker"`. Write each README block, exactly as it appears, to its own file, then run it with `env HOME=<tmp home> DOCKER_CONFIG="$REAL_DOCKER_CONFIG" COMPOSE_PROJECT_NAME=readme-check bash <block file>`. Do not use `bash -c '…'`, because the blocks contain single quotes. Port 8000 on this machine is free.
  - **File modes.** Check them with `stat -f %Lp <file>` (expect `600`), not with `ls -l`.

  Check and record each item:
  1. Source build:
     - create `.env` with the README's command; its mode is 600, and the command printed nothing;
     - add the `COMPOSE_FILE` line and run `docker compose up -d --build`;
     - `docker image inspect catchup:local` succeeds;
     - first record whether `ghcr.io/zhuoang2/catchup:latest` exists locally, and check that the build did not create or change it;
     - the README's health command answers `{"status":"ok"}`.
  2. Backup and restore:
     - change one preference through the API: `GET`, then `PUT /api/settings/preferences` with the header `Origin: http://localhost:8000`;
     - run the backup block; the file is at `<tmp home>/catchup-data.tar.gz` with mode 600;
     - after the backup, change the same preference again, and add a marker file to the volume, for example `docker run --rm -v <volume>:/data --entrypoint python catchup:local -c "open('/data/after-backup.marker','w').close()"`;
     - run the restore block; the backed-up preference is back, and `/data/after-backup.marker` no longer exists.
  3. New-machine restore:
     - run `docker compose down -v`, which removes the container and the volume; check that the `readme-check` volume is gone;
     - run the new-machine restore block from the clone; a new volume is created, CatchUp starts, and the backed-up preference is there.

     The image stays, because you do not delete images (see "Deleting"). The design probe showed that `docker compose create` builds a missing image, and the review re-run on a clean machine covers that path. Say so in the test report.
  4. Development secret: in a temporary directory with a copy of `.env.example`, run the README's development `.env` commands. The mode is 600, nothing was printed, and `CATCHUP_SECRET_KEY` has exactly one non-empty line. Do not print the value.
  5. Built frontend: in the clone, follow the README's source order. Under Node 22, run `npm ci` and `npm run build` in `frontend/`. Then start the backend as the README says, with the environment loaded, using `uv run catchup serve --port <free port>`. Check that `/` answers 200 with HTML, then stop it.

  **Clean up afterwards:** run `docker compose down -v` for the `readme-check` project, and stop any backend you started. Record that in the test report, and list what is left for Claude Code to remove: the `catchup:local` image and the full paths of the temporary directories, including the temporary home.

  Verify: every item passes. If a README command fails as written, fix the README and repeat that item.
- [ ] 3.2 Run the full checks, with `npm` under Node 22:
  - `UV_PYTHON=3.12 uv run pytest` in `backend/`;
  - `npm test -- --run` and `npm run build` in `frontend/`;
  - `npm test -- --run` in `extension/`;
  - `DO_NOT_TRACK=1 openspec validate fix-install-guide --strict`;
  - `docker build -t catchup:fix-install-guide-local .`, then `scripts/docker-smoke.sh catchup:fix-install-guide-local`.

  Write the commands and their real results to `docs/process/test-report-fix-install-guide.md`. It contains:
  - the Node.js and Python versions used;
  - the lock diff stats from 1.2;
  - every item of 3.1 with its result;
  - a mapping from each scenario of the two new requirements to its tests or 3.1 items;
  - the guard checks;
  - the review re-run on a clean `debian:12` container (design "Migration Plan") as not performed. That run is what checks the minimum versions on a clean machine.

  Add your entry to `docs/process/ai-usage-log.md` after the latest entry, with a faithful prompt excerpt. Leave out the session id; Claude Code adds it at review.

  Verify: every command passes, and the report has the actual numbers.
