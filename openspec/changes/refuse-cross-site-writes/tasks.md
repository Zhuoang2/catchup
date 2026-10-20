# Tasks

Implementer notes:
- **Read first.** Read `proposal.md`, `design.md` (D1–D3), and the delta in `specs/model-settings/spec.md`. If something looks wrong, stop and report.
- **Use the `tdd` skill** (D-016). Write each task's checks as failing tests first, watch them fail, then implement. The "refused" checks fail today, because the server accepts these requests. The "accepted" checks pass today; each gets the named temporary mutation as its red step: see it fail, then revert it.
- **Test rules.**
  - `TestClient` with explicit `Host`, `Origin`, and `Sec-Fetch-Site` headers.
  - The autouse DNS block stays on, and nothing reaches the network. Mock routes with `respx`, and assert `route.call_count == 0` for anything that must not be requested.
  - For the run case, configure a model as the runner tests do, and stub the run's worker, so that no collection or model call happens.
- **Out of scope:** any frontend change; the extension's token path (#58); CORS headers.
- **Commits.** Commit after each task group. Do not push, tag, or open a PR.

## 1. Refuse cross-site writes

- [ ] 1.1 **Tests first**, in a new `backend/tests/test_cross_site.py`.

  **Refused**, each returning 403 `{"error": {"code": "cross_site_request", "message": "This request came from another site and was refused."}}` with no effect:
  1. `POST /api/digest-runs` with `Content-Type: application/x-www-form-urlencoded`, an empty body, and `Origin: https://evil.example`, while a model is configured. No `DigestRun` row exists afterwards.
  2. The same request with only `Sec-Fetch-Site: cross-site`, and no `Origin`.
  3. `PUT /api/settings/preferences` (JSON) with `Host: localhost:8000` and `Origin: http://localhost:3000`. The preferences are unchanged.
  4. `DELETE /api/sources/{id}` with `Origin: https://evil.example`. The source still exists.
  5. `POST /api/sources/preview` with `Origin: null`. The mocked feed route has `call_count == 0`.
  6. `PUT /api/settings/preferences` with only `Sec-Fetch-Site: same-site`.
  7. `Origin: chrome-extension://abc` and `Origin: file://` on `PUT /api/settings/preferences`.
  8. `Host: localhost:8000` with `Origin: http://127.0.0.1:8000`, a different host.

  **Accepted as today:**

  9. `Host: localhost:8000`, `Origin: http://localhost:8000`, and `Sec-Fetch-Site: same-origin` on `PUT /api/settings/preferences`. It returns 200 and saves.
  10. The Vite dev proxy: `Host: localhost:5173` with `Origin: http://localhost:5173`.
  11. Behind a domain: `CATCHUP_ALLOWED_HOSTS` includes `catchup.example.org`, with `Host: catchup.example.org` and `Origin: https://catchup.example.org`.
  12. IPv6: `Host: [::1]:8000` with `Origin: http://[::1]:8000`.
  13. A default port: `Host: localhost` with `Origin: http://localhost`.
  14. No `Origin` and no `Sec-Fetch-Site` (a tool): `PUT /api/settings/preferences` returns 200. `POST /api/digest-runs`, with a model configured, returns 202.
  15. `Sec-Fetch-Site: none` with no `Origin`.
  16. `GET /api/digests` with `Origin: https://evil.example` and `Sec-Fetch-Site: cross-site`: 200, because reads are not affected.

  **Order:** a disallowed `Host` with a foreign `Origin` still gets 400 `invalid_host`, because the host check runs first.

  Named mutations for the accepted checks, in 1.2:
  - "compare hostnames only" fails check 3;
  - "refuse every write that has an `Origin`" fails checks 9–13;
  - "ignore `Sec-Fetch-Site`" fails checks 2 and 6;
  - "check `GET` too" fails check 16.

  Verify: checks 1–8 fail before 1.2, and the accepted checks pass.
- [ ] 1.2 **Implement design D1** in `backend/src/catchup/main.py`: a middleware after `allowed_host`, for `POST`, `PUT`, `PATCH`, and `DELETE` on any path. Add a short comment at the decision point, saying that #58 will add the extension-token exception there (D3).

  Verify:
  - all 1.1 checks pass;
  - each named mutation fails its checks, and is reverted;
  - `uv run pytest` passes, including `tests/test_allowed_hosts.py`.
- [ ] 1.3 **Raise the FastAPI floor** (design D2). Change `backend/pyproject.toml` to `fastapi>=0.132,<1`, and run `uv lock`. The locked version stays 0.142.2.

  Verify: `uv lock --check` passes, and `uv run pytest` passes.

## 2. Checks and docs

- [ ] 2.1 **The frontend and the image.**
  - Run `npm run build` and `npm test -- --run` in `frontend/`. Nothing there changes, and everything still passes.
  - Build a local image with `docker build -t catchup:cross-site-local .`, and run `scripts/docker-smoke.sh catchup:cross-site-local`.

  Verify: everything passes. Record the commands and results.
- [ ] 2.2 **Docs.**
  - **`README.md`**, in the paragraph on local-only access (around `:129-136`):
    - CatchUp accepts requests that change data only from its own pages, and from tools that send no browser origin headers;
    - a page on another site, or on another local port, is refused;
    - a proxy in front of CatchUp must pass the browser's `Host` header.
  - **`docs/process/test-report-refuse-cross-site-writes.md`:** the red-first results for each check, the mutation table, and the commands of 2.1.
  - **`docs/process/coverage-summary.md`:** add this change's line.
  - **Final checks:** `npm run build` first, then `uv run pytest --cov=catchup --cov-report=term` in `backend/`, `npm test -- --run`, and `openspec validate refuse-cross-site-writes --strict`.
  - **`docs/process/ai-usage-log.md`:** add your entry after the latest entry, with a faithful excerpt of the prompt you actually received, and the tool and model. Leave out the session id.

  Verify: every command passes, and the report has the actual numbers.
