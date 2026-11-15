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

This mapping reflects the revised spec at `6bce12a`. Groups 1–3 above are
historical success-path results. Fix rounds 1 and 2 below distinguish their
own failure-path checks; round 2 did not repeat the round 1 truncation loop.

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
| Backup: backup after a rebuild | The three data-block tests require `{{.Config.Image}}` and reject `{{.Image}}`; backup ordering requires derivation before stop. In 5.3.3 the old image ID actually disappeared after a no-change rebuild, yet backup B succeeded and the service ran afterwards. 5.3.4 restored backup A. An upgrade with source changes followed by a backup was not run: 5.3.8 made its backup before `git pull`. That backup uses the same image-name lookup. |
| Backup: commands outside the installation directory | Ordered I1 guard checks in all three data-block tests. In 5.3.5 all three raw blocks refused `backend/`, each with and without the project variable: six exit-1 results, unchanged container/image/running state, preferences and backup files, and no published-image tag. |

Guard comments identify the already-correct private creation masks, the
CI Node-major check (Node 24), and both paste-safety cases. The other
original passing checks remain in the suite. Existing backend README-context
and extension docs tests remain compatibility checks.
Round 2 also marks the exact Docker-secret and COMPOSE_FILE blocks and
both subshell cases as guards. Its development-secret failure paths are
verified in 5.3.1; private new-machine setup in 5.3.7; recovery after
`down` in 5.3.6. Source-image isolation held through 5.3.2–7. Item 5.3.8
intentionally built the old checkout under the legacy published tag, then
switched to the local name; that tag is retained for review cleanup.

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

## Fix round 2

Date: 2026-11-14 (local; archive names use UTC). Started at plan commit
`6bce12a`. Re-read the revised review context, D4–D6, D8, I1–I5, risks,
tasks, and spec. No proposal, design, or spec delta was edited.

### Test first and implementation, 5.1/5.2

`UV_PYTHON=3.12 UV_OFFLINE=1 uv run pytest tests/test_install_docs.py -q`:
- before README edits: **8 failed, 17 passed, 0.28 s**, all assertion
  failures about old or missing content, not lookup exceptions;
- after README edits: **25 passed, 1.82 s**.

Tests now compare the secret and COMPOSE_FILE blocks line by line with
each line stripped, not whitespace-collapsed. Data-block selectors use
their unique write/empty/emptiness commands, not the `create` text that
also appears in the new error message. Checks cover subshells, ordered
directory/container/volume checks, rebuild-safe image names, private copied
files, apt prerequisites, and first-upgrade order.

Already-passing guards: exact Docker secret, exact COMPOSE_FILE block,
and both subshell cases. Existing masks, CI Node major, and paste-safety
guards remain. Other tests and the Docker smoke script already existed;
the temporary 5.3 assertions are additional live checks.

The three data blocks were written anew from D5's ordered invariants.
An independent old/new comparison verified that every one-line archive
write, check, emptying, and extraction command is byte-identical.
All headings and all README text outside the two approved sections are
unchanged.

Pre-5.3 verification:

| Check | Actual result |
| --- | --- |
| Backend suite, Python 3.12.13 | **921 passed, 24.89 s** |
| Extension suite, Node v22.17.1 / npm 10.9.2 | **114 passed, 8 files, 1.50 s** |
| Strict OpenSpec validation | Exit **0**, valid |
| README scope, headings, preserved Python commands; `git diff --check` | Passed |

Committed 5.1/5.2 as **`e6c05e55e06d87d4cc1be18037905588501d3073`**
before the first 5.3 clone.

Ranked causes and predictions:
1. A rebuild can remove an image ID retained by a running container;
   using its configured image name should keep the archive commands usable.
2. Compose can discover a parent configuration without applying its source
   override; checking for both files in the current directory should refuse
   every subdirectory attempt before Compose runs.
3. After `down`, `ps -aq` succeeds with no output; explicit non-empty checks
   should give a recovery instruction before any stop or archive write.

The review probes and the live results below confirmed those causes.
No application-code defect or dependency change was involved.

### Committed command checks, 5.3

