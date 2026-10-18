# Tasks

Implementer notes:
- **Read first.** Read `proposal.md`, `design.md` (D1–D4), and `specs/source-management/spec.md`. If something looks wrong or contradictory, stop and report instead of redesigning.
- **Work test-first with the `tdd` skill** (D-016). For each task, first write its verification items as failing tests and watch them fail, then implement until they pass. The seams to test are the ones named in each task; they count as agreed.
- **Test rules.** Backend tests use `respx` and the autouse DNS block, with no real network. Frontend tests mock `fetch`. No real sleeps.
- **Out of scope:**
  - `safe_fetch` (`backend/src/catchup/net/safe_fetch.py`)
  - the rate-limit handling and its message
  - run-time source checks (`backend/src/catchup/collection.py`)
  - the preview cache
  - the Sources list
- **Commits.** Commit after each task group. Do not push, tag, or open a PR.

## 1. Discovery (backend)

- [x] 1.1 In `backend/tests/test_discovery.py`, add failing tests for `discover`, using `respx` and the existing `public_dns` fixture:
  1. **Refused page, working feed.** The home page answers 403, and `/feed` answers a valid RSS document. `discover` returns that feed.
  2. **Notice from a deeper page.** A deeper path such as `/blog/post` answers 403, and `/feed` works. The returned discovery has the "follows the whole site" notice set.
  3. **Refused page, no feed.** The page answers 403, and every probe answers 404. `discover` raises `FetchError` with code `fetch_failed` and `status_code` 403, not `no_feed`.
  4. **Server error, then probing.** The page answers 503 without `Retry-After`, and `/feed` works. The feed is found.
  5. **Rate limit, no probing.** The page answers 429 with `Retry-After: 120`. `rate_limited` is raised, and no probe request is made.
  6. **Timeout, no probing.** The page times out. `fetch_failed` without a status is raised, and no probe request is made.
  7. **Declared feed unavailable (#23).** The page declares one feed, and that feed answers 404. `discover` raises code `feed_unavailable` with `status_code` 404.
  8. **Mixed declared failures.** The page declares two feeds: one answers 404, and one answers 200 with content that is not a feed. `not_a_feed` is raised.

  Verify: the new tests fail before 1.2, and existing discovery tests still pass.
- [x] 1.2 Implement design D1 and D2 in `backend/src/catchup/sources/discovery.py`.

  Verify: the 1.1 tests pass, and `uv run pytest tests/test_discovery.py` passes.

## 2. API payload (backend)

- [x] 2.1 In `backend/tests/test_sources_api.py`, add failing tests:
  - A preview of a refused page with no feed returns 422 with `{"code": "fetch_failed", "http_status": 403}`.
  - A preview whose declared feed answers 404 returns 422 with `{"code": "feed_unavailable", "http_status": 404}`.
  - A confirm whose feed re-fetch answers 404 (no preview cache) returns 422 with `{"code": "feed_unavailable", "http_status": 404}`.
  - A rate-limited preview still returns `retry_after`, and no `http_status` is required.

  Verify: these fail before 2.2.
- [x] 2.2 Implement design D3 in `backend/src/catchup/api/sources.py`, in `_fetch_error` and in the confirm error path.

  Verify: the 2.1 tests pass, `uv run pytest` passes, and coverage for `api/sources.py` and `sources/discovery.py` does not drop.

## 3. Messages (frontend)

- [x] 3.1 In `frontend/src/pages/Sources.test.tsx`, add failing tests for the preview error message. Each case mocks the preview response.
  - `fetch_failed` with 403, with 404, with 503, with 418, and without `http_status` (the message is unchanged).
  - `feed_unavailable` with 404, and without a status.

  Each case asserts the exact text in design D4, including the status number.

  Verify: these fail before 3.2.
- [x] 3.2 Implement design D4:
  - `frontend/src/api/client.ts`: `ApiError` reads `http_status` into `httpStatus`.
  - `frontend/src/pages/Sources.tsx`: `describeError` uses it.

  Verify: the 3.1 tests pass, the existing `Sources.test.tsx` and `client` tests pass, and `npm test -- --run` and `npm run build` pass.

## 4. Integration checks and report

- [x] 4.1 Run the full checks:
  - `uv run pytest --cov=catchup --cov-report=term` in `backend/` (count and coverage)
  - `npm test -- --run` and `npm run build` in `frontend/`
  - `openspec validate improve-feed-discovery-errors --strict`
  - a local `docker build`, if available

  Write the commands and their real results to `docs/process/test-report-improve-feed-discovery-errors.md`. List the manual check that was not performed: pasting `https://spaces.ac.cn/` on a local instance.

  Add your entry to `docs/process/ai-usage-log.md` after the latest entry, with a faithful prompt excerpt. Leave out the session id; Claude Code adds it at review.

  Verify: every command passes, and the report has the actual numbers.

## 5. Fix round 1 (review findings)

Read the amended `design.md` (D1 "Not for the Apple lookup's feed URL", D2 "What counts as an HTTP error" and the precedence list, D3, the D4 bounds, and the two known limits under Risks) and the two new scenarios in `specs/source-management/spec.md` ("Declared feed cannot be fetched" and "Apple Podcasts feed unavailable"). These are confirmed bugs and test gaps from review, so use the `diagnosing-bugs` skill for 5.1–5.2 and `tdd` for the rest: write each check first and watch it fail, unless the task says it may already pass.

- [x] 5.1 In `backend/tests/test_discovery.py`, add failing tests, using `respx` and the `public_dns` fixture:
  1. **Declared feed times out.** The page declares one feed, and fetching it raises `httpx.ConnectTimeout`. `discover` raises `feed_unavailable` with `status_code` `None`.
  2. **Declared feed over the size limit.** With a small `max_feed_bytes`, the declared feed answers 200 with a larger body. `feed_unavailable`, with no status.
  3. **Declared feed redirect without `Location`.** The declared feed answers 302 with no `Location`. `feed_unavailable`, with no status.
  4. **Declared feed at a blocked address.** The page declares `https://internal.example/feed.xml`, and a test DNS stub resolves `internal.example` to `10.0.0.1` and every other host to a public address. (The `public_dns` fixture resolves every host, including `127.0.0.1`, to a public address, so it cannot be used here.) `blocked_address` is raised.
  5. **Precedence.** Each case declares two feeds: 404 and a timeout → `feed_unavailable` 404; a timeout and unparsable content → `not_a_feed`; a blocked address and a timeout → `blocked_address`; a blocked address and 404 → `feed_unavailable` 404.
  6. **Last status wins.** Two declared feeds answer 404, then 410. `feed_unavailable` with 410.
  7. **Page status bounds.** The page answers 400, and `/feed` works: the feed is found. The page answers 200 with a body over `max_feed_bytes`: `fetch_failed` with `status_code` 200 is raised, and no probe request is made. The page answers 302 without `Location`: no probe request is made.
  8. **Apple feed URL unavailable.** Apple's lookup returns `https://host.example/show.xml`, which answers 404, while `https://host.example/feed` would answer a valid feed. `discover` raises `feed_unavailable` with 404, and the `/feed` route is not called.
  9. **Apple feed URL times out.** The same lookup, and the feed URL times out. `feed_unavailable`, with no status.

  Verify: the new tests fail before 5.2, except any that the report marks as already passing, with the reason.
- [x] 5.2 Implement the amended D1 and D2 in `backend/src/catchup/sources/discovery.py`. For the Apple branch, add a keyword-only parameter to `discover` that only the Apple branch passes. Keep `safe_fetch` unchanged.

  Verify: the 5.1 tests pass, and the existing discovery tests still pass.
- [x] 5.3 In `backend/tests/test_sources_api.py`, add failing tests:
  - A preview whose page body exceeds the size limit returns 422 `fetch_failed`, and the JSON has no `http_status` key.
  - A preview whose declared feed times out returns 422 `feed_unavailable`, with no `http_status` key.
  - A confirm whose feed re-fetch answers 400 returns 422 `feed_unavailable` with `http_status` 400.
  - A confirm whose feed re-fetch exceeds the size limit returns 422 `fetch_failed`, with no `http_status` key.

  Verify: the tests for the payload bound fail before 5.4. The report names any test that already passed, with the reason.
- [x] 5.4 Implement the amended D3 in `backend/src/catchup/api/sources.py`.

  Verify: the 5.3 tests pass, and `uv run pytest` passes.
- [ ] 5.5 In `frontend/src/pages/Sources.test.tsx`, add failing tests for the D4 bounds:
  - `fetch_failed` with 401 gives the refused message, with 410 the not-found message, and with 500 and with 599 the not-responding message.
  - `fetch_failed` with 499 and with 600 gives the other-status message.
  - `fetch_failed` with 200 and with 302 gives the unchanged no-status message.
  - `feed_unavailable` with 200 gives the message without a parenthesis.

  Each case asserts the exact text, including the status number.

  Verify: the cases that today's code gets wrong fail before 5.6. The report names the cases that already passed.
- [ ] 5.6 Implement the D4 bounds in `frontend/src/pages/Sources.tsx`.

  Verify: the 5.5 tests pass, and `npm test -- --run` and `npm run build` pass.
- [ ] 5.7 Rerun the full checks from 4.1, and update the documents:
  - In `docs/process/test-report-improve-feed-discovery-errors.md`, add a "Fix round 1" section with the commands and their real results, and the red-first results of 5.1, 5.3, and 5.5.
  - Correct the final coverage line of the first run: 1,838 of 1,913 statements, 75 missed.
  - List the two known limits from design.md Risks.
  - Update this change's line in `docs/process/coverage-summary.md` with the new numbers.
  - Add a fix-round entry to `docs/process/ai-usage-log.md` after the latest entry, with a faithful prompt excerpt. Leave out the session id; Claude Code adds it at review.

  Verify: every command passes, and the report has the actual numbers.
