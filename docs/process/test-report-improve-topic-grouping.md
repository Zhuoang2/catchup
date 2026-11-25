# Test report: improve-topic-grouping (#32)

## Implementation by Factory Droid

Date: 2026-11-25. Model: GPT-6.1 Sol. Starting commit: `42561a0`.

Implemented task groups 1–3 with the `openspec-apply-change` and `tdd` skills.
The limit is prompt guidance only: single and batch grouping use their own
item counts, merging uses the total item count, and merge entries carry item
counts. Validation, fallback, batching, token budgets, and saved-topic behavior
are unchanged. Existing tests were not edited; 25 cases were appended.

Implementation commits:

- Group 1: `508bd3a`, Improve single-call topic grouping guidance (#32).
- Group 2: `21cd538`, Apply topic grouping guidance to batch merges (#32).
- Group 3: the documentation/checks commit containing this report.

### Environment and offline boundaries

All backend commands ran in `backend/` with `uv run --offline`.
Its first run created `.venv` and installed 62 locked packages from the local
cache; no dependency was added, removed, or upgraded.
The existing autouse fixture blocks unmocked DNS and socket connections.
The new tests use only the existing `FakeModel` classes and runner fixtures.
No real model, network, or real API key was used.

Before each frontend/extension command:

```sh
export PATH="$HOME/.nvm/versions/node/v22.17.1/bin:$PATH"
```

`node --version` printed `v22.17.1` in both directories.
`npm ci --offline --no-audit --no-fund` exited 0 in both:

| Directory | Actual output |
| --- | --- |
| `frontend/` | `added 124 packages in 1s` |
| `extension/` | `added 120 packages in 1s` |

Both installs emitted the existing `whatwg-encoding@3.1.1` deprecation warning.
No manifest or lockfile changed.

### Test-first evidence

Test aliases below are also used in the mutation table. S tests are in
`backend/tests/test_digest_stages.py`; R tests are in
`backend/tests/test_digest_runner.py`.

| Alias | New test | Observed before its implementation | Mutations killed |
| --- | --- | --- | --- |
| S-limit | `test_topic_limit_grows_with_the_item_count` (16 cases) | All 16 failed with `ImportError: cannot import name 'topic_limit'` | L1, L2, L3 |
| S-prompt | `test_grouping_prompt_asks_for_broad_topics_within_the_limit` | Failed with `TypeError: group_messages() takes 2 positional arguments but 3 were given` | P1, P2, P4 |
| S-seven | `test_seven_items_ask_for_four_topics_and_keep_the_six_answered` | Failed because `use at most 4 topics` was absent | L3, P1, P3, K1, K2 |
| R-limit | `test_run_asks_grouping_for_the_topic_limit_of_its_items` (3 cases) | All 3 failed because their required limit phrases were absent | L2, L3, P2, P3 |
| R-keep | `test_run_saves_more_topics_than_the_limit_as_answered` | Passed, as required, guarding behavior already present | K1, K2 |
| S-merge | `test_merge_prompt_asks_for_broad_final_topics_within_the_limit` | Failed with `TypeError: merge_messages() takes 2 positional arguments but 3 were given` | B3 |
| S-batch | `test_batched_grouping_limits_follow_batch_and_total_counts` | Batch-size and 3/3/2 limit assertions passed, then failed because `use at most 5 final topics` was absent | B1, B2, P3 again |
| S-keep | `test_batched_grouping_keeps_more_final_topics_than_the_limit` | Passed after group 1, as required, guarding behavior already present | K1m, K2m |

The pre-change group 1 command, run before any production edit:

```sh
uv run --offline pytest tests/test_digest_stages.py::test_topic_limit_grows_with_the_item_count tests/test_digest_stages.py::test_grouping_prompt_asks_for_broad_topics_within_the_limit tests/test_digest_stages.py::test_seven_items_ask_for_four_topics_and_keep_the_six_answered tests/test_digest_runner.py::test_run_asks_grouping_for_the_topic_limit_of_its_items tests/test_digest_runner.py::test_run_saves_more_topics_than_the_limit_as_answered -q
```

Actual results:

- Before implementation: exit 1, `21 failed, 1 passed in 3.71s`.
- After implementation: exit 0, `22 passed in 2.36s`.
- After all group 1 mutations were restored: exit 0, `22 passed in 2.04s`.

The group 2 command, first run on the committed group 1 code:

```sh
uv run --offline pytest tests/test_digest_stages.py::test_merge_prompt_asks_for_broad_final_topics_within_the_limit tests/test_digest_stages.py::test_batched_grouping_limits_follow_batch_and_total_counts tests/test_digest_stages.py::test_batched_grouping_keeps_more_final_topics_than_the_limit -q --tb=short
```

Actual pre-change result: exit 1, `2 failed, 1 passed in 0.52s`.
The same selection without `--tb=short` passed after implementation:
`3 passed in 0.36s`, exit 0. After restoring its mutations it again passed:
`3 passed in 3.29s`, exit 0.

### Isolated named mutations

Each row was one isolated run, using:

```sh
uv run --offline pytest <the test node IDs named in the row> -q --tb=short
```

Before every mutation, `git diff --no-ext-diff --binary` was saved in memory.
Each mutation was applied alone, then reversed by editing the file back.
After each reversal, that same `git diff` output exactly matched the saved
pre-mutation diff. No reset, checkout, restore, or stash command was used.
All 15 runs exited 1 for the expected test failures; none survived.

| Mutation | Change applied alone | Tests that actually failed | Actual pytest result |
| --- | --- | --- | --- |
| L1 | Remove cap of 12 | S-limit at counts 200 and 10,000 | `2 failed, 14 passed in 2.90s` |
| L2 | Remove bound by item count | S-limit at count 1; R-limit at count 1 | `2 failed, 17 passed in 2.46s` |
| L3 | Floor with `math.isqrt(2 * count)` | S-limit at counts 3, 4, 5, 7, 9, 11, 15, 30, 60, 61; S-seven; R-limit at counts 7 and 30 | `13 failed, 7 passed in 2.25s` |
| P1 | Remove cross-source phrase | S-prompt; S-seven | `2 failed in 0.40s` |
| P2 | Use general size text for limit 1 | S-prompt; R-limit at count 1 | `2 failed, 2 passed in 2.14s` |
| P3 | Pass 12 to `group_messages` | S-seven; all three R-limit cases | `4 failed in 2.32s` |
| P4 | Remove overview non-repetition clause | S-prompt | `1 failed in 0.44s` |
| K1 | Fold excess single-call topics into Other | S-seven; R-keep, both on topic preservation | `2 failed in 2.26s` |
| K2 | Make the specified extra Check call after excess single-call topics | S-seven with `StopIteration`; R-keep with 2 non-summary calls instead of 1 | `2 failed in 2.44s` |
| B1 | Derive merge limit from batch-topic count | S-batch on merge limit | `1 failed in 0.54s` |
| B2 | Omit merge input item counts | S-batch on merge payload equality | `1 failed in 0.44s` |
| B3 | Remove merge item-count instruction | S-merge | `1 failed in 0.46s` |
| P3 again | Pass 12 to `group_messages` after group 2 | S-batch on the first batch limit | `1 failed in 0.45s` |
| K1m | Fold excess validated merge topics into Other | S-keep on final topic preservation | `1 failed in 0.46s` |
| K2m | Make the specified extra Check call after excess merge topics | S-keep with `StopIteration` | `1 failed in 0.49s` |

### Full verification commands and real results

All commands below exited 0. Test totals include the existing suites, with
only the 25 new backend cases added by this change.

| Directory | Command | Actual result |
| --- | --- | --- |
| `backend/` (initial existing stage tests) | `uv run --offline pytest tests/test_digest_stages.py -q` | `53 passed in 0.67s` |
| `backend/` (group 1) | `uv run --offline pytest` | `1291 passed, 2 warnings in 31.09s` |
| `backend/` (group 2) | `uv run --offline pytest` | `1294 passed, 2 warnings in 38.00s` |
| `backend/` (group 3 final) | `uv run --offline pytest` | `1294 passed, 2 warnings in 42.19s` |
| `frontend/` | `npm test -- --run` | `Test Files  14 passed (14)`; `Tests  336 passed (336)`; `Duration  7.29s` |
| `frontend/` | `npm run build` | `tsc --noEmit && vite build`; `40 modules transformed`; `built in 335ms` |
| `extension/` | `npm test -- --run` | `Test Files  7 passed (7)`; `Tests  169 passed (169)`; `Duration  4.45s` |
| `extension/` | `npm run build` | `tsc --noEmit && vite build && node scripts/check-build.mjs`; `10 modules transformed`; `built in 290ms` |
| Repository root | `DO_NOT_TRACK=1 openspec validate improve-topic-grouping --strict` | `Change 'improve-topic-grouping' is valid` |
| Repository root | `git diff --check` | No output |

The backend's two warnings came from unchanged tests:
`test_usage_of_the_wrong_shape_is_not_counted[seven-3-expected0]` and
`test_usage_of_the_wrong_shape_is_not_counted[seven-three-expected2]` in
`test_anthropic_client.py`, intentionally giving Pydantic a non-integer usage
value. No unrelated test failed, so no isolated failure rerun was needed.

### Not performed and deviations

- Docker smoke and the live check with a recording stub model: not performed
  by Droid, as instructed. Claude Code runs these at review.
- Real-model grouping quality: not tested by Droid. Under design D7/Q1, the
  user checks their next 2–3 real digests after merge.
- No Docker command ran; port 8800 and running containers were not touched.
- No plan deviations. Every stated pre-change failure/pass and every named
  mutation matched the approved plan. Protected planning/process files were
  not edited. No temporary helper files were created.

## Review by Claude Code

Reviewed in worktree `review32` on the branch. Droid's run started at the plan commit `42561a0` and ended at `cf0c6e8`.

### Checks

| Check | Result |
| --- | --- |
| Backend `uv run --offline pytest` | 1294 passed on `cf0c6e8`; 1295 with Claude's review test |
| Frontend `npm test -- --run`, `npm run build` | 336 passed; build passed |
| Extension `npm test -- --run`, `npm run build` | 169 passed; build passed |
| `DO_NOT_TRACK=1 openspec validate improve-topic-grouping --strict` | valid |
| `git diff --check 42561a0..HEAD` | clean |
| `scripts/docker-smoke.sh catchup:fix32-local` (built from `cf0c6e8`) | 12 of 12 |

### Live check

A scratch container from `catchup:fix32-local` ran on its own volume and port 8832, with a local OpenAI-compatible stub model on the host that recorded every request. Seven pages were saved through the extension API (two about Apple, two about AI, one each about AI rules, a library, and a recipe), and one run succeeded:

- the run made 8 model calls: 7 summaries and 1 grouping call, with no merge call;
- the grouping call's system text contained "use at most 4 topics" and the exact text of design D6, over 7 item refs;
- the stub answered 6 topics; the saved digest has those 6 topics in the model's order, with 2, 1, 1, 1, 1, and 1 items, and no further model call was made.

The container, its volume, and the stub were removed afterwards.

### Findings

- **`/code-review` (high) on `42561a0..cf0c6e8`:**
  - the Droid entry's heading in the AI usage log used a comma instead of the log's dash: fixed in Claude's review commit;
  - the merge input's key `items` could read as a list rather than a count: not changed, because design D3 and the tests name the key, and the merge text says what it holds.
- **Spec sub-agent** (independent, detached worktree): no behavior defect; every requirement and scenario is implemented, the text matches design D6 exactly for four languages and every limit, and all 15 named mutation runs failed their tests. Claude checked its findings against the code:
  - **Fixed by Claude (test only, D-023 class c):** the merge limit was tested at one value, and the 10-item fixture sits on a plateau of the formula (`topic_limit` is 5 for 9, 10, 11, and 12 items); the merge input's counts were tested only where each batch answered one topic. Mutations that hard-code "use at most 5 final topics", pass `topic_limit(len(items) - 1)`, or count the batch's items instead of the topic's passed the suite. The new test `test_merge_limit_and_counts_follow_the_items_of_each_topic` groups 13 items in batches of 5, 5, and 3, with a first batch that answers topics of 3 and 2 items; it expects the limit 6 and the counts 3, 2, 5, and 3, and also checks the merge text for a limit of 12. Each of the three mutations, applied alone, failed it, and the code was restored exactly.
  - **Recorded, not fixed (literal strings):** moving the size sentence after the title sentence, putting `items` before `overview` in the merge input, and a double space before the size sentence survive the tests; the code has none of them.
  - **Wording:** the "Mutations killed" column above lists only the tests each mutation was named for. K1 and K2 also fail the batched keep test, and L3 also fails the batch test.
  - **Plan wording:** the K1m and K2m rows of the task 2.2 table lost their indent in Claude's plan fix; restored.
- **Not checked here:** real-model grouping quality is the user's check on their next 2–3 real digests after the merge (design D7, Q1).
