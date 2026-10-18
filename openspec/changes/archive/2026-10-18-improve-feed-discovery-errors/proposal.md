# Proposal

## Why

Two failures when adding a source give the user a wrong or useless answer.

- **#39.** Pasting `https://spaces.ac.cn/` fails with "Could not fetch the source. Check the URL and try again", although the site's feed at `/feed` works. The home page answers HTTP 403. Discovery stops at that failed page fetch, and it tries common feed locations only after a page that loads without declaring a feed (`backend/src/catchup/sources/discovery.py`, `discover`).
- **#23.** When a page declares a feed but the feed itself answers an HTTP error, the preview says "The declared feed could not be parsed." That points at a format problem when the feed is simply unavailable. This was seen when YouTube's channel feeds returned 404 for 40+ minutes on 2026-10-05.
- **No status in the message.** In both cases, the HTTP status is known (`FetchError.status_code`), but it is dropped. The Sources page shows one fixed message per error code (`frontend/src/pages/Sources.tsx:21-27`).

## What Changes

- **Probe after a failed page fetch.** When the pasted page itself answers an HTTP error, discovery still tries the bounded list of common feed locations on the same site, with the same budget and same-origin rule as today. Timeouts, DNS failures, blocked addresses, and rate limits stop discovery as they do today. When the pasted URL is deeper than the site root, the preview says that CatchUp will follow the site's feed.
- **Name the cause and the HTTP status.**
  - **The page fails** with an HTTP error and no feed is found: the error stays `fetch_failed`, now with `http_status`. The Sources page names the status and suggests what to do:
    - 401/403: the site refused the request, so paste its feed URL.
    - 404/410: the page was not found, so check the URL or paste the feed URL.
    - 5xx: the site is not responding, so try again later.
    - Any other status is named as it is.
  - **Every declared feed fails** with an HTTP error, or the feed re-fetched on confirm does: a new code, `feed_unavailable`, with `http_status`, meaning the site's feed is temporarily unavailable; try again later.
  - **Unchanged.** `not_a_feed` is kept for content that was fetched but could not be parsed, and `no_feed` for when nothing was found.
- **The API's error payload** carries `http_status` whenever a fetch failed with an HTTP status, the same way it carries `retry_after` for rate limits.
- **Unchanged:** rate-limit handling and its message, the safe-fetch rules (blocked addresses, size limits, timeouts), run-time source checks, and the preview cache.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `source-management`, "Preview a source from a pasted URL": try common feed locations after a failed page fetch, with a scenario for a refused page whose feed works.
- `source-management`, "Explain unsupported and duplicate sources": name the HTTP status, and tell an unavailable feed from an unparsable one. Scenarios cover a refused page with no feed, and a declared feed that answers 404.

## Impact

- **Backend.**
  - `backend/src/catchup/sources/discovery.py`: probing after a failed page fetch, and the reported error.
  - `backend/src/catchup/api/sources.py`: `_fetch_error` adds `http_status`, and the confirm re-fetch reports `feed_unavailable`.
  - Tests in `backend/tests/test_discovery.py` and `backend/tests/test_sources_api.py`.
- **Frontend.**
  - `frontend/src/api/client.ts`: `ApiError` carries `httpStatus`.
  - `frontend/src/pages/Sources.tsx`: the new messages.
  - Tests in `frontend/src/pages/Sources.test.tsx`.
- **No change** to the database, the run pipeline, or the source list.
