# Design

Lean change for issues #39 and #23. See `proposal.md` for the motivation, and the `source-management` delta for the requirements.

## Context

- **`discover`** (`backend/src/catchup/sources/discovery.py:53-126`):
  - It fetches the pasted URL first; a `FetchError` there propagates immediately.
  - Only after an HTML page that declares no feed does it probe `_probes(url)`: the page path plus `.rss` or `/.rss`, then `COMMON_PATHS`. Probing is same-origin, uses a budget of 8 requests, and keeps the "follows the whole site" notice for origin-level paths found from a deeper page.
  - In the declared-feed loop, every `FetchError` except `rate_limited` is swallowed, and the loop ends with `not_a_feed`.
- **`safe_fetch`** raises `FetchError("fetch_failed", "The source could not be fetched.", status_code)` for HTTP errors (`backend/src/catchup/net/safe_fetch.py:186-189`). For timeouts, DNS failures, and blocked addresses, `status_code` is `None` or the code differs. Rate limits raise `rate_limited` with `retry_after`.
- **API errors.** `_fetch_error` (`backend/src/catchup/api/sources.py:32-33`) passes only `retry_after`. `AppError` details become extra fields of the error JSON (`backend/src/catchup/errors.py:17-21`).
- **The frontend.**
  - `ApiError` keeps `code`, `message`, and `retryAfter` (`frontend/src/api/client.ts`).
  - `describeError` maps each code to one fixed message (`frontend/src/pages/Sources.tsx:21-37`).

## Decisions

### D1. Probe after an HTTP failure of the pasted page
- **When probing runs.** If the first fetch of the pasted URL raises `FetchError` with code `fetch_failed` and a `status_code` of 400 or higher, `discover` probes `_probes(url)` on the pasted URL's origin. The redirect target is unknown when the fetch failed, so the pasted URL's origin is used.
- **Same rules as today.** Probing keeps today's budget, same-origin check, "has entries" rule, and notice rule. The notice applies when the pasted path is deeper than "/" and the feed was found at an origin-level path.
- **What still stops discovery.** Any other `FetchError` stops it as today: `rate_limited`, timeouts and DNS failures without a status, `blocked_address`, and `invalid_url`.
- **When probing finds nothing,** `discover` re-raises the original page error, keeping its `status_code`. It does not raise `no_feed`, because the page itself was never seen.
- **Alternative:** retrying the page with a browser-like user agent. Rejected: CatchUp identifies itself on purpose (`source-management`, "Identify CatchUp in outgoing requests"), and `spaces.ac.cn` also refuses a plain `Mozilla/5.0` request.

### D2. Error codes
- **`fetch_failed` with `http_status`.** The pasted page answered an HTTP error, and no feed was found.
- **`feed_unavailable` with `http_status`** (new). Every declared feed candidate failed with an HTTP error, or the confirm-time re-fetch of the feed did. When several candidates failed, the status of the last one is used.
- **`not_a_feed`.** At least one declared candidate was fetched but could not be parsed (this takes precedence over HTTP failures), or the fetched content is not a feed, as today.
- **`no_feed`.** The page loaded, declared no feed, and no probe found one.
- **`rate_limited`.** Unchanged, and still raised immediately.
- **Alternative:** one `fetch_failed` code with a `stage` field. Rejected: a separate code keeps the frontend mapping flat, and makes the declared-feed case testable on its own.

### D3. API payload
- `_fetch_error` adds `http_status` whenever `exc.status_code` is set, for `fetch_failed` and `feed_unavailable`. It still adds `retry_after` for `rate_limited`.
- The confirm endpoint (`sources.py:89-100`) reports an HTTP failure of its feed re-fetch as `feed_unavailable`, with `http_status`.

### D4. Messages on the Sources page
`ApiError` gains `httpStatus`, read from `http_status`. `describeError` maps:

| Code and status | Message |
|---|---|
| `fetch_failed`, 401 or 403 | "The site refused the request (HTTP 403). If you know its feed URL, paste that instead." |
| `fetch_failed`, 404 or 410 | "The page was not found (HTTP 404). Check the URL, or paste the site's feed URL." |
| `fetch_failed`, 5xx | "The site is not responding (HTTP 503). Try again later." |
| `fetch_failed`, other status | "The site answered HTTP 418. Check the URL, or paste the site's feed URL." |
| `fetch_failed`, no status | Unchanged: "Could not fetch the source. Check the URL and try again." |
| `feed_unavailable` | "The site's feed is temporarily unavailable (HTTP 404). Try again later." When there is no status, the parenthesis is left out. |

Each message shows the actual status. The other codes are unchanged.

## Risks / Trade-offs

- **[Extra requests to a refusing site]** Up to 8 probe requests follow a refused page. → They use the same budget and same-origin limit as today's probing, and they stop at the first feed with entries.
- **[A 404 on a mistyped article URL finds the site's feed]** → The preview shows the feed it found, and the existing notice says that CatchUp will follow the whole site, so the user can cancel.
- **[Mixed failures]** For example, one declared candidate answers 404 and another is not a feed. → `not_a_feed` wins (D2): something was fetched and was the wrong format.

## Migration Plan

- No data change. Clients that ignore `http_status` keep working; the new code `feed_unavailable` falls back to the backend message in any older frontend.
- Rollback is a revert.
