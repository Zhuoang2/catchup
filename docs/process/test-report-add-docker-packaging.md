# Docker packaging verification (2026-10-04)

Change: `add-docker-packaging` (#7). Local Docker Desktop 29.8.0, arm64;
buildx `desktop-linux`. No real model key, live source, or registry publish was
used. Backend pytest uses the autouse sandbox (temporary data dir, blocked
network and real sleeps). Docker checks used local images, temporary volumes,
and loopback ports; the test containers and volumes were removed.

## Commands and results

| Command/check | Result |
| --- | --- |
| `cd backend && uv run pytest` | 206 passed |
| `cd backend && uv run pytest --cov=catchup --cov-report=term` | 206 passed; 96% overall statement coverage (1214/1269) |
| `cd backend && uv run catchup serve --help` | Exit 0; host/port options printed |
| `cd backend && uv build --wheel` + zip assertion | Pass: `catchup/migrations/env.py`, `script.py.mako`, `versions/0001_initial.py` packaged |
| `cd frontend && npm ci && npm test -- --run && npm run build` | 22 tests passed; TypeScript and Vite build passed |
| `docker build -t catchup:local .` | Pass (also with dummy `.env` in working copy, then removed) |
| `docker run --rm --entrypoint id catchup:local -u` | 999 |
| `docker run --rm --entrypoint python catchup:local -c 'import catchup, pathlib; print(pathlib.Path(catchup.__file__).parent / "migrations")'` | `/app/.venv/lib/python3.12/site-packages/catchup/migrations` |
| Image inspection | No `/app/.env` or `/app/backend`; health check, `/data` volume, port 8000 present |
| `docker compose -p catchup-packaging-check config --quiet && docker compose -p catchup-packaging-check up -d --build` | Pass, healthy, `docker compose ... port catchup 8000` returned `127.0.0.1:8000`; `down --volumes` cleaned test volume |
| `scripts/docker-smoke.sh catchup:local` | Pass; output below |
| Smoke with temporary image whose health URL is `/api/broken` | Failed with unhealthy/404 as expected; temporary image removed |
| README backup/restore commands on a throwaway volume | Pass: fixture restored, volume removed |
| `actionlint .github/workflows/ci.yml .github/workflows/release.yml` | Pass (actionlint 1.7.12) |
| `docker buildx build --platform linux/amd64,linux/arm64 --progress=plain .` | Pass locally for both, without push |
| `openspec validate add-docker-packaging --strict` | Pass |

Image size (`docker image inspect catchup:local --format '{{.Size}}'`):
**427,128,247 bytes (407.34 MiB)** on arm64.

Smoke output:

```text
PASS: container healthy
PASS: GET /api/health (Host: localhost)
PASS: GET / returns HTML
PASS: saved zh-Hans preference
PASS: process is non-root
PASS: database exists on volume
PASS: image excludes .env and backend source tree
PASS: preference survives restart
```

## Spec scenario mapping

| Scenario in `local-deployment` | Test or check | Status |
| --- | --- | --- |
| Start with compose | Compose build/up health + `scripts/docker-smoke.sh` UI and API checks; README `.env` command reviewed | Automated startup, manual browser view pending |
| Images for common machines | Local two-platform build; release workflow `platforms` reviewed | Build verified, registry publication pending merge |
| Restart | Smoke PUT/restart/GET of `zh-Hans` on same named volume | Automated pass |
| Upgrade to a newer image | `test_db.py::test_existing_database_at_old_revision_is_unchanged`, startup migration and volume persistence; Compose upgrade command reviewed | Partly verified; actual newer-image replacement/new migration pending |
| Default compose installation | `docker compose ... port catchup 8000` = `127.0.0.1:8000`; `compose.yaml` reviewed | Automated pass |
| Process user | `docker run ... id -u` = 999; smoke checks uid and database creation on volume | Automated pass |
| Healthy after start | Compose status healthy and smoke Docker health poll after migrations | Automated pass |
| Installed outside the repository | Wheel zip check, `docker run` package import path, smoke migrations/UI | Automated pass |
| Running from a source checkout | `test_static.py::test_source_tree_dist_fallback`, `test_built_frontend_fallback_keeps_api_json` | Automated pass |
| Environment file present | Dummy `.env` build + absence assertion; `.dockerignore` allowlist excludes `data/`, dependencies and unrelated files | Automated `.env` check; `data/` exclusion by allowlist inspection |

## Manual verification (reviewer/user)

- [ ] On the user's Mac: `docker compose up --build`, open UI, save model
  settings with a real key, generate one digest, restart, and confirm data.
- [ ] After merge, confirm GHCR `edge` exists for amd64 and arm64 and check
  package visibility; after a user-created version tag, verify semver and
  `latest` tags. No image was published or tag created here.
- [ ] Replace an existing container with a genuinely newer schema/image on
  the same volume and confirm migrations and data preservation when a later
  revision exists.

The example `.env.example` is for source checkouts and sets
`CATCHUP_DATA_DIR=./data`. Docker users must generate the Docker-specific
`.env` documented in the README (secret only), otherwise that override would
put the database outside `/data`. No other design deviations were needed.
