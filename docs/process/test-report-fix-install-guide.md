# Test report: fix-install-guide

Date: 2026-11-13. Updated: 2026-11-14. Started at `252714e`, on `fix-install-guide`.

## Environment and network (groups 1–3)

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
git clone <review checkout> <previous tmp>/readme-check
```

The clone's HEAD was verified as
`ce01211f92e17c04f39a22a353d91af001bd223c`. Before changing `HOME`, the
runner saved the real Docker config path, `~/.docker`.
Each README shell block was extracted unchanged into a separate file under
`<previous tmp>/blocks/`. The relevant
blocks ran in independent shells with this invocation pattern, from the clone:

```sh
env HOME=<previous tmp home> \
  DOCKER_CONFIG=~/.docker \
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

At group 3 completion, the new permanent tests were the **10** checks in
`test_install_docs.py`
(**9** initially failing checks and **1 guard**). The backend suite's other
tests, all frontend/extension tests, and the smoke script already existed.
Command-run assertions in 3.1 were additional temporary verification checks.

## Scenario mapping and guard checks

This mapping reflects the revised spec at `d30ef34`. Groups 1–3 above are
historical success-path results; failure-path evidence is from fix round 1.

| Requirement / scenario | Evidence |
| --- | --- |
| Install: source checkout on minimum versions | Python/config and runtime-text tests; 4.3.1 installs without `UV_PYTHON`, reports 3.12.13, and contrasts the unpinned 3.14.6 dry-run. Full backend/frontend suites and build pass on Python 3.12.13 and Node 22.17.1. A new clean-OS run at exact minimums was not performed in this fix round. |
| Install: built frontend is served | Existing build-order/path test, original 3.1.5 first-start HTML check, and fix-round Docker smoke root-HTML check. |
| Install: source build keeps published image name free | Exact Compose override test, source-config command-block test; 4.3.3 confirms guarded/idempotent setup and local image build, with published tag unchanged; 4.3.7 reuses the same local image without pulling. |
| Install: health address | Address/response test and every-start-waits test; 4.3.3 runs the exact health command immediately after `up -d --build --wait`; existing smoke health check. |
| Install: private instance secret | Both secret-block cases and privacy guards; 4.3.2 checks silent output, mode 600, and exactly one 64-hex key line in each path. |
| Install: secret is not replaced | Both secret-block cases; 4.3.2 repeats each block with an existing file (exit 1, file SHA-256 unchanged), then removes OpenSSL from the command search path (exit 127, no file created). |
| Backup: restore in a new shell | Archive-validation ordering test; 4.3.6 restores the first archive in a new shell, compares the complete API preference response, and checks visible/hidden post-backup markers are absent. |
| Backup: restore on a new machine | New-machine ordering/emptiness test; 4.3.7 refuses a populated volume, then restores from a second clone with `cp -p` of `.env` after the old volume was removed. Missing-image creation remains covered by the design probe, not this image-retaining rerun. |
| Backup: private backup outside checkout | Private, unique, atomic backup-block test; 4.3.4 checks two separate files under `<tmp home>/catchup-backups`, file modes 600, and directory mode 700. |
| Backup: failed backup keeps earlier backups | Atomic-backup test; 4.3.4 compares the first two SHA-256 values after wrong-directory failures with and without the project variable, with no new archive/partial file; 4.3.6 proves making a third backup preserves the first two. |
| Backup: unreadable backup leaves installation unchanged | Restore-ordering test; 4.3.5 missing and half-length archives fail before the service stops, retaining preferences and markers. All 2,391 truncated lengths fail the exact archive-check code; the full archive passes. |

Guard comments identify the already-correct private creation masks, the
CI Node-major check (Node 24), and both paste-safety cases. The other
original passing checks remain in the suite. Existing backend README-context
and extension docs tests remain compatibility checks.

## Historical group 3 review handoff

The independent review re-run on a clean `debian:12` container is **not
performed** in this implementation run. That review run checks the stated
minimum versions on a clean machine, including a missing-image new-machine
restore. It is not replaced by these cached macOS installs.

The following was the group 3 cleanup handoff. Claude Code later removed
that temporary root and local source image during review. These entries
are historical, not the current fix-round cleanup list:

- Temporary root (contains all block files, logs, state, and the following
  subdirectories): `<previous tmp>`
  - Clone, including its dependencies, built frontend, `.env`, and test
    database: `<previous tmp>/readme-check`
  - Private temporary home and backup:
    `<previous tmp home>`
    (`<previous tmp home>/catchup-data.tar.gz`)
  - Development-secret fixture:
    `<previous tmp>/development-secret`
  - Extracted shell blocks:
    `<previous tmp>/blocks`
- Docker image `catchup:local`,
  ID `sha256:42c5b9d5a0a364823afdbd182c8c79257a1edc5fd956a5e0ba35825c5f09fb40`.
- Docker image `catchup:fix-install-guide-local`,
  ID `sha256:d44b6f67990d4111cbe707cc151c24af6c4c3a4eba3698813c23b345c105ae61`.

