# Test report: refuse-cross-site-writes (#59)

2026-10-20. HTTP tests use `TestClient` with explicit `Host`, `Origin`, and/or `Sec-Fetch-Site` headers. The autouse DNS/network block remained enabled; the preview feed had an `respx` route and its mocked DNS result. Both run tests configured a model and stubbed the worker. No feed collection or model call occurred.

## Red before middleware

`cd backend && uv run pytest tests/test_cross_site.py -q --tb=line`: **10 failed, 10 passed** before task 1.2. The nine requested refused cases (case 7 has two origins) and the extra PATCH-on-unknown-path case failed; all accepted and host-order checks passed.

| Plan check | Expected behavior | Before middleware |
| --- | --- | --- |
| 1 | Foreign form POST refuses run, leaves zero `DigestRun` rows | 202 instead of 403 |
| 2 | Cross-site Fetch Metadata without Origin refuses run | 202 instead of 403 |
| 3 | Another local port cannot change preferences | 200 instead of 403 |
| 4 | Foreign DELETE keeps source | 204 instead of 403 |
| 5 | `Origin: null` refuses preview before feed request | 200 instead of 403 (mocked route was called) |
| 6 | `Sec-Fetch-Site: same-site` refuses preference write | 200 instead of 403 |
| 7 | `chrome-extension://abc` and `file://` refuse preference write | 200 instead of 403 for each |
| 8 | `127.0.0.1` differs from `localhost` | 200 instead of 403 |
| Extra | Foreign PATCH on a non-API path is refused | 404 instead of 403 |
| 9 | Same-origin write with `same-origin` Fetch Metadata | 200, saved |
| 10 | Vite proxy origin | 200, saved |
| 11 | Allowed domain behind TLS proxy | 200, saved |
| 12 | Bracketed IPv6 origin | 200, saved |
| 13 | Default HTTP port | 200, saved |
| 14 | Tool preference write and run without browser headers | 200, saved; 202, run row created |
| 15 | `Sec-Fetch-Site: none` without Origin | 200, saved |
| 16 | Foreign GET remains readable | 200 as expected |
| Order | Disallowed Host wins over foreign Origin | 400 `invalid_host` as expected |

After task 1.2, `uv run pytest tests/test_cross_site.py tests/test_allowed_hosts.py -q`: **34 passed**. Refused cases returned the exact 403 `cross_site_request` response with no effect; the preview route had `call_count == 0`. `uv run pytest -q --tb=short` passed **579 tests**, including allowed-host tests. The lock step's red check was `uv lock --check` after changing the dependency floor but before regenerating the lockfile: it failed with “lockfile needs to be updated”. `uv lock` changed only the root package's FastAPI constraint; the pinned FastAPI remains **0.142.2**. `uv lock --check` and a second `uv run pytest -q --tb=short` then passed (**579 tests**).

## Named mutation checks

Each mutation was applied only temporarily to `backend/src/catchup/main.py`; the target checks passed again after reversion.

| Temporary mutation | Target | Red under mutation | Green after revert |
| --- | --- | --- | --- |
| Compare hostnames only | 3, other local port | 1 failed (200 vs 403) | 1 passed |
| Refuse every write with an `Origin` | 9–13, own origins | 5 failed (403 vs 200), 2 tool cases passed | 7 passed |
| Ignore `Sec-Fetch-Site` | 2 and 6 | 2 failed (202/200 vs 403) | 2 passed |
| Check `GET` too | 16 | 1 failed (403 vs 200) | 1 passed |

Checks 14, 15, and host-check ordering had no named mutation in the task plan; they passed before and after the middleware. No red-phase claim is made for those baseline checks.

## Frontend and image (task 2.1)

| Command | Result |
| --- | --- |
| `cd frontend && npm run build` | First attempt could not find `tsc` in the new worktree. After `npm ci`, passed (41 modules transformed). |
| `cd frontend && npm test -- --run` | **221 passed** in 14 files; no frontend source changed. |
| `docker build -t catchup:cross-site-local .` | Passed; image includes FastAPI **0.142.2**. |
| `scripts/docker-smoke.sh catchup:cross-site-local` | Passed: health, API, HTML, PWA files, tool preference write, non-root process, persisted database/restart, and image exclusions. Its temporary container and volume were cleaned by the script. |

## Final checks (task 2.2)

| Command | Result |
| --- | --- |
| `cd frontend && npm run build` | Passed first in the final sequence; 41 modules transformed. |
| `cd backend && uv run pytest --cov=catchup --cov-report=term` | **579 passed**, **96%** statement coverage (2,303/2,390, 87 missed); `main.py` **97%** (84/87). |
| `cd frontend && npm test -- --run` | **221 passed** in 14 files. |
| `openspec validate refuse-cross-site-writes --strict` | Passed. |

No live browser-origin or production proxy check was performed; those are review-time checks in the design. No external feed or model provider was contacted in tests.
