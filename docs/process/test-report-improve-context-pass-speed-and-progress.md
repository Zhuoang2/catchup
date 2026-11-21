# Test report: improve-context-pass-speed-and-progress

## Implementation by Droid

Baseline: `985d4ed`. Backend checks use `uv run --offline pytest` in `backend/`.
All network-dependent tests use offline stubs. No packages were added or upgraded.
Docker and browser/benchmark review checks are reserved for Claude Code.

### Test-first evidence

| Tasks | Before implementation | After implementation |
| --- | --- | --- |
| 1.1–1.2 | 5 failed, 2 passed: missing `sources_total` column, three missing `stage_seconds` keys, live source count 3 instead of 2. Before-thread and X-count guards passed as planned. | Full backend: 1041 passed (32.44 s). |
| 2.1–2.2 | 2 failed (feed and X both observed `no_new_items`); 3 guards passed. | Full backend: 1046 passed (35.71 s). |
| 3.1–3.2 | 4 failed: global host lock blocked other host, missing origin/verdict, robots requested twice. Same-host and budget guards passed as allowed. | Full backend: 1052 passed (33.31 s), including all three safety files and context gather. |

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
| H1 | feed_with_held_items_shows_new_items_when_checked | Killed, 1 failed: no_new_items observed. |
| H2 | x_account_with_held_posts_shows_new_items_when_checked | Killed, 1 failed: no_new_items observed. |
| H3 | waiting_podcast_episode_keeps_no_new_items_when_checked | Killed, 1 failed: waiting episode upgraded to new_items. |
| H4 | failed_check_with_held_items_stays_failed | Killed, 1 failed: failed check upgraded to new_items. |
| S1 | other_hosts_do_not_wait_while_one_host_sleeps | Killed, 1 failed: other-host thread still alive. |
| S2 | same_host_waits_are_spaced_across_threads | Killed, 1 failed: interval below 0.19 s. |
| R1 | robots_is_read_once_when_two_threads_ask_at_once | Killed, 1 failed: 2 robots requests. |
| R2 | verdict_never_requests_and_reads_stored_rules | Killed, 1 failed: first verdict False rather than None after making a request. |
| B1 | budget_units_are_taken_once_per_request_across_threads | Survived, 1 passed, as anticipated. The check/decrement critical section was inspected; race evidence is design probe P3, not a deterministic regression-test kill. |
