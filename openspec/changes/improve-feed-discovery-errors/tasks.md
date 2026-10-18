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

- [ ] 3.1 In `frontend/src/pages/Sources.test.tsx`, add failing tests for the preview error message. Each case mocks the preview response.
  - `fetch_failed` with 403, with 404, with 503, with 418, and without `http_status` (the message is unchanged).
  - `feed_unavailable` with 404, and without a status.

  Each case asserts the exact text in design D4, including the status number.

  Verify: these fail before 3.2.
- [ ] 3.2 Implement design D4:
  - `frontend/src/api/client.ts`: `ApiError` reads `http_status` into `httpStatus`.
  - `frontend/src/pages/Sources.tsx`: `describeError` uses it.

  Verify: the 3.1 tests pass, the existing `Sources.test.tsx` and `client` tests pass, and `npm test -- --run` and `npm run build` pass.

## 4. Integration checks and report

- [ ] 4.1 Run the full checks:
  - `uv run pytest --cov=catchup --cov-report=term` in `backend/` (count and coverage)
  - `npm test -- --run` and `npm run build` in `frontend/`
  - `openspec validate improve-feed-discovery-errors --strict`
  - a local `docker build`, if available

  Write the commands and their real results to `docs/process/test-report-improve-feed-discovery-errors.md`. List the manual check that was not performed: pasting `https://spaces.ac.cn/` on a local instance.

  Add your entry to `docs/process/ai-usage-log.md` after the latest entry, with a faithful prompt excerpt. Leave out the session id; Claude Code adds it at review.

  Verify: every command passes, and the report has the actual numbers.
