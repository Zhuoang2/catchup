# Test report: fix-install-guide

Date: 2026-11-13. Started at `252714e`, on `fix-install-guide`.

## Environment and network

- Python 3.12.13, selected with `UV_PYTHON=3.12`.
- Node.js v22.17.1, npm 10.9.2, selected before every npm command with
  `source ~/.nvm/nvm.sh && nvm use 22`.
- uv installs and test runs use `UV_OFFLINE=1`; npm installs use offline mode.
  No registry access was needed for the lock refreshes.
- Group 3 resumed from `ce01211` in the review checkout after the plan's
  network and cleanup corrections. Docker builds ran normally, with access
  to Docker Hub, GHCR, PyPI, and the npm registry. All non-Docker installs
  used existing caches, with no external network in tests.
- The unchanged Dockerfile uses Node 24 and Python 3.12 images. Its build log
  selected Python 3.12.16. Local checks used Python 3.12.13 and Node v22.17.1,
  not an exact Node 22.12.0 minimum-version installation.

## Group 1: configuration

New tests in `backend/tests/test_install_docs.py` first failed as intended:
`UV_PYTHON=3.12 UV_OFFLINE=1 uv run pytest tests/test_install_docs.py -q`
reported **3 failed** (3.11 instead of 3.12, the base Compose `build:` line,
and version 0.1.0).

Commands and results:

| Command | Result |
| --- | --- |
| `UV_PYTHON=3.12 uv lock --offline` (backend) | 63 packages resolved; only `Updated catchup v0.1.0 -> v0.2.0` and `Removed tomli v2.4.1` |
| `npm install --package-lock-only --offline` (frontend, Node 22) | Passed; 168 packages audited |
| `npm install --package-lock-only --offline` (extension, Node 22) | Passed; 164 packages audited |
| `UV_PYTHON=3.12 UV_OFFLINE=1 uv run pytest` (backend) | **899 passed**, 25.40 s |
| `docker compose -f compose.yaml config --images` | `ghcr.io/zhuoang2/catchup:latest` |
| `docker compose -f compose.yaml -f compose.build.yaml config --images` | `catchup:local` |

Lock diff stats (`git diff --numstat`):

| File | Added | Removed |
| --- | ---: | ---: |
| `backend/uv.lock` | 4 | 225 |
| `frontend/package-lock.json` | 2 | 2 |
| `extension/package-lock.json` | 2 | 2 |

Parsed old/new locks were compared independently. Both npm locks differ only
in their two root version fields. The uv lock differs only in the project
version, Python minimum, deleted resolution markers, removed 3.11-only
wheels, removed tomli and coverage toml extra, and the httpx2-jsfetch marker.
Compatible cp311-abi3 wheels remain. An initial ad hoc checker incorrectly
excluded those compatible wheels; after correcting that checker, the exact
allowed-diff comparison passed. No additional dependency changed.

Diagnosis ranked metadata/instruction drift first, dependency incompatibility
second, and an application defect third. The failing configuration assertions
and green suite after metadata-only changes confirm drift for this group.

## Group 2: README

The seven new README checks first produced **6 failed, 4 passed** (including
the three group-1 tests). All six failures were assertions about missing or
old text. The CI Node-major check is a **guard**: it passed before the README
changed, because CI already installs Node 24.

| Command | Result |
| --- | --- |
| `UV_PYTHON=3.12 UV_OFFLINE=1 uv run pytest tests/test_install_docs.py -q` before edits | 6 failed, 4 passed, 0.07 s |
| `UV_PYTHON=3.12 UV_OFFLINE=1 uv run pytest` after edits | **906 passed**, 22.32 s |
| `npm ci --offline --no-audit --no-fund` (extension, Node 22) | Passed; 120 packages installed from cache |
| `npm test -- --run` (extension, Node 22) | **114 passed**, 8 files, 2.18 s |

An independent comparison removed the two editable README sections from old
and new text and verified that everything else is identical except for the
User-Agent version example. Existing `test_readme_context.py` and extension
docs tests pass. The confirmed cause remains documentation drift; application
code, dependency ranges, Dockerfile, CI, and submitted course documents are
unchanged.

## Earlier stop and corrected plan

