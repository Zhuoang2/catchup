# Proposal

## Why

Another site can show CatchUp inside a frame on its own page (#69, found in the system review of `add-x-accounts` on 2026-11-01).
- **No response refuses framing.** No response sets `X-Frame-Options` or a `Content-Security-Policy` with `frame-ancestors`. A search of `backend/src`, `frontend/index.html`, `frontend/public`, `frontend/src`, and `extension/src` on 2026-11-03 found neither header, no `<meta>` policy, and no `<iframe>`.
- **The write rule does not stop it.** A click inside the frame sends its request from CatchUp's own page, so it is same-origin, and the cross-site write rule (D-022, `backend/src/catchup/main.py:116-142`) accepts it. One tricked click could start a digest run, which costs model and X API reads, remove the X token, or disconnect a browser.
- **README says otherwise.** It says that a page on another site, or on another local port, is refused (`README.md:258-260`).

## What Changes

- **Every response refuses framing.** The server adds `X-Frame-Options: DENY` and `Content-Security-Policy: frame-ancestors 'none'` to every response:
  - pages, including the SPA fallback for client routes;
  - files at the root of the built frontend, such as `/offline.html`, `/sw.js`, and `/manifest.webmanifest`;
  - `/assets/*`;
  - API responses;
  - error responses, including a refused host (400), a refused cross-site write (403), an invalid browser token (401), a not-found address (404), an invalid request (422), and an internal error (500).
- **Nothing else changes.**
  - The policy has only the `frame-ancestors` directive. Scripts, styles, images from source sites, the service worker, the manifest, and the browser extension work as before.
  - Status codes, bodies, and content types stay the same. The internal error keeps its plain-text body, "Internal Server Error".
- **The Docker smoke checks the headers** on the files it already fetches (`design.md`, D5).
- **README** adds a sentence to the paragraph at `README.md:258-260`: other sites cannot show CatchUp inside their own pages.
- **Out of scope:**
  - a fuller Content Security Policy (`script-src`, `img-src`, and others);
  - other security headers, such as `Referrer-Policy` or `X-Content-Type-Options`;
  - the Vite dev server, which serves the frontend only during development.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `model-settings`: an ADDED requirement, "Refuse to be shown inside other sites' pages", next to "Refuse write requests from other sites" (D-022), where the server's rules for requests from other sites live.

## Impact

- **Backend:** `backend/src/catchup/main.py`: one middleware registered last in `create_app`, and a handler for unhandled exceptions. A new test file, `backend/tests/test_framing.py`.
- **Deployment:** `scripts/docker-smoke.sh` checks the headers.
- **Docs:** `README.md`, and in `docs/process/` a test report, a coverage-summary line, a requirements-changes row, and AI usage log entries.
- **Not changed:** the frontend, the extension, the API shapes, and the data.
