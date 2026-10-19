# Proposal

## Why

Two recent changes left known test gaps. In each case the behavior is correct today, but a later edit could break it without a failing test.

- **`improve-feed-discovery-errors` (#39, #23), tracked in #44.** The final mutation run left four of these:
  1. **Mixed declared-feed failures.** Reducing the declared-candidate guard in `backend/src/catchup/sources/discovery.py` to `exc.code == "fetch_failed"` makes "404, then over the size limit" lose its 404, and makes "blocked, then over the size limit" stop reporting `blocked_address`. Every existing test declares only one failing feed.
  2. **Statuses 303 to 399.** Raising the bound in `http_error_status` or in `describeError` (`frontend/src/pages/Sources.tsx`) to `>= 303` fails no test. A 307 or 308 without `Location` is a real case.
  3. **Statuses of 600 and above.** An upper bound such as `< 600` in `http_error_status` survives. Design D2 says "400 or higher".
  4. **Message text.** Nothing checks the backend `FEED_UNAVAILABLE_MESSAGE` text, which an older frontend shows as is.
- **`show-attention-sources-after-run` (#38).** The 12-row ended-run table in `frontend/src/pages/Home.test.tsx` does not check each state's result title:
  - Dropping "Your digest is ready" from the compact result line survives.
  - Changing the "Digest generation failed" alert title, in both layouts or only in the compact bar, survives.

## What Changes

- **Backend tests** in `backend/tests/test_discovery.py` and `backend/tests/test_sources_api.py` for items 1–4.
- **Frontend tests** in `frontend/src/pages/Sources.test.tsx` (item 2) and `frontend/src/pages/Home.test.tsx` (the result titles).
- **Each new check is red-tested by a named temporary mutation,** because the code is already correct.
- **No change** to runtime code, behavior, or specs, so `skip_specs: true` is set.
- **Left out on purpose:**
  - The row order of the attention list. The spec does not require an order.
  - Item 5 of #44, the plan wording. It needs no test.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- None. Tests only; `skip_specs: true` is set in `.openspec.yaml`.

## Impact

- Test files only: `backend/tests/test_discovery.py`, `backend/tests/test_sources_api.py`, `frontend/src/pages/Sources.test.tsx`, `frontend/src/pages/Home.test.tsx`.
- A test report and an AI usage log entry in `docs/process/`.
