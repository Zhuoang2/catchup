# Test report: improve-context-pass-speed-and-progress

## Implementation by Droid

Baseline: `985d4ed`. Backend checks use `uv run --offline pytest` in `backend/`.
All network-dependent tests use offline stubs. No packages were added or upgraded.
Docker and browser/benchmark review checks are reserved for Claude Code.

### Test-first evidence

| Tasks | Before implementation | After implementation |
| --- | --- | --- |
| 1.1–1.2 | 5 failed, 2 passed: missing `sources_total` column, three missing `stage_seconds` keys, live source count 3 instead of 2. Before-thread and X-count guards passed as planned. | Full backend: 1041 passed (32.44 s). |

### Named mutations

Each mutation was applied alone, tested, and edited back. After every restore,
`git diff -- <file>` exactly matched its pre-mutation diff.
Exit 1 below means the named assertion killed the mutation, not a collection error.

| Mutation | Test (`test_` prefix omitted) | Observed result |
| --- | --- | --- |
| D1 | stage_durations_are_saved_for_each_stage | Killed, 1 failed: missing context duration. |
| D2 | failed_run_keeps_durations_of_finished_stages | Killed, 1 failed: empty duration dict after deferring saves until successful save. |
| N1 | sources_total_stays_fixed_when_a_source_is_added_during_the_run | Killed, 1 failed: 3 instead of 2. |
| N2 | source_added_before_the_run_thread_starts_is_counted | Killed, 1 failed: 1 instead of 2. |
| M1 | run_progress_migration_fills_sources_total_and_downgrades | Killed, 1 failed: historical count 0 instead of 2. |
