# Design

## Context

See `proposal.md` for the problem. The facts that shape the design:
- **The host check.** The `allowed_host` middleware (`backend/src/catchup/main.py:50-77`) checks the `Host` header's hostname against `CATCHUP_ALLOWED_HOSTS`. It accepts any port. It runs on every request, before any route.
- **Same-origin calls.** The frontend calls `fetch('/api' + path)` on its own origin (`frontend/src/api/client.ts:14-15`). Browsers send `Origin` on same-origin `POST`, `PUT`, and `DELETE`, but not on `GET`. Modern browsers also send `Sec-Fetch-Site` on every request.
- **The dev proxy.** The Vite dev server proxies `/api` without `changeOrigin` (`frontend/vite.config.ts:7-8`). The `Host` header therefore stays `localhost:5173`, the page's own origin.
- **Domain deployments.** README tells them to add their domain to `CATCHUP_ALLOWED_HOSTS` (`README.md:59-63, 129-136`). This works only when the proxy passes the browser's `Host` header.
- **Tools.** The tests (`TestClient`), the Docker smoke script, and `curl` send neither `Origin` nor `Sec-Fetch-Site`.

## Goals / Non-Goals

**Goals:**
- No other web page can make CatchUp change data or start work.
- Nothing changes for CatchUp's own pages and for tools.

**Non-Goals:**
- Authentication or a login. CatchUp stays a single-user local app (D-011).
- Protecting `GET` responses. Without CORS headers, other pages cannot read them.
- The extension's token path. #58 adds it later, at the place this check makes its decision.

## Decisions

### D1. Compare `Origin` with `Host`, and use Fetch Metadata as a second signal
- **The rule.** A new middleware, placed after `allowed_host`, handles `POST`, `PUT`, `PATCH`, and `DELETE` on any path. It refuses when either holds:
  1. **`Origin` is present and does not match the request.** It does not match when it is `null`, is not `http` or `https`, or its hostname and port differ from the `Host` header's. The comparison is case-insensitive, IPv6 brackets are stripped, and a missing port means the default port for the `Origin`'s scheme (80 or 443).
  2. **`Sec-Fetch-Site` is `cross-site` or `same-site`.** `same-origin` and `none` pass.
- **The refusal.** `403 {"error": {"code": "cross_site_request", "message": "This request came from another site and was refused."}}`, before any route runs.
- **Why `Host`.** The `Host` header has already passed the allow list, so it is the address the browser used. Comparing ports too makes another local app, such as `http://localhost:3000`, a different origin. The allow list cannot do this, because it has no ports.
- **Why two signals.** `Origin` covers every browser in use. `Sec-Fetch-Site` also covers requests where a browser omits `Origin`, and it marks other ports on the same host as `same-site`.
- **Alternatives:**
  - **A CSRF token** (a cookie or a page token sent with every write). Rejected: CatchUp has no cookies or sessions, and the token would need new state and a frontend change on every request.
  - **Requiring a custom header** (for example `X-CatchUp: 1`) on writes. Rejected: it needs a frontend change on every write. A custom header forces a preflight, which fails today, so it would also block the future extension until CORS is added.
  - **CORS configuration.** Rejected: CORS controls what pages can read. It does not stop simple requests, which is the problem here.
  - **A `Content-Type: application/json` requirement on `POST /api/digest-runs` only.** Rejected as the fix: it fixes one route, and leaves the rule implicit for any future bodiless route.

### D2. Raise the FastAPI floor to `>=0.132`
- From 0.132, FastAPI rejects request bodies whose content type is missing or not JSON (https://fastapi.tiangolo.com/advanced/strict-content-type/). This keeps the JSON routes closed to simple requests, even for a tool that sends no `Origin`.
- `backend/uv.lock` already pins 0.142.2. Only `pyproject.toml` and the lock's metadata change.

### D3. Hook for #58
The middleware decides in one place. #58 will add an exception there for requests that carry a valid extension token. Until then, extension origins (`chrome-extension://…`) are refused like any other origin.

## Risks / Trade-offs

- **[Proxies that rewrite `Host`]** CatchUp's own pages would be refused on writes. → The README says the proxy must pass the browser's `Host` header, which the allowed-hosts setting already needs.
- **[TLS in front]** `Origin` is `https://…`, while the app sees `http`. → The scheme is not compared; only the host and port are, with the default port taken from `Origin`'s scheme.
- **[A browser that sends neither header]** It would be treated as a tool, and accepted. → All current browsers send `Origin` on cross-origin `POST`. JSON routes stay protected by D2.

## Migration Plan

- No data change. Rollback: revert the middleware.
- Testing notes:
  - backend tests for the whole matrix, with a configured model for the run case;
  - the existing frontend tests unchanged;
  - `scripts/docker-smoke.sh` on a local image build;
  - a live check at review: a page on another local port that auto-submits a form is refused, and the real UI still works.
