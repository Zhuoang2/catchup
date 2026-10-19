# Error bounds and run-bar title test report

2026-10-19, change `cover-error-bound-and-run-bar-test-gaps`. Only tests and docs were committed. All runtime mutations below were temporary, made the named checks fail, and were reverted before the test-group commits.

## Verification

Commands ran from `backend/` or `frontend/` as indicated; OpenSpec ran from the project root.

| Check | Actual result |
| --- | --- |
| `cd backend && uv run pytest -q tests/test_discovery.py -k 'declared_feed_http_error_is_unavailable or declared_feed_http_error_precedes_oversized_candidate or declared_feed_blocked_address_precedes_oversized_candidate or declared_feed_status_600_is_unavailable or page_307_without_location_does_not_probe'` | First run: **3 failed, 2 passed**. The limit was initially set to 100 bytes, below the declared HTML page's size; the optional probe route also needed `assert_all_called=False`. Raised the limit to 512 bytes and enlarged the candidate body to 1,024 bytes, correcting the test fixtures, not runtime code. Rerun: **5 passed**, 49 deselected. |
| `cd backend && uv run pytest -q tests/test_discovery.py` after restoring the mutations | **54 passed**. |
| `cd backend && uv run pytest -q tests/test_sources_api.py -k preview_307_without_location_omits_http_status` | **1 passed**, 50 deselected; after the mutation and restoration, the same check passed again in the full suite. |
| `cd frontend && npm test -- --run src/pages/Sources.test.tsx -t 'bounds the preview message'` | **10 passed**, 22 skipped, including the new 307 row and accessibility check. |
| `cd backend && uv run pytest` after task group 1 | **416 passed**. |
| `cd frontend && npm test -- --run` after task group 1 | **200 passed** in 13 files. |
| `cd frontend && npm test -- --run src/pages/Home.test.tsx -t 'shows .* in the .* layout with'` | **12 passed**, 63 skipped, before the mutations. |
| `cd frontend && npm test -- --run` after restoring task group 2 mutations | **200 passed** in 13 files. |
| `cd frontend && npm run build` (task 3.1, first) | Passed TypeScript and Vite build; **41 modules transformed**. |
| `cd backend && uv run pytest --cov=catchup --cov-report=term` (task 3.1, second) | **416 passed**, **96%** statement coverage (**1,854/1,926**, 72 missed). `sources/discovery.py`: **97%** (132/136); `api/sources.py`: **91%** (106/116). |
| `cd frontend && npm test -- --run` (task 3.1, third) | **200 passed** in **13 files**. |
| `openspec validate cover-error-bound-and-run-bar-test-gaps --strict` (task 3.1, fourth) | Valid; `skip_specs` accepts zero deltas. |

## Temporary mutation checks

Each row passed on the unchanged code before the mutation, failed with the indicated temporary mutation, and passed again after restoration (focused rerun or full suite).

| Task/check | Mutation | Observed failing result |
| --- | --- | --- |
| 1.1, 404 then oversized; blocked then oversized | Reduce the declared-candidate guard to `if exc.code == "fetch_failed":`. | **2 failed** in the focused run, and 4 in the full suite. The full suite also fails 2 existing precedence rows, which already caught this mutation before this change (found at review). The HTTP status became `None` instead of 404, and `feed_unavailable` replaced `blocked_address`. |
| 1.1, page 307 without `Location` | Change `http_error_status` to `>= 303`. | **1 failed**: 8 fetches instead of 1, including probes. |
| 1.1, declared feed status 600 | Add `and exc.status_code < 600` to `http_error_status`. | **1 failed**: status became `None` instead of 600. |
| 1.1, unavailable message | Change `FEED_UNAVAILABLE_MESSAGE` to "The site's feed is unavailable." | **1 failed**: exact expected message differed. |
| 1.2, preview page 307 without `Location` | Change `http_error_status` to `>= 303`. | **1 failed**: API JSON included `http_status: 307` instead of omitting the key. |
| 1.2, frontend preview status 307 | Change `describeError` status bound in `Sources.tsx` to `>= 303`. | **1 failed**: UI said "The site answered HTTP 307..." instead of the no-status message. |
| 2.1, succeeded compact title | Drop the title from the compact succeeded result line. | **2 failed**: both compact succeeded rows lacked "Your digest is ready". |
| 2.1, failed title in both layouts | Change the failed-branch `Alert` title to "Digest failed". | **4 failed**: all failed rows lacked the exact alert title. |
| 2.1, failed compact title only | Change the failed-branch `Alert` title only when `compact`. | **2 failed**: both compact failed rows lacked the exact alert title. |

The backend uses `respx` and DNS fixtures with no real network calls. Frontend tests mock `fetch`, use no new timers, and run `expectAccessible` on the newly checked rendered states. No live feed or model run was performed.
