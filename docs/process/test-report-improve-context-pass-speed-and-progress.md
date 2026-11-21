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
| 6.1–6.2 | Replacement deleted-source test: 1 failed, 98 skipped, because the bar still read Sources checked: 2 of 3. | Node 22.17.1; offline npm ci installed 124 locked packages. Frontend: 314 passed in 14 files (5.14 s), including accessibility and unchanged status text; npm run build passed (40 modules, 273 ms). |
| 7.1 | First part stopped before final checks; no result was claimed. | Resumed: all named final checks passed; exact summaries below. |
| 7.2 | The first stop report retained incomplete checks explicitly. | Completed report with both attempts, every named mutation and the single existing-test worker pin. |
| 7.3 | Partial usage entry existed at the stop. | Replaced with one combined Droid entry covering the original prompt, stop, amendment, resumed prompt and completed results. |

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
| F1 | shows linked-page progress after a source is deleted during the checks | Killed, 1 failed, 98 skipped (1.48 s): Linked pages read: 7 of 20 progressbar missing. |

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
  At review, the spec sub-agent ran it 10 times without the pin: 5 runs failed that way,
  and 5 failed with `(1, 0, 1)` instead of `(1, 1, 0)`, because item 2 took the page unit
  and item 1 got none. Either way the pin is needed.
  The test requires item 2 not to start before the last budget unit is taken.
  Its only change was `monkeypatch.setattr("catchup.context.gather.CONTEXT_WORKERS", 1)`.
- `test_second_item_keeps_partial_context_in_successful_digest` passed unchanged
  in group 5; it was not pinned preemptively.
- The new deleted-item and next-item T4 tests already explicitly use one worker
  as required by task 4.1, not as modifications of existing tests in group 5.2.

### Task 7.1 command status

| Command | Real result |
| --- | --- |
| `uv run --offline pytest` in backend | `1068 passed in 29.75s`, exit 0. |
| Five-run concurrency loop below, in backend | All five passed, 240 tests per run, exit 0. |
| `npm test -- --run` in frontend | `Test Files 14 passed (14)`; `Tests 314 passed (314)`; duration 5.51 s, exit 0. |
| `npm run build` in frontend | TypeScript check passed; Vite 8.3.5: 40 modules transformed, built in 95 ms, exit 0. |
| `DO_NOT_TRACK=1 openspec validate improve-context-pass-speed-and-progress --strict` | `Change 'improve-context-pass-speed-and-progress' is valid`, exit 0. |
| `git diff --check` | Exit 0, no output. Also repeated after final evidence edits. |

The exact repeated command was:

```sh
for i in 1 2 3 4 5; do uv run --offline pytest tests/test_context_gather.py tests/test_host_spacing.py tests/test_context_robots.py tests/test_safe_fetch.py tests/test_digest_runner.py -q || break; done
```

Its five summary lines:

```text
240 passed in 12.08s
240 passed in 11.86s
240 passed in 12.13s
240 passed in 12.09s
240 passed in 12.42s
```

Both frontend command calls used:

```sh
export PATH="$HOME/.nvm/versions/node/v22.17.1/bin:$PATH"
```

Before frontend testing, `node --version` returned `v22.17.1` and
`npm ci --offline --no-audit --no-fund` installed 124 locked packages.
Its existing whatwg-encoding deprecation warning did not fail installation.
Neither package.json nor package-lock.json changed.

Tests added in this change are the migration, run-timing/count, held-item,
host/robots/budget concurrency, reachable-read/progress, and context-pool
cases named in tasks 1–5. Existing suites supplied the regression coverage.
The frontend test was replaced as task 6.1 required, retaining its accessibility
check. No unrelated existing assertions were changed.

Docker smoke, the benchmark comparison and the live browser check were not run,
as instructed; Claude Code performs them at review. Stage durations from real
user sources/model credentials remain for the user's next run after merge.

No Docker command, port 8800 operation, push, merge, tag, or PR action was performed.

## Fix round 1

Baseline: `cd96580` (group 8 planned in `0483756`, wording checked in `cd96580`).
Only group 8 was implemented. The earlier implementation and stop evidence above
is historical and unchanged. This round adds six test functions, 14 parametrized
cases, without changing existing tests, dependencies, or frontend code.

### Reproduction, diagnosis, and fixes

The first command below ran before any production edit, in `backend/`:

```sh
uv run --offline pytest tests/test_context_robots.py tests/test_context_gather.py tests/test_digest_runner.py -k "origin_refuses_addresses or reachable_reads_counts_refused or link_with_a_bad_port or odd_comment_feed_address or post_page_with_a_bad_port or source_deleted_while_held" -q --tb=short
```

Result: **12 failed, 2 passed, 166 deselected in 1.21 s**, exit 1.
The two passing cases were the existing invalid-port guards in `origin`.

