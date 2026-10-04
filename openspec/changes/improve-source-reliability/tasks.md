# Tasks

Implementer notes:
- Read `proposal.md`, `design.md` (D2–D6), and both files under `specs/` first. Follow them; if something looks wrong, stop and report rather than redesigning.
- Treat these rules as verification criteria, not notes:
  - Tests make no real network calls (respx; DNS is blocked by the autouse fixture in `backend/tests/conftest.py`).
  - Tests use no real API key.
  - Tests write nothing outside pytest temp dirs.
  - Tests use **no real sleeps**. Patch the sleep hooks and inject clocks.
- Backend commands run from `backend/` with uv; frontend commands run from `frontend/` with npm.
- Commit after each task group. Do not edit `proposal.md`, `design.md`, or `specs/`.

## 1. Identify CatchUp and honor rate limits in `safe_fetch`

- [x] 1.1 Add the User-Agent per design.md D2:
  - `CATCHUP_USER_AGENT_CONTACT` in `backend/src/catchup/config.py`, with validation (printable ASCII, no CR/LF, ≤ 100 chars) that fails at startup with a clear error
  - the header on the `httpx.Client` in `backend/src/catchup/net/safe_fetch.py`
  - the version from `importlib.metadata` with a `0.0.0` fallback

  Verify: tests assert the exact header with and without a contact, that an invalid contact (e.g. containing `\r\n`) is rejected, and (respx) that the header is present on a redirect hop.
- [x] 1.2 Add `Retry-After` parsing per design.md D3 (delay-seconds; HTTP-date in IMF-fixdate, RFC 850, and asctime; past → 0; invalid → `None`) as a small function in `safe_fetch.py` or a new `net/retry_after.py`. Verify: unit tests for each format, a past date, an empty value, and garbage.
- [x] 1.3 Implement the retry policy per design.md D3 in `safe_fetch.py`:
  - 429, or 503 with `Retry-After`, is retried once when ≤ 10 s and within the deadline (a patchable module-level sleep hook)
  - otherwise `FetchError("rate_limited", message, status_code, retry_after=…)`
  - `FetchError` gains `retry_after`
  - 503 without `Retry-After` stays `fetch_failed`
  - a retry consumes probing `budget`

  Verify: respx tests for every scenario in "Honor rate limits when fetching" (`specs/source-management/spec.md`), plus 503 with and without the header, plus a test that a retry is skipped when the remaining deadline is too short (injected clock). Assert request counts.

## 2. Reuse a recent preview on confirm

- [ ] 2.1 Add `backend/src/catchup/net/feed_cache.py` (`FeedCache`: lock, TTL 600 s, max 50 with oldest evicted, pop on use, injectable clock) per design.md D4. Create it on `app.state.feed_cache` in `create_app`. Pass it to `discover(url, cache=…)` from preview, which stores the final feed response under its final URL. In `confirm` (`backend/src/catchup/api/sources.py`), pop a fresh entry for `feed_url` instead of fetching, and fall back to fetching otherwise. Verify:
  - unit tests for TTL, cap, and pop
  - API tests: preview → confirm makes exactly one request to the feed URL (respx call count); confirm after the TTL (injected clock) fetches again; confirm without any preview fetches
  - existing source tests still pass

## 3. Run politeness and showing "rate limited"

- [ ] 3.1 Add `backend/src/catchup/net/host_spacing.py` (`HostSpacer`, min interval 1.0 s, case-insensitive host, thread-safe, injectable clock and sleep) per design.md D5. Add `safe_fetch(..., spacer=None)`, which calls `spacer.wait(url)` before every request, including redirects and retries. Pass it through:
  - the runner creates one `HostSpacer` per run (`digest/runner.py`)
  - `check_source(..., spacer=)` and `article_text(..., spacer=)` (`collection.py`)
  - confirm's article fetches use their own `HostSpacer`

  Verify: unit tests for same and different hosts; a runner test with two same-host sources asserting ≥ 1 s spacing via the injected clock, and no delay for different hosts.
- [ ] 3.2 Show "rate limited" in the API per design.md D6:
  - one helper decides whether a stored check is rate limited
  - the source list (`api/sources.py`) and run detail (`digest/runner.run_detail`) add `http_status` and `rate_limited` to each check
  - preview and confirm map `rate_limited` to `422` with `retry_after`

  Verify: tests for every scenario in `specs/content-collection/spec.md` "Identify rate-limited checks", the preview and confirm 422 shape, and a 503 rate-limit check detected via the shared message prefix.
- [ ] 3.3 Update the frontend per design.md D6:
  - `frontend/src/pages/Sources.tsx`: a "Rate limited — try again later" message (include the wait when given) for preview/confirm, and a "Rate limited" badge in the list
  - `frontend/src/pages/Generate.tsx`: label rate-limited checks "rate limited (try later)"

  Verify: Vitest tests for the preview error, the list badge, and the Generate label; `npm run build` passes.

## 4. Documentation and test report

- [ ] 4.1 Update `README.md` and `.env.example`:
  - in Supported sources, state that Reddit support ends on 2026-11-13 because Reddit is discontinuing RSS, citing the TechCrunch report URL from `research.md`
  - document `CATCHUP_USER_AGENT_CONTACT` and the User-Agent CatchUp sends

  Verify: the README renders the new text, and `.env.example` lists the variable commented out.
- [ ] 4.2 Write `docs/process/test-report-improve-source-reliability.md`:
  - the commands and results
  - backend coverage for the new and changed modules
  - a table mapping every scenario in both spec files under `specs/` to its tests, listing any scenario without a test explicitly
  - a placeholder "Manual verification" section for the reviewer

  Also append a short entry to `docs/process/ai-usage-log.md`. Verify: every scenario in both spec files appears in the table.

Manual verification (Reddit preview → confirm without waiting; User-Agent seen by a server) is done during review by Claude Code with the user, not by the implementer.
