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
- **Not for the Apple lookup's feed URL** (fix round 1). The feed URL that Apple's lookup returns is fetched without this probing, so that a failed show feed never turns into an unrelated feed on the same host. Its fetch failures follow D2. A feed URL that returns an HTML page keeps today's handling: declared feeds first, then the common locations.
- **Alternative:** retrying the page with a browser-like user agent. Rejected: CatchUp identifies itself on purpose (`source-management`, "Identify CatchUp in outgoing requests"), and `spaces.ac.cn` also refuses a plain `Mozilla/5.0` request.

### D2. Error codes
- **What counts as an HTTP error.** In this design, an HTTP error is a `FetchError` with code `fetch_failed` and a `status_code` of 400 or higher. `safe_fetch` also raises `fetch_failed` with a lower status: 200 when the body exceeds the size limit or the read times out, and 302 for a redirect without a usable `Location`. Those are not HTTP errors (fix round 1).
- **`fetch_failed` with `http_status`.** The pasted page answered an HTTP error, and no probe found a feed.
- **`fetch_failed` without `http_status`.** The pasted page could not be fetched for any other reason, as today.
- **`feed_unavailable`** (new). A feed could not be fetched. This covers the declared candidates, the feed URL from Apple's lookup, and the confirm-time re-fetch (HTTP errors only, see D3).
  - With `http_status` when the failure was an HTTP error. When several declared candidates answered HTTP errors, the status of the last one is used.
  - Without `http_status` when the feed could not be fetched for another reason, such as a timeout, an unresolvable host, a redirect without a usable `Location`, a body over the size limit, or an invalid candidate URL (fix round 1).
- **Declared candidates.** When no declared candidate yields a feed, the error follows this precedence (fix round 1):
  1. `not_a_feed` ("The declared feed could not be parsed.") if any candidate was fetched but could not be parsed;
  2. otherwise `feed_unavailable` with the status, if any candidate answered an HTTP error;
  3. otherwise `blocked_address`, if any candidate targets a blocked address;
  4. otherwise `feed_unavailable` without a status.
- **The Apple lookup's feed URL** (fix round 1). If fetching it fails, `discover` raises `feed_unavailable`, with or without the status as above. `rate_limited` and `blocked_address` keep their codes.
- **`not_a_feed`.** Content was fetched but is not a parsable feed, as today.
- **`no_feed`.** The page loaded, declared no feed, and no probe found one.
- **`rate_limited`.** Unchanged, and still raised immediately.
- **Alternative:** one `fetch_failed` code with a `stage` field. Rejected: a separate code keeps the frontend mapping flat, and makes the declared-feed case testable on its own.

### D3. API payload
- `_fetch_error` adds `http_status` only for `fetch_failed` and `feed_unavailable` errors whose `status_code` is 400 or higher. A lower status never reaches the payload (fix round 1). It still adds `retry_after` for `rate_limited`.
- The confirm endpoint (`sources.py:89-100`) reports an HTTP error of its feed re-fetch as `feed_unavailable`, with `http_status`. Its other fetch failures stay `fetch_failed`, without `http_status`.

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

Fix round 1 makes the bounds explicit:
- `httpStatus` counts only when it is 400 or higher. A missing or lower status gets the no-status message for that code.
- "5xx" means 500 to 599.
- "Other status" covers the remaining statuses of 400 or higher, including 600 and above.

## Risks / Trade-offs

- **[Extra requests to a refusing site]** Up to 8 probe requests follow a refused page. → They use the same budget and same-origin limit as today's probing, and they stop at the first feed with entries.
- **[A 404 on a mistyped article URL finds the site's feed]** → The preview shows the feed it found, and the existing notice says that CatchUp will follow the whole site, so the user can cancel.
- **[Mixed failures]** For example, one declared candidate answers 404 and another is not a feed. → `not_a_feed` wins (D2): something was fetched and was the wrong format.
- **[Known limit: redirect to another origin]** The pasted URL redirects to another origin (for example http to https, or a bare domain to `www`), and the page there refuses the request. `safe_fetch` raises without the final URL, so probing uses the pasted origin. Every probe there redirects off-origin and is skipped, and the user sees the page error. → Fixing this needs `safe_fetch` to report the final URL, which is out of scope. The workaround is to paste the final URL or the feed URL.
- **[Known limit: a pasted feed URL that answers an HTTP error]** It is reported as a page error, for example "The page was not found (HTTP 404)", because nothing tells a feed from a page before a successful fetch. → The #23 case, a feed declared by a page, is reported as temporarily unavailable.

## Migration Plan

- No data change. Clients that ignore `http_status` keep working; the new code `feed_unavailable` falls back to the backend message in any older frontend.
- Rollback is a revert.
