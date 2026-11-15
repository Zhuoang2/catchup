# Proposal

## Why

On 2026-11-13, a fresh agent installed CatchUp by following only the README, at `064d3a9`, on a clean Debian 12 container and with Docker on macOS (#13). The app installed and ran both ways, but a new user would get stuck or need outside knowledge in four places:

- **Python 3.11 cannot run the tests.** The README says "Python 3.11 or newer", but `uv run pytest` stops while collecting tests on 3.11. `tests/test_discovery.py:258` uses f-string syntax that needs 3.12. CI and the image use 3.12, so nothing caught it.
- **The built frontend is not served until a restart.** The README starts the backend first and builds the frontend afterwards. The backend checks for `frontend/dist` only at startup, so the page answers 404 until the backend is restarted.
- **The default image is old.** The plain `docker compose up -d` starts v0.1.0, from 2026-10-04, 456 commits behind `main`. And because `compose.yaml` has both `image: …:latest` and `build: .`, a source build is tagged locally as the published `latest`.
- **Restore does not work on its own.** The restore line uses variables from the backup lines and fails in a new shell. There is no command to empty the volume, and no way to restore on a new machine.

Smaller gaps:

- the health address is not named;
- the Node.js version names no install source, and Debian's package is too old;
- `.env` and the backup are readable by other users, and the backup lands in the checkout;
- the development secret is printed on screen;
- the source checkout's database path is not given;
- the Docker section never says to get the repository first.

## What Changes

- **Python 3.12 is the minimum.** This changes `requires-python` and `uv.lock`, where `tomli`, a 3.11 backport, drops out, and the README. With uv, a machine that has only 3.11 gets 3.12 automatically.
- **Node.js 22.12 or newer.** The README says that distribution packages can be older, and where to get Node.js instead.
- **The README builds the frontend before the backend starts**, or tells the user to restart the backend after a build.
- **Source builds no longer use the published image's name.**
  - `compose.yaml` keeps only the published image.
  - A new `compose.build.yaml` adds the source build under the local name `catchup:local`.
  - The README turns it on with one line in `.env` (`COMPOSE_FILE=compose.yaml:compose.build.yaml`), so every later Compose command uses the same image.
- **Backup and restore get separate commands**, each of which works on its own:
  - a backup written outside the checkout, readable only by its owner;
  - a restore into the stopped service's volume, with a command to empty it first;
  - a restore on a new machine into a new, empty volume.
- **Smaller README fixes:**
  - the health address and its answer;
  - the health-check wording;
  - `.env` created readable only by its owner, in both paths;
  - a development secret step that writes the secret into `.env` without printing it;
  - the source checkout's database path;
  - a clone step for the Docker source build.
- **Version 0.2.0** in `backend/pyproject.toml`, `uv.lock`, `frontend/package.json`, `extension/package.json`, `extension/public/manifest.json`, their lock files, and the User-Agent example in the README.
- **After the merge, the v0.2.0 release.** With the user's confirmation at that point, Claude Code pushes the `v0.2.0` tag. The existing release workflow then publishes the `0.2.0`, `0.2`, and `latest` images. This step is not part of the implementation.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `local-deployment`: two new requirements.
  - "Install from the README on a clean machine": stated minimum versions that run everything, the frontend build order, a source-built image under its own name, the health address, and `.env` readable only by its owner.
  - "Back up and restore the data volume": commands that work on their own, a private backup outside the checkout, and a restore on a new machine.

## Impact

- **Changed:**
  - `README.md`, `compose.yaml`, and the new `compose.build.yaml`;
  - `backend/pyproject.toml` and `backend/uv.lock`;
  - the version fields listed above;
  - a new docs test, `backend/tests/test_install_docs.py`.
- **Unchanged:** application code, the Dockerfile, CI, and the release workflow. The Docker smoke script tests an image tag, not Compose, so it does not change.
- **Users:**
  - Installs from source on Python 3.11 now get 3.12 through uv.
  - Docker users who build from source add one line to `.env`.
  - Users of the published image change nothing. After the release, `latest` is current.
- **Docs:**
  - a decision log entry (D-028), a requirements-changes row, the test report, and the AI usage log;
  - `docs/alpha-release.md` is a submitted course document and stays as it is.