The first attempt at 3.1 used `docker build --network none -t catchup:local .`
under the original base-image-only network allowance. It exited 1 because
`uv sync --locked --no-editable` attempted to resolve `hatchling` at
`https://pypi.org/simple/hatchling/`. Its frontend `npm ci` was canceled.
No tagged image or Compose resources were left. The temporary-directory
cleanup was then refused by the execution permission gate.

Claude Code removed that earlier temporary directory and committed `ce01211`,
allowing build-time dependency downloads and leaving host files and images
for review cleanup. This was a plan error, not an application defect. The
resumed run did not retry an offline Docker build.

## Group 3.1: README commands

Fresh local clone command, run from the review checkout:

```sh
git clone /private/tmp/claude-501/-Users-madivhkassel-Desktop-Stanford-Fall-2026-CS-146S/fecc26ac-03ed-4f62-bdd5-ba35b7996c52/scratchpad/review-13 /private/tmp/catchup-install-guide-resume-0kmtb1fk/readme-check
```

The clone's HEAD was verified as
`ce01211f92e17c04f39a22a353d91af001bd223c`. Before changing `HOME`, the
runner saved the real Docker config path, `/Users/madivhkassel/.docker`.
Each README shell block was extracted unchanged into a separate file under
`/private/tmp/catchup-install-guide-resume-0kmtb1fk/blocks/`. The relevant
blocks ran in independent shells with this invocation pattern, from the clone:

```sh
env HOME=/private/tmp/catchup-install-guide-resume-0kmtb1fk/home \
  DOCKER_CONFIG=/Users/madivhkassel/.docker \
  COMPOSE_PROJECT_NAME=readme-check bash <absolute-block-file>
```

No `bash -c` wrapping was used. Backup, existing-install restore, and
new-machine restore inherited no `container`, `volume`, or `image` variables.
The remote clone was replaced by the task's required local clone. Published
image downloads, pulls, and remote upgrades were not exercised, since only
Docker builds may use external networking in this implementation run.

| Item | Commands/checks and real result |
| --- | --- |
| 3.1.1, secret | Exact Docker `.env` block passed; stdout and stderr both empty. `stat -f %Lp <clone>/.env` returned **600**. No secret was displayed. |
| 3.1.1, build | Exact block appended `COMPOSE_FILE=compose.yaml:compose.build.yaml`, then ran `docker compose up -d --build`. Exit **0**. `docker image inspect catchup:local` succeeded. |
| 3.1.1, image isolation | Published `ghcr.io/zhuoang2/catchup:latest` was absent before the build, after the build/restores, and after the final smoke run. It was neither created nor changed. Container inspection showed the local image ID. |
| 3.1.1, health | Exact `curl http://localhost:8000/api/health` block returned **`{"status":"ok"}`**. |
| 3.1.2, preference and backup | `GET /api/settings/preferences`, then `PUT` with `Origin: http://localhost:8000`, saved `digest_language=zh-Hans`. Exact backup block passed in a new shell. Backup was in the temporary home, outside the clone; `stat -f %Lp` returned **600**. |
| 3.1.2, post-backup data | Another `PUT` set the language to `en`. Added and checked `/data/after-backup.marker` and `/data/.after-backup-hidden` in only the readme-check service's volume. |
| 3.1.2, restore | Exact existing-install restore block passed in another new shell. The entire preferences response matched the backup's response, including `zh-Hans`. Both visible and hidden post-backup markers were absent. |
| 3.1.3, empty-volume setup | `docker compose down -v` exited **0**. Inspection confirmed `readme-check_catchup-data` no longer existed and the project had no container. The local image was retained, as the updated task requires. |
| 3.1.3, new-machine restore | Exact `docker compose create` / restore / `up -d` block passed in a new shell. A different container and a new named volume were created, the service became ready, and the backed-up preferences were present. Container inspection again matched `catchup:local`. |
| 3.1.4, development secret | In a separate temporary directory with a copy of `.env.example`, the exact development secret block passed with empty stdout/stderr. `stat -f %Lp` returned **600**. Exactly one non-empty `CATCHUP_SECRET_KEY=` line existed; its value was not displayed. |
| 3.1.5, frontend order | In the clone, created the development environment, then ran the exact frontend block, `npm ci` followed by `npm run build`, under Node **v22.17.1**. Cache-only install added **124** packages. Build passed: **40** modules transformed; Vite build **234 ms**. |
| 3.1.5, backend startup | Then ran the backend block: `uv sync`, load `.env`, `uv run catchup serve --port 59101` (the task permits a free port). Runtime **Python 3.12.13**. `/` returned **200 text/html**, `/api/health` returned the stated JSON, and `backend/data/catchup.sqlite3` existed. |
| Cleanup | Final `docker compose down -v` removed the readme-check container, network, and volume. The temporary backend process group was terminated and exited; a connection probe confirmed it no longer accepted connections. No host files/directories or Docker images were manually deleted. |

