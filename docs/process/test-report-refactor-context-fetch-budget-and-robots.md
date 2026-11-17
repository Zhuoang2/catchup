# Test report: refactor-context-fetch-budget-and-robots

Date: 2026-11-16. Issues: #90 and #60. Runner: Factory Droid, GPT-6.1 Sol.
Starting commit: `7d9c934`. Implementation and verification are in progress.

## Environment and commands

All pytest commands run from this worktree's `backend/`. No dependencies
are installed or changed. Commands reuse the existing Python environment
with these environment variables:

```sh
UV_PROJECT_ENVIRONMENT="<existing checkout>/backend/.venv"
UV_NO_SYNC=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src"
```

`PYTHONPATH` selects this worktree's source, not the environment's editable
installation. Syncing is disabled. HTTP/DNS routes in the new tests are mocked;
clocks and waits are virtual. The existing safe-fetch transport regression
includes a loopback-only socket test. No external source requests are made.

The plan's latest AI-log entry records Claude Code's fresh-agent preflight
and library probes before this run.

## Test-first results

Commands below use `uv run pytest`, with the listed selection and
`--tb=short -q`.

| Stage | Selection | Actual result |
| --- | --- | --- |
| Group 1 baseline | `tests/test_safe_fetch.py` | 62 passed in 2.51s |
| 1.1 red | `tests/test_safe_fetch.py` | 6 failed, 62 passed in 1.85s. Missing `BudgetExhausted` import and unknown `allow` argument, as planned. |
| 1.2 green | `tests/test_safe_fetch.py` | 68 passed in 1.65s |
| 1.2 regression | Full suite | 946 passed in 33.49s |
| Group 1 restored | `tests/test_safe_fetch.py` | 68 passed in 5.99s |

## Mutations

Each mutation is applied alone, run, and restored in a `finally` block.
Source equality with the pre-mutation content is checked after each group.
Every mutation below exited 1. Selections use `uv run pytest` with
`--tb=short -q`; test names are node IDs in the stated test module.

### Group 1: `tests/test_safe_fetch.py`

| Mutation | Selection / failed tests | Actual result |
| --- | --- | --- |
| S1: `allow` only on hop 0 | `test_refused_redirect_target_is_not_requested` | 1 failed in 3.14s: no `FetchError` raised. |
| S2: take budget before `allow` | `test_refused_redirect_target_is_not_requested`; `test_allow_runs_after_the_address_check_and_before_budget_and_spacing` | 2 failed, 1 passed in 2.03s. Redirect budget `[3]`, expected `[4]`; allowed-address refusal budget `[0]`, expected `[1]`. Blocked-address case passes. |
| S3: do not extend deadline | `test_time_in_allow_does_not_count_against_the_deadline` | 1 failed in 2.35s: fetch timed out. |
| S4: raise plain `FetchError` | `test_budget_exhausted_is_a_fetch_error` | 1 failed in 2.14s: wrong exception type. |

## Review-only checks

- Docker build and `scripts/docker-smoke.sh`: not performed. Task 5.1 assigns
  these to Claude Code at review.
- Live comparison from design Migration Plan: not performed. Claude Code
  runs it at review on fresh instances, neither on port 8800.
- No pushes, tags, releases, PRs, Docker cleanup, or requests to port 8800.
