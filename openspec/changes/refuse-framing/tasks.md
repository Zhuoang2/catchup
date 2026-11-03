# Tasks

Implementer notes:
- **Read first.** Read `proposal.md`, `design.md` (D1–D5), and the delta in `specs/model-settings/spec.md`. If something looks wrong or contradictory, stop and report instead of redesigning.
- **Use the `tdd` skill** (D-016). Write each task's checks as failing tests first, watch them fail, then implement. The header checks fail today, because no response carries either header. The status, body, and content-type checks pass today; they are guards. Each guard that a named mutation targets gets that mutation as its red step: apply it, see the check fail, then revert it.
- **Test rules.**
  - Use `TestClient` with explicit `Host`, `Origin`, and `Authorization` headers, as `backend/tests/test_cross_site.py` does. The autouse DNS and network block in `backend/tests/conftest.py` stays on.
  - Read a header's values with `response.headers.get_list(name)`, so a duplicated header fails the check.
  - Build the frontend dist in `tmp_path`, as `backend/tests/test_static.py` does. Do not depend on `frontend/dist`.
- **OpenSpec commands** always run with the `DO_NOT_TRACK=1` prefix, for example `DO_NOT_TRACK=1 openspec validate refuse-framing --strict`.
- **Out of scope:**
  - any other CSP directive, or any other security header;
  - the frontend, the extension, and the Vite dev server;
  - the existing middlewares' logic.
- **Commits.** Commit after each task group. Do not push, tag, or open a PR.

## 1. Refuse framing on every response

- [ ] 1.1 **Tests first**, in a new `backend/tests/test_framing.py`.

  **Setup.** A fixture builds a dist in `tmp_path` with:
  - `index.html` containing a marker such as `<html>CatchUp index</html>`;
  - `offline.html` with its own marker;
  - `sw.js`;
  - `manifest.webmanifest` containing `{}`;
  - `assets/app.js`.

  It creates `create_app(test_settings, dist_dir=dist)`, adds a test-only route `GET /api/test-crash` that raises `RuntimeError`, and opens `TestClient(app, base_url="http://localhost:8000", raise_server_exceptions=False)` in a `with` block, so the lifespan creates `session_factory` (checks 11 and 12 need it). Compare media types without parameters (`content-type` carries `; charset=utf-8`): use `.split(";")[0]` or `startswith`, as `test_static.py` does.

  A helper `assert_refuses_framing(response)` asserts:
  - `response.headers.get_list("x-frame-options") == ["DENY"]`;
  - `response.headers.get_list("content-security-policy") == ["frame-ancestors 'none'"]`.

  **Checks.** Each response passes `assert_refuses_framing`, and keeps the status, type, and body given:
  1. `GET /`: 200, media type `text/html`, the index marker.
  2. `GET /digests/3` (the SPA fallback): 200, the index marker.
  3. `GET /offline.html`: 200, media type `text/html`, the offline marker.
  4. `GET /sw.js`: 200, a JavaScript media type (`text/javascript` or `application/javascript`).
  5. `GET /manifest.webmanifest`: 200, `application/manifest+json`.
  6. `GET /assets/app.js`: 200.
  7. `GET /api/health`: 200, `{"status": "ok"}`.
  8. `GET /api/missing`: 404, `{"error": {"code": "not_found", "message": "Not Found"}}`.
  9. `GET /api/health` with `Host: evil.example`: 400, code `invalid_host`.
  10. `PUT /api/settings/preferences` with `Origin: https://evil.example` and a valid JSON body: 403, code `cross_site_request`.
  11. `GET /api/extension/status` with `Authorization: Bearer cu_unknown`: 401, code `invalid_token`.
  12. `PUT /api/settings/preferences` with `Content-Type: application/json` and the body `b"{"`: 422, code `invalid_request`.
  13. `GET /api/test-crash`: 500, media type `text/plain`, and the body is exactly `Internal Server Error`.
  14. **Without a built frontend**, using `create_app(replace(test_settings, frontend_dist=tmp_path / "missing"))`: `GET /` returns 404 and `GET /api/health` returns 200, and both pass `assert_refuses_framing`.
  15. **Exceptions still propagate.** With a default `TestClient` (`raise_server_exceptions=True`) on the same app, `GET /api/test-crash` raises `RuntimeError`. This is a guard; it passes today.

  Verify: the header assertions of checks 1–14 fail before 1.2. The status, body, and type assertions, and check 15, pass. Record which tests failed, and how.