The new-machine check deliberately reused the image. Building a missing
image via `docker compose create` is supported by the design probe; the
independent clean-machine review re-run covers that path, not this run.

One extra harness assertion failed after successful backend shutdown:
immediately binding the recently used port without address reuse returned
`Address already in use`, consistent with TCP TIME_WAIT. This was not a README
command failure. The backend log confirmed completed shutdown, the process
group had exited, and the follow-up connection probe was refused. No
application or README change was made for that harness-only issue.

## Group 3.2: full checks

Commands ran from the corresponding directories in the review checkout.
Local Python commands set `UV_PYTHON=3.12 UV_OFFLINE=1`. Local npm commands
first ran `source ~/.nvm/nvm.sh && nvm use 22` and recorded
`node --version` as **v22.17.1**; npm was **10.9.2**.
For cache-only installs, the environment set `npm_config_offline=true`,
`npm_config_audit=false`, and `npm_config_fund=false`. Tests and local
installs used the temporary home, with the real uv/npm cache directories
explicitly selected.

| Command | Actual result |
| --- | --- |
| `UV_PYTHON=3.12 UV_OFFLINE=1 uv run pytest` (backend) | Exit **0**; **906 passed**, **30.49 s**, Python **3.12.13** |
| `npm ci` (frontend, offline environment) | Exit **0**; **124** packages installed from cache |
| `npm test -- --run` (frontend, Node 22) | Exit **0**; **281 passed**, **14 files**, **6.87 s** |
| `npm run build` (frontend, Node 22) | Exit **0**; TypeScript check passed; **40** modules transformed; Vite build **273 ms** |
| `npm ci` (extension, offline environment) | Exit **0**; **120** packages installed from cache |
| `npm test -- --run` (extension, Node 22) | Exit **0**; **114 passed**, **8 files**, **4.07 s** |
| `DO_NOT_TRACK=1 openspec validate fix-install-guide --strict` | Exit **0**; `Change 'fix-install-guide' is valid` |
| `docker build -t catchup:fix-install-guide-local .` | Exit **0**; dependency/build layers reused from the successful source build |
| `scripts/docker-smoke.sh catchup:fix-install-guide-local` | Exit **0**; all **12** existing smoke checks passed |

Smoke checks covered container health, API health, root HTML, manifest,
service worker, offline page, preference saving, framing protection,
non-root execution, the database volume, exclusion of secrets/backend
source, and preference persistence across restart. The existing script's
own trap cleaned up its smoke container and volume. No manual Docker
removal command was used other than readme-check's `docker compose down -v`.

The new permanent tests are the **10** checks in `test_install_docs.py`
(**9** initially failing checks and **1 guard**). The backend suite's other
tests, all frontend/extension tests, and the smoke script already existed.
Command-run assertions in 3.1 were additional temporary verification checks.

## Scenario mapping and guard checks

