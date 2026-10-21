# Proposal

## Why

Any web page the user opens can start a CatchUp digest run, and spend the user's model tokens (#59). The server's only access control is the Host allow list (`backend/src/catchup/main.py:50-77`). `POST /api/digest-runs` takes no body (`api/runs.py:14-18`), so a plain HTML form on another site can send it as a "simple" request, with no CORS preflight.

A probe on a throwaway instance showed this. With `Origin: https://evil.example` and an empty form body, the request passed the host check and reached `start_run`. It was refused only because no model was configured. This was found during the research for the browser extension (#58), which will add its own authenticated requests later.

## What Changes

- **Refuse cross-site writes.** The server refuses a `POST`, `PUT`, `PATCH`, or `DELETE` request that a browser sends from another origin, with 403 `cross_site_request`. A browser marks such a request in two ways:
  - an `Origin` header whose host and port differ from the request's `Host`, or that is `null` or not http(s);
  - a `Sec-Fetch-Site` header of `cross-site` or `same-site`.
- **Another local port is another origin.** For example, a page on `http://localhost:3000` is refused when it writes to CatchUp on port 8000.
- **No change for:**
  - CatchUp's own pages, including the Vite dev proxy, which keeps the `Host` header;
  - non-browser tools that send neither header, such as `curl`, the tests, and the Docker smoke script;
  - `GET` requests.
- **The FastAPI floor is raised to `>=0.132`** in `backend/pyproject.toml`. From 0.132, FastAPI rejects request bodies without a JSON content type, which keeps the JSON routes safe from simple requests. The lock already pins 0.142.2.
- **No frontend change.**
- **Docs:** a README note, decision D-022, and a requirements-changes row.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `model-settings`: an ADDED requirement, "Refuse write requests from other sites", next to "Accept requests only for allowed hosts", where the server's request-acceptance rule lives today.

## Impact

- **Backend:** `backend/src/catchup/main.py` (a middleware after the host check), `backend/pyproject.toml` and `backend/uv.lock` (the FastAPI floor), and a new test file `backend/tests/test_cross_site.py`.
- **Docs:** `README.md`, and `docs/process/` (the decision log, requirements changes, a test report, the coverage summary, and the AI usage log).
- **Not changed:** the frontend, the API shapes, and the data. Deployments behind a proxy must pass the browser's `Host` header, which `CATCHUP_ALLOWED_HOSTS` already assumes.
