# Test report: finish-fix-round-cleanup

Date: 2026-11-17. Implementation starts at `dd1ec68`.

## Environment and method

- Backend: Python 3.12.13, SQLAlchemy 2.1.3. All backend commands below run
  from `backend/`, with `UV_OFFLINE=1 uv run`; the locked environment was
  installed from the local cache, without adding dependencies.
- Frontend: every command runs from `frontend/` after
  `export PATH="$HOME/.nvm/versions/node/v22.17.1/bin:$PATH"`.
  `node --version`: **v22.17.1**.
  `npm ci --offline --no-audit --no-fund`: **exit 0, 124 packages added**.
  No packages downloaded; `package.json` and `package-lock.json` unchanged.
  Frontend test/build commands also set `npm_config_offline=true`.
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

## Group 2: summary and context pins

Each new test passed on unchanged production code before its isolated mutation.
Each mutation then failed the named test (exit 1, **1 failed**). Source changes
were reversed immediately; no production change is retained in this group.

| Mutation | New test and command (`UV_OFFLINE=1` prefix) | Observed failure |
| --- | --- | --- |
| Y1: remove both caption-found summary-clearing lines in `runner.py` | `uv run pytest tests/test_caption_pass.py::test_found_caption_replaces_earlier_summary` | No model messages contained the new transcript |
| U1: preserve prior `used` via `part.used or part.ref in result.used` | `uv run pytest tests/test_digest_runner.py::test_new_summary_resets_used_context_rows` | `L1.used` stayed `True` |
| P1: remove both text-conversion summary-clearing lines in `collection.py` | `uv run pytest tests/test_podcast_collection.py::test_waiting_episode_that_becomes_text_drops_earlier_summary` | Old summary remained after status became `text` |

Y1 and U1 each passed again individually after restoration (**1 passed** each).
After P1 restoration, `UV_OFFLINE=1 uv run pytest`: **967 passed**, including
all three new pins and all 961 original backend tests.

## Group 3: one poll helper

`npx vitest run src/pages/Home.test.tsx`:

| State | Exit | Tests |
| --- | --- | --- |
| Unchanged baseline | 0 | 99 passed |
| F1 before: remove all 19 poll time-advance lines | 1 | 12 failed, 87 passed |
| D3 helper and 19 call sites implemented | 0 | 99 passed |
| F1 after: remove only the helper's time-advance line | 1 | 12 failed, 87 passed |

Both mutations were run alone. Both restorations matched the pre-mutation file
exactly. The before/after failure-name sets were compared and are identical:

| Failing test in `src/pages/Home.test.tsx` | F1 before | F1 after |
| --- | --- | --- |
| `keeps a fetched edition when the next run ends no_new_content` | Failed | Failed |
| `keeps a fetched edition when the next run ends succeeded` | Failed | Failed |
| `hides an older digest fetch error after an overlapping run shows a newer edition` | Failed | Failed |
| `hides an older fetch error when the newer digest resolves in the same tick` | Failed | Failed |
| `keeps the higher digest error when an older pending fetch also fails` | Failed | Failed |
| `polls from summarizing to success with a persistent status region using fake timers` | Failed | Failed |
| `announces a polled run failure only through the persistent status region` | Failed | Failed |
| `announces 16 saved items (14 summarized, 2 in Creator updates)` | Failed | Failed |
| `announces 3 saved items (3 summarized, 0 in Creator updates)` | Failed | Failed |
| `announces 2 saved items (0 summarized, 2 in Creator updates)` | Failed | Failed |
| `keeps a startup latest-digest error visible through successful progress polls` | Failed | Failed |
| `uses action-specific alerts when starting or checking a run fails` | Failed | Failed |

After restoration:

- Content search for `advanceTimersByTimeAsync` (the `grep -c` check's
  equivalent): **1**, at line 18 inside `advancePoll`; none outside it.
- `npm test -- --run`: **307 passed in 14 files**, including the 99 Home tests.
- `npm run build`: **exit 0** (`tsc --noEmit` and Vite; 40 modules transformed).
- Frontend diff contains only the helper and the 19 poll-step replacements.

## Group 4: final checks

All final commands passed on the restored implementation:

| Directory | Command | Actual result |
| --- | --- | --- |
| `backend/` | `UV_OFFLINE=1 uv run pytest` | Exit 0, **967 passed in 32.98s** |
| `frontend/` | `npm_config_offline=true npm test -- --run` | Exit 0, **307 passed in 14 files**, 7.49s |
| `frontend/` | `npm_config_offline=true npm run build` | Exit 0, TypeScript check and Vite build passed; **40 modules** transformed |
| Repository root | `DO_NOT_TRACK=1 openspec validate finish-fix-round-cleanup --strict` | Exit 0, change valid; `skip_specs` INFO accepts zero deltas |

The final suites contain six new backend tests (961 original + 6 = 967), no
new frontend tests, and no changes to existing test assertions. All nine named
backend mutations were killed, with each mutation restored before the next.
F1's two isolated runs failed the same 12 tests. The only red results were the
planned initial load checks and mutation checks; there are no unresolved test
failures. No plan adjustment was needed.

## Review-only checks not performed

Docker build, `scripts/docker-smoke.sh`, and the live before/after comparison
from the design's Migration Plan: **not performed**. Claude Code runs these
at review, per task 4.1. The live comparison still needs fresh main/branch
instances, a stub model, the same public podcast and website feeds, and two
runs on each to compare counters and stored items after delivery.

No Docker images, containers, or volumes were removed or pruned. No requests
were sent to port 8800. No pushes, tags, releases, pull requests, or other
external writes were made.