| Requirement / scenario | Evidence |
| --- | --- |
| Install: source checkout on minimum versions | `test_python_minimum_matches_ci_image_and_lock`, `test_readme_states_supported_runtime_minimums`, Node-major guard; 3.1.5 installs/startup and 3.2 backend/frontend suites/build on Python 3.12.13 and Node 22.17.1. Exact minimum versions on a clean OS remain for review. |
| Install: built frontend is served | `test_readme_builds_frontend_before_starting_backend_and_names_database`; 3.1.5 verifies 200 HTML at first backend startup after the build. |
| Install: source build keeps published image name free | `test_compose_separates_published_image_and_source_build`, `test_readme_explains_local_docker_source_build`; 3.1.1 image inspection and 3.1.2/3 Compose commands all use the same local image. |
| Install: health address | `test_readme_names_health_address_and_response`; exact health block in 3.1.1, source health in 3.1.5, existing Docker smoke check. |
| Install: private instance secret | `test_readme_creates_private_env_and_backup_files`; 3.1.1 and 3.1.4 assert mode 600 and empty output, plus one non-empty development secret line. |
| Backup: restore in a new shell | 3.1.2 independently runs backup and restore, compares API preferences, and proves visible and hidden post-backup files were removed. |
| Backup: restore on a new machine | 3.1.3 proves old-volume removal, new-volume creation, local-image reuse, service startup, and recovered preferences. Missing-image creation is reserved for review, as the updated task states. |
| Backup: private backup outside checkout | `test_readme_creates_private_env_and_backup_files`; 3.1.2 verifies the actual temporary-home path, mode 600, and absence of a backup in the clone. |

The explicitly marked guard is `test_ci_node_major_supports_documented_minimum`:
CI already used Node 24 before this change. Existing backend README-context
and extension docs tests also remain passing compatibility guards. Version
agreement and the User-Agent example are covered by the two new release
version checks; the database-path check is also exercised in 3.1.5.

## Review handoff and retained artifacts

The independent review re-run on a clean `debian:12` container is **not
performed** in this implementation run. That review run checks the stated
minimum versions on a clean machine, including a missing-image new-machine
restore. It is not replaced by these cached macOS installs.

Claude Code should remove these artifacts at review. They were deliberately
left in place under the revised deletion rule:

- Temporary root (contains all block files, logs, state, and the following
  subdirectories): `/private/tmp/catchup-install-guide-resume-0kmtb1fk`
  - Clone, including its dependencies, built frontend, `.env`, and test
    database: `/private/tmp/catchup-install-guide-resume-0kmtb1fk/readme-check`
  - Private temporary home and backup:
    `/private/tmp/catchup-install-guide-resume-0kmtb1fk/home`
    (`/private/tmp/catchup-install-guide-resume-0kmtb1fk/home/catchup-data.tar.gz`)
  - Development-secret fixture:
    `/private/tmp/catchup-install-guide-resume-0kmtb1fk/development-secret`
  - Extracted shell blocks:
    `/private/tmp/catchup-install-guide-resume-0kmtb1fk/blocks`
- Docker image `catchup:local`,
  ID `sha256:42c5b9d5a0a364823afdbd182c8c79257a1edc5fd956a5e0ba35825c5f09fb40`.
- Docker image `catchup:fix-install-guide-local`,
  ID `sha256:d44b6f67990d4111cbe707cc151c24af6c4c3a4eba3698813c23b345c105ae61`.

The checks also generated these ignored paths in the review checkout,
retained for review and eligible for cleanup afterwards:

- `/private/tmp/claude-501/-Users-madivhkassel-Desktop-Stanford-Fall-2026-CS-146S/fecc26ac-03ed-4f62-bdd5-ba35b7996c52/scratchpad/review-13/backend/.venv`
- `/private/tmp/claude-501/-Users-madivhkassel-Desktop-Stanford-Fall-2026-CS-146S/fecc26ac-03ed-4f62-bdd5-ba35b7996c52/scratchpad/review-13/backend/.pytest_cache`
- `/private/tmp/claude-501/-Users-madivhkassel-Desktop-Stanford-Fall-2026-CS-146S/fecc26ac-03ed-4f62-bdd5-ba35b7996c52/scratchpad/review-13/frontend/node_modules`
- `/private/tmp/claude-501/-Users-madivhkassel-Desktop-Stanford-Fall-2026-CS-146S/fecc26ac-03ed-4f62-bdd5-ba35b7996c52/scratchpad/review-13/frontend/dist`
- `/private/tmp/claude-501/-Users-madivhkassel-Desktop-Stanford-Fall-2026-CS-146S/fecc26ac-03ed-4f62-bdd5-ba35b7996c52/scratchpad/review-13/extension/node_modules`

No readme-check container, network, named volume, or development backend
remains running. Tool caches and BuildKit cache were retained; no prune
command was run. The protected containers, volumes, and images were not
touched. Nothing was pushed, tagged as a release, or published.
