# Test report: fix-install-guide

Date: 2026-11-13. Started at `252714e`, on `fix-install-guide`.

## Environment and network

- Python 3.12.13, selected with `UV_PYTHON=3.12`.
- Node.js v22.17.1, npm 10.9.2, selected before every npm command with
  `source ~/.nvm/nvm.sh && nvm use 22`.
- uv installs and test runs use `UV_OFFLINE=1`; npm installs use offline mode.
  No registry access was needed for the lock refreshes.

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

## Remaining verification

Group 3 has not run yet.

The independent review re-run on a clean `debian:12` container is **not
performed** in this implementation run. That review run checks the stated
minimum versions on a clean machine.
