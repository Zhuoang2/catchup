# Test report: finish-fix-round-cleanup

Date: 2026-11-17. Implementation starts at `dd1ec68`.

## Environment and method

- Backend: Python 3.12.13, SQLAlchemy 2.1.3. All backend commands below run
  from `backend/`, with `UV_OFFLINE=1 uv run`; the locked environment was
  installed from the local cache, without adding dependencies.
- Tests use the agreed seams in `tasks.md`. New HTTP interactions use
  `respx.mock(assert_all_mocked=True)`. Existing autouse fixtures block real
  socket connections and replace spacing sleeps. No real network or sleeps.
- Each mutation is applied alone, tested, and immediately reversed, including
  on test failure. Exit 1 in the mutation results below is the expected red
  result, not an unresolved failure.

## Group 1: source-check rows

New tests in `tests/test_podcast_collection.py`:

| Test | Initial result | Mutation killed |
| --- | --- | --- |
| `test_podcast_check_loads_only_episodes_it_may_update` | Red: loaded `delivered`, `found`, `waiting`, not only `waiting` | M1, M2 |
| `test_website_check_loads_no_full_rows` | Red: loaded `delivered`, `pending`, not zero rows | M3 |
| `test_feed_upgraded_to_podcast_resolves_pending_item` | Green | M4, M6 |

`uv run pytest tests/test_podcast_collection.py` before implementation:
**2 failed, 7 passed**. All six existing tests and the upgrade guard passed.
The same command after D1: **9 passed**.
`uv run pytest`: **964 passed**.

Each command below has the `UV_OFFLINE=1` prefix:

| Mutation | Command | Actual result |
| --- | --- | --- |
| M1: full rows for every podcast item in `by_key` | `uv run pytest tests/test_podcast_collection.py::test_podcast_check_loads_only_episodes_it_may_update` | Exit 1, 1 failed; loaded all three keys |
| M2: remove transcript-status predicate, keep pending predicate | Same command as M1 | Exit 1, 1 failed; loaded `found`, `waiting` |
| M3: build `by_key` for every source kind | `uv run pytest tests/test_podcast_collection.py::test_website_check_loads_no_full_rows` | Exit 1, 1 failed; loaded `pending` |
| M4: remove the `IS NULL` branch | `uv run pytest tests/test_podcast_collection.py::test_feed_upgraded_to_podcast_resolves_pending_item` | Exit 1, 1 failed; status stayed `None`, not `waiting` |
| M5: use `bool(by_key)` for possible gap | `uv run pytest tests/test_collection.py` | Exit 1, 3 failed, 31 passed; all failures listed below |
| M6: build `by_key` before feed-to-podcast upgrade | Same command as M4 | Exit 1, 1 failed; kind upgraded but item status stayed `None` |

Every M5 failure:

- `test_possible_gap_only_with_prior_items_and_no_match`
- `test_linkless_new_entry_can_signal_gap`
- `test_empty_feed_after_recorded_entries_is_success_with_possible_gap`

After restoring M6, `UV_OFFLINE=1 uv run pytest tests/test_podcast_collection.py
tests/test_collection.py`: **43 passed**. Existing backend tests were not edited.

## Remaining verification

Groups 2–4 have not yet run.

Docker build, `scripts/docker-smoke.sh`, and the live before/after comparison
from the design's Migration Plan: **not performed**. Claude Code runs these
at review, per task 4.1. No requests were sent to port 8800.