- [ ] 1.2 **Implement design D1 and D2** in `backend/src/catchup/main.py`:
  - a module constant with the two headers;
  - a `refuse_framing` `@app.middleware("http")` function, registered as the last registration in `create_app`, after the `if (frontend_dist / "index.html").is_file():` block (`:182-196`) and just before `return app`. Give it a short comment: it must stay the last registration so that it wraps the SPA fallback, and any future `Content-Security-Policy` must keep `frame-ancestors 'none'`;
  - a handler for `Exception`, registered in `create_app`, that returns `PlainTextResponse("Internal Server Error", status_code=500, headers=<the constant>)`.

  Verify:
  - all 1.1 checks pass;
  - each named mutation fails the checks given, and is reverted afterwards:
    - M1, register `refuse_framing` right after `allowed_host` (`:144-171`), so that it runs inside `spa_fallback`: checks 1–5 fail;
    - M2, register it inside the `if` block, after `spa_fallback`: check 14 fails;
    - M3, remove the `Exception` handler: check 13 fails;
    - M4, remove the handler, and in `refuse_framing` catch `Exception` around `call_next` and return the 500 there: check 15 fails;
  - `git diff` shows no change left from the mutations;
  - `uv run --python 3.12 pytest` passes in `backend/`, including `tests/test_static.py`, `tests/test_cross_site.py`, and `tests/test_allowed_hosts.py`.

## 2. The Docker smoke and README

- [ ] 2.1 **The smoke checks the headers** (design D5). In `scripts/docker-smoke.sh`, in the first Python block (`:40-83`), assert `response.headers.get_all("X-Frame-Options") == ["DENY"]` and `response.headers.get_all("Content-Security-Policy") == ["frame-ancestors 'none'"]` on every response the block reads:
  - in `request()` (`:48-55`), which covers `/api/health`, `/`, and the `PUT`;
  - in the file loop (`:61-77`), which covers `/manifest.webmanifest`, `/sw.js`, and `/offline.html`.

  Give every new assertion a message naming the path, the header, and the value, for example `assert value == ["DENY"], (path, "X-Frame-Options", value)`: the script runs Python from a heredoc, so a bare `assert` prints no source line. Print `PASS: responses refuse framing` once, at the end of the block, after the `PUT` assertion. Change nothing else in the script.

  Red step: build an image from the commit before this change, and run the new smoke against it:
  - `git archive 8faaed6 | docker build -t catchup:refuse-framing-before -`, from the repository root;
  - `scripts/docker-smoke.sh catchup:refuse-framing-before`.

  Verify: the smoke fails at the new header assertion, and the failure names the header. Then remove the image with `docker image rm catchup:refuse-framing-before`. The passing run is in 3.1.
- [ ] 2.2 **README.** In the paragraph at `README.md:251-264`, after the sentence "A page on another site, or on another local port, is refused." (`:259-260`), add one sentence: other sites also cannot show CatchUp inside their own pages, so they cannot trick you into clicking its controls. Keep the paragraph's line wrapping.

  Verify: `git diff README.md` shows only that sentence and the rewrapped lines around it.

## 3. Checks and report

- [ ] 3.1 Run the full checks:
  - in `frontend/`: `npm run build` first, so that backend coverage is measured with `frontend/dist` present, then `npm test -- --run`;
  - in `backend/`: `uv run --python 3.12 pytest --cov=catchup --cov-report=term`;
  - in `extension/`: `npm test -- --run`;
  - from the repository root: `docker build -t catchup:refuse-framing-local .`, then `scripts/docker-smoke.sh catchup:refuse-framing-local`, which must print `PASS: responses refuse framing`;
  - `DO_NOT_TRACK=1 openspec validate refuse-framing --strict`.

  Write `docs/process/test-report-refuse-framing.md`, a new file, with:
  - the commands and their real results;
  - the red-first results of 1.1, and of the smoke in 2.1;
  - the mutation table of 1.2;
  - the coverage of `main.py`;
  - the manual checks that were not performed: a page on another local port that frames `http://localhost:8000/` in Chrome, where the frame must stay empty; and the installed app, opened while CatchUp runs and again while it is stopped, where the offline page must appear.

  Add this change's line to `docs/process/coverage-summary.md`, in the style of the existing lines.

  Add your entry to `docs/process/ai-usage-log.md` after the latest entry, with a faithful excerpt of the prompt you actually received, and the tool and model. Leave out the session id; Claude Code adds it at review.

  Verify: every command passes, and the report has the actual numbers.
