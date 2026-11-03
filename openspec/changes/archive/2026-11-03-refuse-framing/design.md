# Design

Lean change for issue #69. See `proposal.md` for the motivation, and the `model-settings` delta for the requirement.

## Context

- **Middleware order.** `create_app` (`backend/src/catchup/main.py:87-198`) registers three `@app.middleware("http")` functions:
  - `cross_site_writes` (`:116-142`);
  - `allowed_host` (`:144-171`);
  - `spa_fallback` (`:187-196`), only when `frontend_dist/index.html` exists (`:182`).

  Starlette runs the last registered middleware first (comment at `:115`). So today `spa_fallback` is the outermost: it receives the 404 for `/`, `/digests/3`, or `/offline.html` and returns a new `FileResponse`, which no other middleware sees.
- **Responses built outside the routes:**
  - `allowed_host` returns 400 `invalid_host`;
  - `cross_site_writes` returns 403 `cross_site_request` and 401 `invalid_token`;
  - `/assets/*` comes from a `StaticFiles` mount (`:185`);
  - handled errors (`AppError`, `HTTPException`, `RequestValidationError`) come from `register_error_handlers` (`backend/src/catchup/errors.py:39-42`).
- **Unhandled exceptions.** Starlette's `ServerErrorMiddleware` sits outside every app middleware. It writes its own plain-text 500, "Internal Server Error", and re-raises the exception.
- **A probe on 2026-11-03** (Starlette 1.7.0, FastAPI 0.142.2, a temporary dist, a test-only route that raises) registered a header middleware after `create_app`:
  - it saw every response listed in the delta, except the unhandled 500;
  - with a handler registered for `Exception`, the 500 carried the headers and kept its body, and `TestClient` still raised the exception.
- **No existing policy.** Nothing in the code sets `X-Frame-Options` or `Content-Security-Policy`. Nothing frames CatchUp: there is no `<iframe>` in `frontend/` or `extension/src`. The extension opens CatchUp in a tab with `chrome.tabs.create` (`extension/src/popup.ts:190`, `:301`).

## Goals / Non-Goals

**Goals:**
- Both headers on every response, including the SPA fallback, files at the dist root, errors, and the unhandled 500.
- No change to any status, body, or content type.

**Non-Goals:**
- Any other CSP directive. A fuller policy would have to allow images from any source site (`user-interface`, "Show chosen images from their source sites"), and is a separate decision.
- Headers on the Vite dev server.

## Decisions

### D1. One outermost middleware, registered last
- **What.** Add `refuse_framing`, a `@app.middleware("http")` function, as the last registration in `create_app`, after the `if (frontend_dist / "index.html").is_file():` block and just before `return app`. It awaits `call_next`, then sets `X-Frame-Options` to `DENY` and `Content-Security-Policy` to `frame-ancestors 'none'` on the response, by assignment, and returns it.
- **Why last.** Starlette runs it first, so it wraps `spa_fallback`'s new `FileResponse`, the host and cross-site refusals, the static mount, and the routes.
- **Why outside the `if`.** It must also run when no frontend is built, for example in the API-only test setup.
- **A comment** at the registration says that it must stay last, and that a future `Content-Security-Policy` must keep `frame-ancestors 'none'`.
- **Alternatives:**
  - A pure ASGI middleware that wraps `send`. Not needed: the probe showed the `http` middleware reaches every response the app builds, and the file already uses that style three times.
  - `response.headers.setdefault`. Rejected: nothing sets either header today, and plain assignment cannot leave a second, weaker value.

### D2. The same plain 500, with the headers
- **What.** Register a handler for `Exception` in `create_app`, next to D1. It returns `PlainTextResponse("Internal Server Error", status_code=500, headers=...)`, with the same two headers from one module constant that D1 also uses.
- **Why.** Starlette passes a handler for `Exception` to `ServerErrorMiddleware`, which then sends that response in place of its own. The body and type match Starlette's default, and the exception is still re-raised, so logs and test behavior do not change (probe).
- **Alternative:** leave the 500 without the headers, because it has no controls to click. Rejected: the requirement says every response, and the cost is a few lines.

### D3. `DENY` and `frame-ancestors 'none'`, not `SAMEORIGIN` and `'self'`
- CatchUp never frames its own pages, so `'self'` would allow nothing that is needed.
- Both headers are sent. Current browsers follow `frame-ancestors`, which takes precedence over `X-Frame-Options`; older browsers know only `X-Frame-Options`.
- A `<meta http-equiv>` policy was rejected, because browsers ignore `frame-ancestors` in `<meta>`.

### D4. Service worker, manifest, and offline page
- A policy with only `frame-ancestors` restricts nothing in a worker, so `sw.js` loads, installs, and fetches as before.
- The offline page that the worker caches keeps the headers it was served with. It is shown as a top-level page, which framing rules do not affect.
- The manifest is fetched, not framed.
- The live check opens the installed app after the change, then opens it with the server stopped.

### D5. The Docker smoke checks the headers
- **Decision.** Yes. In the smoke's first Python block, assert both headers on every response it already reads: `/api/health`, `/`, the three files, and the `PUT`.
- **Why.** The smoke is the only check that runs the shipped image: the installed package, `catchup serve`, and the real `frontend/dist` with the real `offline.html` and `sw.js`. CI runs it on every push (`.github/workflows/ci.yml`). The README promise is about that image. The cost is a few lines in a block that already fetches these addresses.
- **Its red step** builds an image from `main` before this change (`git archive 8faaed6 | docker build -t catchup:refuse-framing-before -`), and sees the new assertion fail there.

## Risks / Trade-offs

- **[Someone embeds CatchUp in their own dashboard]** That no longer works. → This is the intended effect. README states it.
- **[A later change adds a fuller CSP]** It must keep `frame-ancestors 'none'`. → The comment at D1, and `test_framing.py`, which asserts the exact header value.
- **[A middleware registered later, after this one]** It would run outside D1, and the responses it builds itself would lack the headers. → The comment at D1. The fallback tests fail if D1 ends up inside `spa_fallback`, and the no-dist test fails if D1 moves into the `if` block.

## Migration Plan

- No data change. The headers apply from the first response after upgrading.
- Rollback is a revert.
