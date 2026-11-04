# Test report: refuse-framing (#69)

2026-11-03. Implemented by Claude Code (a Claude Opus 5.5 sub-agent) in place of Factory Droid, whose login had expired. HTTP tests use `TestClient` with explicit `Host`, `Origin`, and `Authorization` headers. The autouse DNS and network block in `backend/tests/conftest.py` stayed on. The test dist is built in `tmp_path`; no test reads `frontend/dist`. No feed, model provider, or other network service was contacted, apart from what `docker build` needed. Backend commands ran with `-p no:cacheprovider`, so the worktree got no `.pytest_cache`.

## Red before the middleware (task 1.1)

`cd backend && uv run -p 3.12 pytest -q -p no:cacheprovider tests/test_framing.py --tb=line`: **14 failed, 1 passed**.

- All 14 failures were at the first line of `assert_refuses_framing` (`test_framing.py:23`), with `assert [] == ['DENY']`: no response carried `X-Frame-Options`.
- Each test asserts status, media type, and body before the header helper. So these guards ran and passed in all 14 tests before the header assertion failed.
- Check 15, the guard that the unhandled exception still reaches `TestClient`, passed.

| Check | Request | Status, type, body (guard) | Headers before 1.2 |
| --- | --- | --- | --- |
| 1 | `GET /` | 200, `text/html`, index marker | missing |
| 2 | `GET /digests/3` (SPA fallback) | 200, `text/html`, index marker | missing |
| 3 | `GET /offline.html` | 200, `text/html`, offline marker | missing |
| 4 | `GET /sw.js` | 200, `text/javascript`, file body | missing |
| 5 | `GET /manifest.webmanifest` | 200, `application/manifest+json`, `{}` | missing |
| 6 | `GET /assets/app.js` (static mount) | 200, `text/javascript`, file body | missing |
| 7 | `GET /api/health` | 200, `{"status": "ok"}` | missing |
| 8 | `GET /api/missing` | 404, `not_found` | missing |
| 9 | `GET /api/health`, `Host: evil.example` | 400, `invalid_host` | missing |
| 10 | `PUT /api/settings/preferences`, `Origin: https://evil.example` | 403, `cross_site_request` | missing |
| 11 | `GET /api/extension/status`, `Bearer cu_unknown` | 401, `invalid_token` | missing |
| 12 | `PUT /api/settings/preferences`, body `{` | 422, `invalid_request` | missing |
| 13 | `GET /api/test-crash` | 500, `text/plain`, `Internal Server Error` | missing |
| 14 | No built frontend: `GET /` and `GET /api/health` | 404 and 200 | missing |
| 15 | Default `TestClient`, `GET /api/test-crash` | raises `RuntimeError` | (guard, passed) |

Checks 8–12 compare the whole JSON body, including the message, not only the code.

## Green and named mutations (task 1.2)

After the `refuse_framing` middleware and the `Exception` handler: `tests/test_framing.py` **15 passed**. `uv run --python 3.12 pytest -q -p no:cacheprovider`: **791 passed** (776 before this change, plus 15). `tests/test_static.py`, `tests/test_cross_site.py`, and `tests/test_allowed_hosts.py`: **45 passed**.

Each mutation was written into `backend/src/catchup/main.py` from a backup, `tests/test_framing.py` was run, and the backup was restored. `cmp` against the backup confirmed the file was unchanged afterwards.

| Mutation | Planned to fail | Result under the mutation |
| --- | --- | --- |
| M1: register `refuse_framing` right after `allowed_host`, inside `spa_fallback` | checks 1–5 | **5 failed, 10 passed**: checks 1–5 (`assert [] == ['DENY']`). Check 6 (`/assets/`) still passed: the static mount is inside both. |
| M2: register it inside the `if` block, after `spa_fallback` | check 14 | **1 failed, 14 passed**: check 14 |
| M3: remove the `Exception` handler | check 13 | **1 failed, 14 passed**: check 13 (Starlette's own 500 has no headers) |
| M4: remove the handler, and in `refuse_framing` catch `Exception` around `call_next` and return the 500 there | check 15 | **1 failed, 14 passed**: check 15, `DID NOT RAISE RuntimeError` |

## Docker smoke red step (task 2.1)

- `git archive 8faaed6 | docker build -t catchup:refuse-framing-before -`, from the repository root: passed.
- `scripts/docker-smoke.sh catchup:refuse-framing-before`, with the new smoke: printed `PASS: container healthy`, then failed at the first new assertion with `AssertionError: ('/api/health', 'X-Frame-Options', None)`. Exit code 1.
- `docker image rm catchup:refuse-framing-before`: removed. The script's own container and volume were cleaned by its trap.

## Final checks (task 3.1)

Run in this order.

| Command | Result |
| --- | --- |
| `cd frontend && npm run build` | Passed: 41 modules transformed. |
| `cd frontend && npm test -- --run` | **259 passed** in 14 files. |
| `cd backend && uv run --python 3.12 pytest -p no:cacheprovider --cov=catchup --cov-report=term` | **791 passed**, **96%** statement coverage (3,039/3,151, 112 missed). `main.py` **100%** (134/134). |
| `cd extension && npm test -- --run` | **112 passed** in 8 files. |
| `docker build -t catchup:refuse-framing-local .` | Passed. |
| `scripts/docker-smoke.sh catchup:refuse-framing-local` | Passed. Every line printed `PASS`, including `PASS: responses refuse framing`, followed by the non-root, database-on-volume, image-exclusion, and restart checks. |
| `DO_NOT_TRACK=1 openspec validate refuse-framing --strict` | `Change 'refuse-framing' is valid`. |

`catchup:refuse-framing-local` was removed after the smoke. No other container, image, or volume was touched; `catchup-e2e` stayed up.

## Manual checks not performed

- **Framing from another local port.** A page served on another local port, with `<iframe src="http://localhost:8000/">`, opened in Chrome: the frame must stay empty.
- **Installed app.** Open the installed app while CatchUp runs, then again while it is stopped: the app must open as before, and the offline page must appear.

Both are left for Claude Code's review and the user's live check.

## Claude's review and browser check (2026-11-04)

- **Diff.** `main.py` adds the two headers in one middleware registered last, and an `Exception` handler that answers the same plain 500 with the headers, re-raising as before; the smoke script checks every response it already requests; README gains one sentence. Matches D1–D5.
- **Browser check.** Claude ran the branch's backend on `localhost:8769`, and a static page on `localhost:5191` that frames `http://localhost:8769/settings` in an `<iframe>`. The built-in browser (Chromium) left the frame empty and logged: "Framing 'http://localhost:8769/' violates the following Content Security Policy directive: "frame-ancestors 'none'". The request has been blocked." Opening CatchUp directly still worked: the Latest page rendered, the service worker registered, and the console had no errors.
- **Not checked:** Firefox and Safari, and the installed app with the server stopped.