The checks also generated these ignored paths in the review checkout,
retained for review and eligible for cleanup afterwards:

- `<review checkout>/backend/.venv`
- `<review checkout>/backend/.pytest_cache`
- `<review checkout>/frontend/node_modules`
- `<review checkout>/frontend/dist`
- `<review checkout>/extension/node_modules`

No readme-check container, network, named volume, or development backend
remains running. Tool caches and BuildKit cache were retained; no prune
command was run. The protected containers, volumes, and images were not
touched. Nothing was pushed, tagged as a release, or published.

## Fix round 1

Date: 2026-11-14. Started at `d30ef34`. Committed tasks 4.1/4.2 as
`1374516` before cloning for 4.3. The review confirmed unsafe secret setup,
unconstrained Python selection, and backup/restore data-loss paths.
This section supersedes the earlier success-only installation conclusions.

### Tests and implementation, 4.1/4.2

`UV_PYTHON=3.12 UV_OFFLINE=1 uv run pytest tests/test_install_docs.py -q`
first reported **11 failed, 10 passed**, **2.39 s**, all failures assertions.
The old final-line Compose regex and the two contradictory secret/backup
assertions were replaced. Missing files and blocks give assertion messages.
Guards identify the already-correct private masks, CI Node major, and
both paste-safety cases.

After the changes, one test regex rejected the valid `.env)` redirect
terminator (**1 failed, 20 passed**, **0.09 s**). Correcting that checker
made all **21 installation cases** pass. No README command failed.
Before commit: backend **917 passed, 24.78 s**; extension under Node
v22.17.1 **114 passed, 8 files, 1.65 s**; Compose override image check
printed **`catchup:local`**.

Ranked hypotheses were unsafe shell-command ordering, unconstrained uv
interpreter selection, and incorrect Compose lifecycle assumptions.
The review probes and targeted checks confirmed those causes, not an
application defect. The revised invariants are: do not replace a secret;
do not overwrite an earlier backup; validate the entire archive before
stopping or emptying a live installation; refuse a populated new-machine
target; start only after successful steps.

### Committed command checks, 4.3

Both clones used `1374516a497143cce5157d1c4258cafeed8977b0`, at
`<tmp>/readme-check` and `<tmp>/readme-check-new-machine`.
Raw README blocks were saved individually under `<tmp>/blocks` and run in
new shells, with `HOME=<tmp home>`, the real Docker config path saved
before changing HOME, and `COMPOSE_PROJECT_NAME=readme-check`, except for
the explicitly named environment probes. Mode checks used `stat -f %Lp`.
No request went to port 8800.

| Item | Actual checks and result |
| --- | --- |
| 4.3.1, automatic Python | With real `HOME`, `UV_OFFLINE=1`, and `UV_PYTHON` unset: README `uv sync` succeeded, then `uv run python --version` reported **Python 3.12.13**. |
| 4.3.1, contrast | `env -u UV_PYTHON UV_PYTHON_PREFERENCE=system UV_OFFLINE=1 uv sync --dry-run` reused the pinned clone's 3.12.13 environment. The comparison copy excluded `.python-version` and `.venv`; the same command selected **3.14.6** and would install 60 packages/download 10. It was a dry-run; nothing was downloaded. |
| 4.3.2, Docker secret | Exit **0**, empty stdout/stderr, mode **600**, exactly one **64-hex** key line. Repeat: exit **1**, file SHA-256 unchanged. Value not displayed. |
| 4.3.2, development secret | With a copy of `.env.example`: same checks passed; repeat exit **1**, SHA-256 unchanged. |
| 4.3.2, missing OpenSSL | Restricted PATH contained only a `grep` link (printf is a bash builtin). Ran both blocks using `<absolute bash path>`. Both exited **127** and created **no `.env`**. |
| 4.3.3, absent environment | Source-config block in a fresh directory: exit **1**, create-secret-first message, no `.env` created. |
| 4.3.3, repeat/newline | Repeated source-config block: exactly **one** COMPOSE_FILE line, `.env` mode still **600**. On a copy with no final newline, all original bytes stayed intact and the setting appeared on its own new line. |
| 4.3.3, build/health | Exact `docker compose up -d --build --wait`: exit **0**. Exact health command immediately afterwards, with no retry loop, returned **`{"status":"ok"}`**. Local image existed; published tag remained absent. |
| 4.3.4, two backups | API GET/PUT with `Origin: http://localhost:8000` saved `digest_language=zh-Hans`. Backup block ran twice, printing two distinct paths. Both files mode **600**, directory **700**. Hashes below. |
| 4.3.4, failures | From a non-installation directory, with project variable set and then unset: both exited **1** at `docker compose config -q`, with `no configuration file provided`. No new archive/partial appeared; both earlier hashes unchanged; service still running. |
| 4.3.5, missing archive | After setting language to `en` and adding visible/hidden markers: example `backup=` path exited **1** before stopping. Running state, complete preferences, and both markers unchanged. |
| 4.3.5, damaged archive | Saved the first half of the first backup as a new mode-600 file. Copied restore block, changing only `backup=` to it: exit **1** with archive-read error. Service running; preferences and markers unchanged. |
| 4.3.5, every cut | In **one** `--network none` local-image container, executed the exact archive-check code extracted from the README with only stdin replaced by in-memory copies. Archive **2,391 bytes**: **2,391/2,391** cuts (lengths **0–2,390**) failed; the full file passed. |
| 4.3.6, backup first | Set language back to `zh-Hans` and `show_images=false`, then made a third backup. First two archives unchanged. |
| 4.3.6, restore first | Copied restore block, changing only `backup=` to the first archive. Exit **0**; full API response matched first backup (`zh-Hans`, `show_images=true`); both markers gone. First two hashes unchanged; third archive still present. |
| 4.3.7, populated volume | Copied new-machine block, changing only `backup=` to first archive. Exit **1**, message **`Volume is not empty; use Restore into this installation instead.`** Data unchanged. Service **remained running**. |
| 4.3.7, new volume | Primary project's `docker compose down -v` removed the old volume. Second clone plus `cp -p` of the same `.env` (600, identical hash): new-machine block with only `backup=` changed succeeded, created a new container/volume, and recovered preferences. **No `pull access denied`**, no build, same image reused. |
| 4.3.8 | **Not run separately**, as instructed; prerequisite-text check in 4.1 covers the note. Full frontend suite ran in 4.4. |
| Cleanup | Both readme-check installations were brought down with `docker compose down -v`. No project container/network/volume remains. No development backend was started. Host files/directories and images retained for review. |

