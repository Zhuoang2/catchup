# Fix new-source check outcome: implementation checks

2026-10-16, branch `fix-new-source-check-outcome`. Commands ran from the repository root unless a directory is specified.

| Check | Actual result |
| --- | --- |
| `cd backend && uv run pytest -q --tb=line tests/test_core_flow.py tests/test_digest_runner.py` before implementation | **9 failed, 27 passed**. The failures reproduced the first-run, carry-over, skipped Short, stale count, and before-summary outcome mismatches. The waiting-only case passed because the old collector already returned `no_new_items`. |
| `cd backend && uv run pytest -q tests/test_core_flow.py tests/test_digest_runner.py` after implementation | **36 passed**. |
| `cd backend && uv run pytest` | **370 passed**. |
| `cd backend && uv run pytest --cov=catchup --cov-report=term` | **370 passed**, **96%** overall statement coverage (1,887 statements, 78 missed). `digest/runner.py`: **99%** (266 statements, 3 missed), unchanged from the pre-change full-suite baseline of **99%** (258 statements, 3 missed; 362 tests). |
| `cd frontend && npm test -- --run` | **164 passed** in **13 files**. |
| `cd frontend && npm run build` | Passed TypeScript and Vite production build (**41 modules**). |
| `openspec validate fix-new-source-check-outcome --strict` | Valid. |
| `docker build -t catchup-fix-new-source-check-outcome .` | Passed locally with Docker **29.8.0**. Image not pushed. |

The first red run also exposed a test typo (`SourceCheck` treated as a dictionary); correcting the assertion yielded nine behavior-only failures. After the implementation, the first-summary test failed because two summary threads recorded the same observation; a lock made the observation deterministic, and all checks passed. The isolated tests used stubbed collection and models, with no live feed, provider, key, or real sleeps. `npm ci` installed locked frontend dependencies before the frontend checks (0 vulnerabilities).

**Manual check not performed:** add a public feed on a local instance, run a digest, and see “New items” for that source beside its items in the digest.

## Review fixes, round 1

2026-10-16, branch `fix-new-source-check-outcome`.

| Check | Actual result |
| --- | --- |
| `cd backend && uv run pytest -q --tb=short tests/test_digest_runner.py -k deleted_source_` before the deletion fix | **2 failed, 1 passed, 34 deselected**. The cases with and without a pending item failed with `StaleDataError` and `AttributeError`, respectively. |
| Same focused command after the fix | **3 passed, 34 deselected**. Both deleted sources were skipped; the surviving source's outcome and digest item were correct. |
| `cd backend && uv run pytest -q --tb=short tests/test_digest_runner.py::test_held_podcast_episode_is_waiting_not_new` with finalization temporarily removed | **1 failed** on `new_items` vs `no_new_items`. After restoring finalization: **1 passed**. The temporary production change was removed. |
| `cd backend && uv run pytest -q tests/test_digest_runner.py tests/test_core_flow.py` | **38 passed**. |
| `cd backend && uv run pytest --cov=catchup --cov-report=term` | **372 passed**, **96%** overall statement coverage (**1,888 statements, 77 missed**); `digest/runner.py`: **99%** (**267 statements, 3 missed**). |

The original run above recorded 78 missed statements in its worktree; this fresh run confirms the review's count of 77. The one-statement difference is in `main.py` (2 missed then, 1 missed here). The earlier result remains as the historical result of that command, not a claim about this round.