All three local clones started from `e6c05e5`. Blocks extracted from that
committed README were saved individually at `<tmp>/blocks` and run in
separate bash processes, with isolated HOME, the saved real Docker config,
and the specified project name. Only the documented `backup=` line
substitutions differed. `stat -f %Lp` supplied the mode checks.
No Debian container, external test networking, or port-8800 request.

Before item 1:
- `ghcr.io/zhuoang2/catchup:latest`: **absent**;
- `docker info --format '{{json .DriverStatus}}'`:
  **`[["driver-type","io.containerd.snapshotter.v1"]]`**;
- no existing containers or volumes for either test project; port 8000 free.

| Item | Actual result |
| --- | --- |
| 5.3.1, missing example | Development block in a new directory without `.env.example`: exit **1**, `Run this from the repository root.`, no `.env`. |
| 5.3.1, creation/repeat | With copied example: exit **0**, empty stdout/stderr, mode **600**, one **64-hex** secret line, every other line preserved in order. Repeat: exit **1**, unchanged contents and SHA-256. No value/hash displayed. |
| 5.3.1, no OpenSSL | Absolute bash with PATH containing only a `grep` link: exit **127**, no `.env`. |
| 5.3.2, source build | Raw Docker secret and COMPOSE_FILE blocks passed, followed by raw `up -d --build --wait`. Immediate raw health command returned **`{"status":"ok"}`**. Image name **`catchup:local`**, published tag absent. |
| 5.3.2, backup A | Set language **`zh-Hans`**, images **true** via API GET/PUT with Origin `http://localhost:8000`. Backup A succeeded, printed its path, mode **600**, directory **700**; service running. |
| 5.3.3, rebuild/backup B | No-change `up -d --build --wait` passed. Container ID and its stored image ID were unchanged (below), but inspecting that old image ID exited **1**, `No such image`. Set language **`en`**, images **false**; backup B succeeded with its own printed path/mode **600**, without altering A. Service running. The round-1 failure condition really occurred. |
| 5.3.4, restore after rebuild | Changed preferences again, added visible and hidden post-backup markers, then restored A. Complete preference response matched A; both markers absent; both A/B SHA-256 values unchanged. |
| 5.3.5, subdirectories | From `<tmp>/readme-check/backend`, ran backup, restore A, and new-machine A, each with project variable set and unset. All **6** exited **1** with the I1 directory message. Container ID, configured image, stored image ID, volume and running state unchanged; preferences/files unchanged; published tag still absent. |
| 5.3.6, down/recreate | Set third preferences (`zh-Hans`, images **false**), distinct from A and B; added visible/hidden markers. `docker compose down` retained the volume. Backup and restore B each exited **1** with the no-container recovery message, creating no file. `docker compose create` reused the same volume; restore B then passed, recovered B rather than A/third, and removed both markers. A/B hashes unchanged. |
| 5.3.7, new machine | `down -v`, second clone `<tmp>/readme-check-new`, and initially empty `<tmp home 2>`. Copied same `.env`, deliberately set **644**; raw private-files block made it **600** and created backups directory **700**. Copied A there; new-machine restore passed into a new volume/container, using `catchup:local`, with A's complete preferences. Same `.env` contents and backup hash. Then `down -v`. |
| 5.3.8, legacy upgrade | Third clone `<tmp>/readme-old`, project **`readme-old`**, branch `old` at **`064d3a9`**, upstream `origin/fix-install-guide`. Old build deliberately created the local **`ghcr.io/zhuoang2/catchup:latest`** tag. Set preference, then followed **backup → `git pull` → COMPOSE_FILE → build**. Backup succeeded in old checkout; pull fast-forwarded to `e6c05e5`; new container used **`catchup:local`**, and complete preferences/backup hash were unchanged. Then `down -v`. No image-removal command was run. |
| Cleanup | `readme-check` and `readme-old` are down; no test project containers or named volumes remain. No development backend was started. Files/directories and image tags retained for review. |

Rebuild observations (5.3.3), both before and after:
- container ID:
  `bb6f4af4de6e8dda0e187ee2ff29c4b178aee1120e3923cbbb185c865e58f7bd`;