Only these `backup=` values differed in the copied blocks:
- damaged restore: `<tmp home>/catchup-backups/damaged-half.tar.gz`;
- successful existing-install and both new-machine attempts:
  `<tmp home>/catchup-backups/catchup-20261114T223721Z.tar.gz`.

Backup files under `<tmp home>/catchup-backups`:

| File | SHA-256 |
| --- | --- |
| `catchup-20261114T223721Z.tar.gz` (first) | `86858d1bbc9ef8912a46186ec1f4343e474b36a550b09072ddad2239191eb670` |
| `catchup-20261114T223727Z.tar.gz` (second) | `155bbf1df5aadd0766c74308925b43fcb31780a22b08b1a0a6a0e11d3051a53a` |
| `catchup-20261114T223828Z.tar.gz` (third) | `bf6d0636774db21235ea4832f55ef2a948599e3a14c92173dbb55693c60e6adf` |

### Full checks, 4.4

Local backend: **Python 3.12.13**, `UV_PYTHON=3.12 UV_OFFLINE=1`.
Every local npm command first ran
`source ~/.nvm/nvm.sh && nvm use 22`; recorded Node **v22.17.1**, npm
**10.9.2**, with `npm_config_offline=true`. No external network in tests.
Docker builds ran normally under the approved network allowance.

| Command | Actual result |
| --- | --- |
| `UV_PYTHON=3.12 UV_OFFLINE=1 uv run pytest` (backend) | Exit **0**, **917 passed**, **30.53 s** |
| `npm test -- --run` (frontend) | Exit **0**, **281 passed**, **14 files**, **8.02 s** |
| `npm run build` (frontend) | Exit **0**, TypeScript passed; **40 modules**, Vite build **112 ms** |
| `npm test -- --run` (extension) | Exit **0**, **114 passed**, **8 files**, **5.14 s** |
| `DO_NOT_TRACK=1 openspec validate fix-install-guide --strict` | Exit **0**, valid |
| `docker build -t catchup:fix-install-guide-local .` | Exit **0** |
| `scripts/docker-smoke.sh catchup:fix-install-guide-local` | Exit **0**, all **12** checks passed |

The existing smoke script cleaned up its own test container and volume.
There was no manual host-file, directory, or image cleanup. Only
readme-check projects were removed directly, with `docker compose down -v`.
Protected resources were untouched. No prune, push, release tag, or
publication occurred.

A fresh clean-Debian/exact-minimum rerun **after these fixes was not
performed** by this implementer. The earlier reviewer clean run supplied
the defects fixed here; these host-side checks do not replace a fresh
review run.

### Retained fix-round artifacts

For Claude Code to remove (full paths are in the final handoff message):
- `<tmp>` and everything under it: two clones, unpinned backend comparison
  copy, temporary home/backups, secret and missing-tool fixtures, blocks,
  logs, evidence files, and verification helpers;
- `catchup:local`, ID
  `sha256:db94c5ffe451f04009889e4b5a3c5cee71c1b0df00dd2a44a873802e00069dee`;
- `catchup:fix-install-guide-local`, ID
  `sha256:d714b6659b59e27df135d8c0b133156c9d205d8c2be7c7ced52015df1a2810a5`.

Ignored checkout dependencies/build outputs remain available for review.
Tool and BuildKit caches were retained. All local filesystem locations in
this report use placeholders; the required path scan prints nothing.
