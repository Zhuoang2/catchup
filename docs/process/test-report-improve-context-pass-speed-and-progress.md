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
| 4.1 | First run: 14 failed, 2 passed: 7 missing reachable_reads cases, old initial total 6, cap total 8, deleted-item total 2, four changed expectations. Commit-between-reads and the unchanged refused-page guard passed. | Resumed: approved new limit-cut test passed against existing 4.2 code (1 passed in 1.69 s); all 4.1 tests: 17 passed, 39 deselected. |
| 4.2 | Implemented the sequential progress tracker; first run stopped at T4's verification gap. | Resumed: context gather 56 passed (4.44 s); full backend 1064 passed (26.26 s). T4 and T7 killed on retry. |
| 5.1–5.2 | 2 failed, 3 passed (4.64 s): measured peak 1 instead of 4; README phrase missing; spacing, budget and unexpected-error guards passed. | Initial pool check: 1 expected order-dependent failure, 137 passed. After the allowed one-worker pin: 139 passed across context, runner and README files (10.50 s); full backend 1068 passed (27.71 s). |
| 6.1–6.2 | Not started after the stop condition. | Frontend untouched. |
| 7.1–7.3 | Final checks not reached. Evidence and this stop report were recorded without claiming completion. | See command status below. |

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
| T1 | total_starts_at_what_the_limit_can_read | Killed, 1 failed: initial total 6 rather than 3. |
| T2 | reachable_reads (all 7 cases ran) | Killed, 2 failed (a and e), 5 passed. |
| T3 | links_after_the_cap_leave_the_total | Killed, 1 failed: final (8, 6) rather than (6, 6). |
| T4 | Four changed tests plus read_cut_by_the_limit_leaves_the_total_after_the_next_item | First run: unexpected survivor, 5 passed (exit 0). After ae04f15: killed, 1 failed, 5 passed, 50 deselected (1.82 s, exit 1). The four changed tests still passed; the new test failed with (2, 1). |
| T5 | reachable_reads (all 7 cases ran) | Killed, 1 failed (d), 6 passed. |
| T6 | reachable_reads (all 7 cases ran) | Killed, 1 failed (e), 6 passed. |
| T7 | reads_of_a_deleted_item_leave_the_total | First attempt invalid (indentation error, exit 2), not a kill. Resumed with valid Python: killed, 1 failed (1.44 s, exit 1), total 2 rather than done 1. Restored with matching diff. |
| W1 | four_items_are_read_at_the_same_time | Killed, 1 failed (3.30 s): peak 1 instead of 4. |
| W2 | four_items_are_read_at_the_same_time | Killed, 1 failed (1.69 s): peak 8 instead of 4. |
| W3 | unexpected_item_error_fails_the_run | Killed, 1 failed (1.57 s): run succeeded after swallowing task exceptions. |
| R1 (pool) | two_items_on_one_site_share_robots_and_spacing | Killed, 1 failed (2.38 s): robots.txt requested twice. |
| Doc | readme_documents_public_context_limits_and_robots | Killed, 1 failed (0.02 s): concurrency phrase missing. |
| F1 | shows linked-page progress after a source is deleted during the checks | Not run: group 6 not reached. |

### Stop condition and diagnosis

T4 was the isolated edit from `except BudgetExhausted: progress.drop(item_id)`
to `except BudgetExhausted: pass`. The reproduction command, in `backend/`, was:

```sh
uv run --offline pytest tests/test_context_gather.py -k "refused_links_count or failed_request_on_last or comment_budget_cutoff or comment_feed_budget_cutoff" -q --tb=short
```

Actual output: `5 passed, 50 deselected in 1.69s`, exit 0, rather than an assertion failure.
The mutation batch continued through T5–T7 before its results were inspected.
This was a workflow mistake: the batch should have stopped at the unexpected survivor.
No further implementation followed. Every mutated file was edited back and its diff
compared to the pre-mutation diff, including after T7's invalid edit.

Ranked hypotheses (diagnosing-bugs skill):

1. The specified tests cannot observe stale in-progress reads because they assert
   persisted totals and `start()` intentionally does not commit.
2. The exhausted budget makes all queued network reads unreachable, masking their
   presence until another progress operation commits.
3. The mutation did not reach the intended handler.

Control-flow inspection supports 1 and 2: the last successful `finish()` already
commits `total == done` when the remaining budget cannot afford the next read.
The next `start()` changes memory only. Without the drop, exhaustion causes no
new progress commit in these fixtures, so the final API still returns the earlier
correct pair. Inspection of the isolated edit rules out 3. This is a verification
gap, not evidence that dropping reads is unnecessary. A later operation (another
item or saved replies) could expose the stale in-progress entry. No extra tests
or plan changes were improvised.

Groups 1–3 are committed separately (`7060a4c`, `8aa1c41`, `ef3af2b`).
At the first stop, group 4 remained uncommitted and task 4.2 unchecked.

Claude Code confirmed the first hypothesis and added the next-item commit test
to tasks.md in `ae04f15`. Droid resumed on the user's instruction, wrote that
test, and observed it pass on 4.2 code. Under T4 it failed with `(2, 1)`, while
the original four changed tests passed, exactly as the amended plan required.
T7 was retried with a valid edit replacing the deleted-item drop calls with
indented `pass` statements; its named test failed with total 2 and done 1.
Both mutations were inspected individually and restored with matching diffs.
Group 4 is complete; the historical stop record above is retained.

### Existing tests pinned to one worker in group 5.2

- `test_budget_leaves_unreached_items_ungathered_and_retries_do_not_refetch`:
  the pool returned `["gathered", "none"]` rather than `["gathered", None]`.
  The test requires item 2 not to start before the last budget unit is taken.
  Its only change was `monkeypatch.setattr("catchup.context.gather.CONTEXT_WORKERS", 1)`.
- `test_second_item_keeps_partial_context_in_successful_digest` passed unchanged
  in group 5; it was not pinned preemptively.
- The new deleted-item and next-item T4 tests already explicitly use one worker
  as required by task 4.1, not as modifications of existing tests in group 5.2.

### Task 7.1 command status

| Command | Real result |
| --- | --- |
| `uv run --offline pytest` | Task 7.1 not reached. Latest full-suite invocation was `uv run --offline pytest -q`: `1063 passed in 33.39s`, exit 0, before group 4 mutations. |
| Five-run concurrency loop from 7.1 | Not run after stop. |
| `npm test -- --run` in frontend | Not run; group 6 and its offline install not reached. |
| `npm run build` in frontend | Not run. |
| `DO_NOT_TRACK=1 openspec validate improve-context-pass-speed-and-progress --strict` | Not run after stop. |
| `git diff --check` | Exit 0, no output, after mutation restoration. |

No Docker command, port 8800 operation, push, merge, tag, or PR action was performed.