- container `{{.Image}}`:
  `sha256:3ec1b87223cc8f5cf61d12a2faaf69351067c3e38e2bcb5de8cf8c0f9c0799ff`;
- configured image: **`catchup:local`**;
- inspecting that old image after the rebuild: **exit 1**. The new backup
  uses the configured name instead, so it still succeeds.

The no-container message in item 6 was exactly
`No CatchUp container here; run docker compose create, then run this block again.`
The six item-5 failures used
`Run this from your installation directory (the one with compose.yaml and .env).`

Backups under `<tmp home>/catchup-backups`:

| Backup | File | SHA-256 |
| --- | --- | --- |
| A | `catchup-20261115T060218Z.tar.gz` | `f7b9f4f62b9ecbd13d4011a25d9a9d9b149898e99cdabef6ef45edc411ba860a` |
| B | `catchup-20261115T060227Z.tar.gz` | `9e30649d69b06ab014e9075897f99f88bd22c89956ae54133f69290602fc4fdd` |
| Legacy pre-upgrade | `catchup-20261115T060424Z.tar.gz` | `561db623255afec065a6b80168255054a9a740a13dd3f515028c48dec4b1fd35` |

All were mode **600**. The copy of A in `<tmp home 2>/catchup-backups`
has the same basename and SHA-256. There is no partial archive.
For the copied restore blocks, only `backup=` was changed:

| Copied block file | Replacement line |
| --- | --- |
| `restore-A.sh`, `new-machine-A.sh` | `backup="<tmp home>/catchup-backups/catchup-20261115T060218Z.tar.gz"` |
| `restore-B.sh` | `backup="<tmp home>/catchup-backups/catchup-20261115T060227Z.tar.gz"` |
| `new-machine-A-new-home.sh` | `backup="<tmp home 2>/catchup-backups/catchup-20261115T060218Z.tar.gz"` |

No README fix was needed during 5.3, so no additional commit/reclone loop.

Harness notes: the first extractor ambiguously matched both source starts;
it was corrected to select the standalone command before any start ran.
Temporary full-container inspection logs initially included generated test
environment values. All **24** such logs had runtime environments redacted,
all evidence logs were scanned for the generated values, and the helper
now requests only safe inspection fields. No secret value was printed.

### Full checks, 5.4

Backend commands used **Python 3.12.13** with
`UV_PYTHON=3.12 UV_OFFLINE=1`. Every local npm command first selected
Node 22 with `source ~/.nvm/nvm.sh && nvm use 22`; recorded Node
**v22.17.1**, npm **10.9.2**. npm used offline mode with audit/funding
requests disabled. Tests used no external network. Docker builds used
the approved normal network allowance, including the old-checkout build;
there was no offline build attempt. `git pull` fetched only its local
temporary-clone upstream.

| Command | Actual result |
| --- | --- |
| `UV_PYTHON=3.12 UV_OFFLINE=1 uv run pytest` (backend) | Exit **0**, **921 passed**, **25.99 s** |
| `npm test -- --run` (frontend) | Exit **0**, **281 passed**, **14 files**, **7.15 s** |
| `npm run build` (frontend) | Exit **0**, TypeScript and Vite passed; **40 modules**, build **263 ms** |
| `npm test -- --run` (extension) | Exit **0**, **114 passed**, **8 files**, **4.49 s** |
| `DO_NOT_TRACK=1 openspec validate fix-install-guide --strict` | Exit **0**, valid |
| `docker build -t catchup:fix-install-guide-local .` | Exit **0** |
| `scripts/docker-smoke.sh catchup:fix-install-guide-local` | Exit **0**, all **12** existing smoke checks passed |

No clean-Debian or exact-minimum run was performed this round, as 5.3
instructs. These macOS Docker checks cover the new rebuild/directory/down
cases; the independent targeted review run remains for Claude Code.

The only direct removal commands were `docker compose down` (item 6)
and `docker compose down -v` for `readme-check` and `readme-old`.
The unmodified smoke script performed its own cleanup. No host file,
directory, or Docker image was deleted manually. No protected resource,
port 8800, Docker prune, push, release tag, or publication was used.