| New test (`test_` prefix omitted) | Before fix | With fix |
| --- | --- | --- |
| origin_refuses_addresses_that_safe_fetch_refuses | 4 failed: relative/mailto TypeError, FTP KeyError, user-info accepted; 2 port cases passed. | All 6 passed. |
| reachable_reads_counts_refused_addresses_without_units | Both h and i raised during origin parsing. | Both passed: 2 and 3 reads respectively. |
| link_with_a_bad_port_is_skipped | Both runs failed rather than succeeded. | Both succeeded, docs requested, totals (2, 2). |
| odd_comment_feed_address_is_skipped | Both runs failed on a later progress commit after adding the bad feed. | Both succeeded, later docs requested, totals (3, 3). |
| post_page_with_a_bad_port_is_skipped | Run failed before fetching. | Succeeded with no requests, totals (1, 1). |
| source_deleted_while_held_items_are_counted | Run failed with StaleDataError. | no_new_content. |

Ranked hypotheses, stated before the fixes:

1. Progress estimation assumes valid HTTP URLs. Matching fetch validation and
   treating refused addresses as zero-cost reads should remove the address
   failures.
2. ORM attribute writes require rows deleted by another session to remain
   present. Explicit updates should make missing rows a no-op.
3. Request-budget handling causes these failures. Changing its accounting would
   then be necessary; this was less likely because several failures occurred
   before any request.

The baseline traces, green regressions and isolated O1/O4 reversions confirmed
1 and 2. The normal budget algorithm was not changed. Re-derived invariants:
estimation must count an address rejected before budget consumption without
querying robots or charging its origin; held-item display updates must tolerate
missing rows while preserving eligibility, check status guards and new_count.
`origin` now rejects non-HTTP, hostless and user-info addresses with ValueError,
like the fetch guard. `reachable_reads` computes origin before verdict, counts
ValueError refusals without cost, and continues. `_show_held_items` uses explicit
check/source updates with session synchronization disabled, so missing rows
match zero updates rather than raising at ORM flush.

The same new-test command after the fixes returned **14 passed, 166 deselected
in 0.98 s**, exit 0. The three affected files, via
`uv run --offline pytest tests/test_context_gather.py tests/test_context_robots.py tests/test_digest_runner.py -q`,
returned **180 passed in 10.84 s**. Task 8.2's full backend run returned
**1082 passed in 27.94 s**.

### Round mutations

Each mutation ran alone, its output was inspected before the next mutation, and
the file was edited back. After every reversal, `git diff -- <changed-file>`
exactly matched the captured pre-mutation diff. There were no collection errors,
unexpected survivors, or invalid attempts in this round.

| Mutation | Named tests and real result |
| --- | --- |
| O1, remove new origin validation | origin test, reachable case i, both odd-comment-feed cases: **7 failed, 2 passed in 0.95 s**, exit 1. Relative/mailto TypeError, FTP KeyError, user-info accepted; both digest runs failed. Killed. |
| O2, charge refused addresses 2 units | reachable h/i: **2 failed in 0.69 s**, exit 1; counts 1 vs 2 and 0 vs 3. Killed. |
| O3, omit refused addresses from count | reachable h/i: **2 failed in 0.80 s**, exit 1; counts 1 vs 2 and 0 vs 3. Killed. |
| O4, restore ORM attribute writes | deletion test: **1 failed in 0.65 s**, exit 1; failed rather than no_new_content, with StaleDataError. Killed. |

With all fixes restored, the deletion test plus these five unchanged group-2
guards returned **6 passed in 1.14 s**:

- `test_feed_with_held_items_shows_new_items_when_checked`
- `test_x_account_with_held_posts_shows_new_items_when_checked`
- `test_waiting_podcast_episode_keeps_no_new_items_when_checked`
- `test_source_without_pending_items_keeps_no_new_items`
- `test_failed_check_with_held_items_stays_failed`

### Task 7.1 commands repeated for task 8.3

Backend commands ran in `backend/`. Frontend commands ran in `frontend/` after
`export PATH="$HOME/.nvm/versions/node/v22.17.1/bin:$PATH"`.
`node --version` returned `v22.17.1`; the required
`npm ci --offline --no-audit --no-fund` installed 124 locked packages.
The existing whatwg-encoding deprecation warning was non-fatal.

| Command | Real result |
| --- | --- |
| `uv run --offline pytest` | **1082 passed in 32.27 s**, exit 0. |
| Five-run loop below | All five passed, **254 tests per run**, exit 0. |
| `npm test -- --run` | **314 tests passed in 14 files**, 6.52 s, exit 0. |
| `npm run build` | TypeScript passed; Vite transformed 40 modules, built in 420 ms, exit 0. |
| `DO_NOT_TRACK=1 openspec validate improve-context-pass-speed-and-progress --strict` | Change is valid, exit 0. |
| `git diff --check` | Exit 0, no output; repeated after evidence and checkbox edits. |

Exact repeated command:

```sh
for i in 1 2 3 4 5; do uv run --offline pytest tests/test_context_gather.py tests/test_host_spacing.py tests/test_context_robots.py tests/test_safe_fetch.py tests/test_digest_runner.py -q || break; done
```

All five summary lines:

```text
254 passed in 12.21s
254 passed in 12.51s
254 passed in 12.92s
254 passed in 12.70s
254 passed in 13.23s
```

Existing backend/frontend suites supplied regression coverage; this round wrote
only the six group-8 tests listed above. No existing group-1–7 assertion or worker
setting changed. No temporary helpers or diagnostic instrumentation were added.
Proposal, design, spec deltas, decision log and requirements log were untouched;
tasks.md has checkbox-only edits. Docker smoke, browser/live checks and benchmark
were not run, as instructed, and remain for Claude Code review. The extension
was out of scope and not run. No Docker, port 8800, container/volume operation,
push, merge, tag or PR action occurred.

## Review by Claude Code

Reviewed in worktree `review64` on the branch. Droid's runs started at `985d4ed` (groups 1–7) and `cd96580` (fix round 1).

### Checks on `fc86f12`

| Check | Result |
| --- | --- |
| Backend `uv run --offline pytest` | 1082 passed |
| Five concurrency files, five runs in a row | 254 passed each time |
| Frontend `npm test -- --run`, `npm run build` | 314 passed; build passed |
| Extension `npm test -- --run`, `npm run build` | 168 passed; build passed |
| `DO_NOT_TRACK=1 openspec validate improve-context-pass-speed-and-progress --strict` | valid |
| `git diff --check 985d4ed HEAD` | clean |
| `scripts/docker-smoke.sh catchup:fix64-local` (built from `54ac5be`, then from `fc86f12`) | 12 of 12 both times |

### Benchmark (offline, main `c67703a` against the branch at `54ac5be`)

Same invented workload through each tree's `gather_context`: 50 pending items, 178 related links on 85 hosts, a per-run limit of 60, and a latency of 0.3–2.0 s per host. A local threaded server answered, and DNS and the public-address check were patched in the benchmark script only (not committed).

| | main | branch |
| --- | --- | --- |
| Context pass | 75.6 s | 19.2 s |
| End of the pass, read / total | 32 / 178 | 31 / 31 |
| Total during the pass | 178 throughout | 32–33 |
| Requests (robots.txt + pages) | 60 (28 + 32) | 60 (29 + 31) |
| Requests in flight at most | 1 | 4 |
| Shortest gap between two requests to one host | 1.0 s | 1.003 s |
| Items gathered / marked `none` | 9 / 0 | 10 / 1 |

The one `none` item on the branch is a boundary item that started while the limit was nearly used up, as design.md Risks accepts.

### Browser check

A scratch container from `catchup:fix64-local` ran on its own volume and port 8864. After startup, Claude wrote an active run into its database: status `collecting`, `sources_total` 3, two source checks, and linked pages 7 of 20. The run bar in the browser pane read "Linked pages read: 7 of 20". The container and volume were removed afterwards.

### Findings

- **`/code-review` (high) on `985d4ed..54ac5be`:** one finding, confirmed (a). `reachable_reads` called `origin()` on every unstarted read. `origin()` raised on an address that `safe_fetch` refuses before it takes a unit (bad port, no host, non-HTTP with a port), so one such link, post page, or comment feed address failed the run. Claude reproduced it end to end on the branch (4 of 4 failed) and on `main` (4 of 4 succeeded). Fixed in fix round 1.
- **Spec sub-agent** (independent, detached worktree; it re-ran every named mutation, and all matched this report, with B1 surviving as planned):
  1. The same `origin()` defect, with one more case: a post page with a bad port. Confirmed; fixed in fix round 1.
  2. A source deleted after `_show_held_items` read its rows and before it committed failed the run with `StaleDataError`. Confirmed (a) by a probe that deletes the source on the first `select_pending` call; fixed in fix round 1.
  3. While several reads are in progress, each one counts as read in progress while its units are still in the budget, so the total can briefly exceed what the run can still read (for example "3 of 6" when at most 4 pages could be read). The pass still ends with read equal to total. Confirmed; D-036 accepts that the total moves while several reads are in progress, but the spec's "MUST" and design.md's "Exactness" line say more. Left to the user's decision.
  4. The pinned test's failure was described in one form only. Confirmed (c); corrected above.
  5. No test that cannot fail was found.
- **Fix round 1 (group 8):** planned by Claude Code with the tests tried in a scratch copy (12 failed on `54ac5be`). A fresh sub-agent that saw only the code and group 8 confirmed every red, green, and mutation, and found four wording errors, which `cd96580` fixed. Droid then implemented it in `fc86f12`. Claude re-ran O1–O4 in an export of the branch: O1 failed 7 tests, O2 and O3 failed cases h and i, and O4 failed the deletion test. The restored files matched the branch.
- **`/code-review` (high) on `cd96580..fc86f12`:** one nit, recorded and not fixed. An address on an X host is also refused before a unit is taken, but `origin()` accepts it, so it costs 2 units in the total until the next commit corrects it. Body links to X hosts are already dropped by `related_links`, so only a feed post page or comment feed on X is affected, and the pass still ends with read equal to total.

### Not fixed

- B1 survives as planned. The budget lock's race window is too small to kill by a test; probe P3 and review cover it.
- The X-host nit above.