### Retained fix-round-2 artifacts

This is the current cleanup handoff, superseding earlier rounds' lists.
All contents of `<tmp>` remain for Claude Code:
- `<tmp>/readme-check`, the first clone, including its private `.env`;
- `<tmp>/readme-check-new`, the second clone and copied private `.env`;
- `<tmp>/readme-old`, the legacy/upgraded clone and its private `.env`;
- `<tmp home>` and `<tmp home 2>`, including the three original backups
  and the copied A;
- `<tmp>/development-missing-example`, `<tmp>/development-secret`,
  `<tmp>/development-no-openssl`, and `<tmp>/bin-without-openssl`;
- `<tmp>/blocks`, `<tmp>/logs`, `<tmp>/verify.py`,
  `<tmp>/evidence.json`, and the root-level red/green/full-check logs.

The prior listed ignored checkout dependencies/build outputs were reused
and remain. Tool/BuildKit caches remain. No test project container,
network, volume, or development backend remains.

Retained image tags, all local:

| Tag | ID |
| --- | --- |
| `catchup:local` | `sha256:8ff9dbeef8ea708edbd94ce548e4df3dff7144b6730d9302a6de7e0c5c7118ac` |
| `catchup:fix-install-guide-local` | `sha256:d15e79272b8e7a153e8f2835ede0ecefe168d732bad3e6bcb0d93b1051f66058` |
| `ghcr.io/zhuoang2/catchup:latest` | `sha256:c38633faabd5dd5d4cabe355e2249880fe81fe6f00a7a4f42622542b89e53c4f` |

The last tag is the **legacy local source build from item 8, not a fetched
release**. It remained at its recorded ID after the upgrade and final
build. Claude Code removes it at review; Droid did not run the README's
image-removal command. Actual cleanup paths are in the final message.
All local paths in this report are placeholders.

## Review of fix round 2 (Claude Code)

Date: 2026-11-14. Range `6bce12a..7b4f657`.

Cleanup: Claude Code removed the temporary tree and `catchup:local`. It
then ran the README's `docker image rm ghcr.io/zhuoang2/catchup:latest`
on the legacy tag from item 8, which exited 0. Before that, it checked
that the tag carried the `com.docker.compose.project=readme-old` label and
no release labels.

Checks on the round's head: backend **921 passed**; strict validation
passed; `git diff --check` passed; a new `docker build` and
`scripts/docker-smoke.sh` passed all **12** checks. A fresh sub-agent
re-ran six scenarios from the README with Docker on this Mac. All six
passed:
- a no-change rebuild, then a backup;
- a restore after the rebuild;
- all three data blocks from `backend/`;
- `docker compose down`, then `create` and a restore;
- the upgrade of a checkout at `064d3a9`, including `docker image rm`.

Review-commit changes, from the spec review and the re-run:
- the three data blocks' tests now require every guard line to end with
  `exit 1; }`, and the backup test requires the `backup=` line before the
  stop;
- the source upgrade block is a subshell with the installation-directory
  guard, and a new test checks it;
- the no-container message names the `docker compose down` case. The text
  above the blocks says that they need an installation started with
  Compose. Probe: Compose does not find a container started with
  `docker run`, and `create` then makes a new, empty volume.

Mutation check: 13 named mutations of the README, run against
`tests/test_install_docs.py`. They covered:
- dropping `exit 1` from each guard in all four guarded blocks;
- moving `backup=` after the stop;
- putting the backup inside the checkout;
- removing the upgrade guard.

Before the test changes, all 7 that applied survived; after them, all
13 fail the tests. After the review changes, the installation tests pass
(**26 passed**), the backend suite passes (**922 passed**), the extension
suite passes under Node 22 (**114 passed**), and strict validation passes. A stub
`docker` and `git` run of the changed blocks matched the design in bash,
zsh, dash, and pasted into interactive bash and zsh. From `backend/`, every
block exits 1 without calling `docker` or `git`. Without a container, each
block exits 1 before any stop.
