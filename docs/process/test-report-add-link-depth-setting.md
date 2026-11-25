# Test report: add-link-depth-setting (#54)

## Implementation by Factory Droid

Date: 2026-11-25. Model: GPT-6.1 Sol. Starting commit: `48619e4`.
Implemented task groups 1–5 in order using the approved test seams and test-first checks.
No Deep level, dependency changes, network/provider calls, or Docker commands.

### Environment

- Backend commands ran from `backend/` with `uv run --offline` (Python 3.12.13).
- Every frontend and extension command used `export PATH="$HOME/.nvm/versions/node/v22.17.1/bin:$PATH"` first.
- `npm ci --offline --no-audit --no-fund` succeeded in both projects: frontend `added 124 packages in 1s`; extension `added 120 packages in 1s`. Both emitted the existing `whatwg-encoding@3.1.1` deprecation warning.
- Lockfiles and dependency manifests are unchanged.
- Context tests use `public_dns` and `respx.mock(assert_all_mocked=True, assert_all_called=False)`; model calls use the existing fake model. The suite's autouse fixture blocks real DNS and socket connections.

### Test-first evidence

| Task | Command (backend unless noted) | Actual red result |
|---|---|---|
| 1.1 | `uv run --offline pytest tests/test_context_depth.py` | Exit 2: `ModuleNotFoundError: No module named 'catchup.context.depth'`, one collection error. |
| 1.1 | `uv run --offline pytest tests/test_context_links.py` | Exit 1: `1 failed, 11 passed in 0.21s`; limit 0 returned the first kept link. |
| 2.1 | `uv run --offline pytest tests/test_db.py --tb=short` | Exit 1: `6 failed, 8 passed in 2.96s`; missing column, migration file, and four new head expectations. |
| 2.1 | `uv run --offline pytest tests/test_settings_api.py -k 'preference or link_depth' --tb=short` | Exit 1: `10 failed, 23 deselected in 2.92s`; missing fields and invalid levels accepted. All changed/new preferences tests failed. |
| 3.1 | `uv run --offline pytest tests/test_context_gather.py -k "shallow or normal_follows or off_ or level_saved or run_without_saved" --tb=short -v` | Exit 1: `5 failed, 5 passed, 65 deselected in 3.81s`. The five failures were exactly the new Shallow/Off tests named by the plan. The lower-server, Normal-server, and no-settings tests already passed, plus two existing cutoff tests selected by the filter. |
| 3.1 | `uv run --offline pytest tests/test_context_gather.py::test_off_makes_no_context_request tests/test_context_gather.py::test_off_keeps_saved_replies --tb=short -q` | Exit 1: `2 failed in 5.22s`; request counts 5 and 2 instead of 0, after placing router-call assertions inside the active mock context. |
| 3.3 | `uv run --offline pytest tests/test_readme_context.py --tb=short` | Exit 1: `1 failed in 0.02s`; the new Linked pages phrase was absent. |
| 4.1 | `npm test -- --run src/pages/Settings.test.tsx --reporter=dot` (frontend) | Exit 1: `4 failed`, `65 passed (69)`; each new test could not find the Linked pages combobox. All existing Settings tests passed with the four authorized mock changes. |

Green results after implementation:

- Group 1: full backend `1283 passed, 2 warnings in 35.16s`.
- Group 2: full backend `1291 passed, 2 warnings in 34.36s`.
- Group 3: full backend `1299 passed, 2 warnings in 36.45s`; after the README edit, its focused check reported `1 passed in 0.23s`.
- Group 4: full frontend `14 passed (14)` files, `340 passed (340)` tests; build succeeded (`40 modules transformed`, `built in 174ms`).

### Test-to-requirement mapping

All backend names below are in `backend/tests/`. Frontend names are in `frontend/src/pages/Settings.test.tsx`.
The existing backend suite gained 30 cases; the existing frontend suite gained four tests. No existing run/context test was changed.

| New or changed test | Requirement/scenario | Mutations observed failing |
|---|---|---|
| `test_context_depth.py::test_link_depths` (new) | Only Off, Shallow, Normal are supported, design D1 | None named |
| `test_context_depth.py::test_context_limits` (new), rows `off`, `shallow`, `shallow_under_2`, `shallow_no_replies`, `normal`, `normal_server`, `unknown`, `empty` | Exact D1 table, server overrides, author-replies switch, unknown/empty fallback to Normal | L1, L2 (`off`); L3 (`shallow`, `shallow_no_replies`); L4 (`shallow_under_2`); L7 (`normal_server`) |
| `test_context_depth.py::test_link_depth_pages` (new), link limits 8, 5, 2, 1 | Settings reports the server's numbers, capped Shallow, singular counts | L6 (5-, 2-, 1-link rows) |
| `test_context_links.py::test_limit_zero_keeps_no_links` (new) | Off plans no related link, including nonpositive limits | L5 |
| `test_db.py::test_link_depth_migration_defaults_existing_settings_and_downgrades` (new) | No level saved: upgraded settings default to Normal; upgrade/downgrade preserve all previous columns and values | M1 |
| `test_db.py::test_migrations_live_inside_package` (changed) | New revision is packaged | None named |
| `test_db.py::test_existing_database_at_old_revision_is_unchanged`, `test_image_migration_from_0004_preserves_rows_and_downgrades`, `test_capture_migration_preserves_rows_and_removes_capture_sources_on_downgrade`, `test_migrate_copy_of_0006_database` (changed head assertions only) | Existing migrations now reach `0010_link_depth` | None named |
| `test_settings_api.py::test_link_depth_save_and_read` (new) | Save Off, reload, save Shallow, preserve level across partial updates | A2 |
| `test_settings_api.py::test_invalid_link_depth` (new), values `deep`, empty string, `OFF`, `none` | Invalid values return `invalid_link_depth` without writing the accompanying language | A1 (all four cases) |
| `test_settings_api.py::test_preferences_report_the_server_numbers` (new) | Server numbers: links 5/2, per-run requests 40 | L6 |
| `test_settings_api.py::test_preference_numbers_cannot_be_written` (new) | Read-only numbers ignore PUT input | None named |
| `test_settings_api.py::test_preference_save_and_read`, `test_partial_preference_updates_keep_other_values`, `test_image_preference_can_be_saved_without_changing_others` (changed answers only) | Normal defaults and existing Digest preferences remain intact | None named |
| `test_context_gather.py::test_shallow_reads_the_first_three_links` (new) | Shallow reads three links, with robots only for those origins; progress 3/3 | L3, G1 |
| `test_context_gather.py::test_shallow_follows_a_lower_server_setting` (new) | Shallow under a lower server setting | L4 |
| `test_context_gather.py::test_normal_follows_the_server_setting` (new) | Normal follows the server setting | L7 |
| `test_context_gather.py::test_off_makes_no_context_request` (new) | Off makes no request, including robots/post page; digest succeeds with one item, progress 0/0, context remains NULL | L1, G1, R2 |
| `test_context_gather.py::test_off_keeps_saved_replies` (new) | Off keeps both browser-saved replies as A1, no article/robots request, progress 1/1 | None named |
| `test_context_gather.py::test_item_left_by_off_is_read_later` (new) | Off run fails in the fake model; next Normal run gathers the still-pending item | L1 |
| `test_context_gather.py::test_level_saved_during_a_run_applies_to_the_next_run` (new) | Level changed during a run applies only to the next run | L1, R1 |
| `test_context_gather.py::test_run_without_saved_digest_settings_reads_at_normal` (new) | No level saved: absence of the entire AppSettings row still uses Normal | R3 |
| `test_context_gather.py::test_configured_two_link_limit_never_requests_third` (existing, unchanged) | Existing server override remains respected at Normal | L7 |
| `test_readme_context.py::test_readme_documents_public_context_limits_and_robots` (changed phrase list only) | README names Settings, levels, no-request Off, run-start snapshot; retains existing limit/robots explanations | None named |
| `shows the linked-pages choice with its numbers and cost note` (new) | Default choice in Digest, exact options, accessible cost description, accessibility audit | U3 |
| `names the server's own numbers` (new) | Server numbers (5 links, 40 requests), plus singular 1-page options | U2 |
| `saves Off with the other digest preferences` (new) | Save Off with other Digest/YouTube preferences and announce success | U1 |
| `loads a saved Off and keeps it when saving without changing it` (new) | Show and preserve saved Off, including PUT body | U1, U4 |
| Existing frontend preference GET mocks: default answer; `loads stored images off and preserves off when saving without changing it`; `explains authentication errors`; `shows the first-run key hint and saves preferences without exposing the key` | Updated API response shape, no behavioral assertion changes | None named |

Stored-state trace: only the context pass selects NULL context status; re-saving a capture resets it in `api/extension.py`. Off leaves an ordinary item NULL. A failed run leaves it pending, so Normal gathers it next time. Delivered items are excluded regardless of context status. Saved replies become gathered at Off and retain that context, as designed.

### Individual mutation results

Every row was applied alone, executed, then edited back. Before each mutation, the file's `git diff HEAD -- <path>` output was saved in memory; after restoration, the same command's output was compared byte-for-byte and matched. The new files were staged before their mutation baseline so the saved diff included them. No reset/checkout/restore/stash commands were used.

Depth abbreviations refer to `test_context_depth.py`; run abbreviations refer to `test_context_gather.py`; API abbreviations refer to `test_settings_api.py`.

| ID | Mutation | Tests that actually failed / actual summary |
|---|---|---|
| L1 | Off keeps the server request budget | Depth `test_context_limits[off]`: `1 failed, 12 passed`. Separately, run `test_off_makes_no_context_request`, `test_item_left_by_off_is_read_later`, `test_level_saved_during_a_run_applies_to_the_next_run`: `3 failed`. The first observed `none` instead of NULL; both next-run checks observed zero page calls instead of one. |
| L2 | Off keeps server author replies | Depth `test_context_limits[off]`: `1 failed, 12 passed`. Only the depth row is required: zero budget still prevents any run request. |
| L3 | Shallow uses the server link count | Depth `test_context_limits[shallow]`, `[shallow_no_replies]`: `2 failed, 11 passed`. Separately, run `test_shallow_reads_the_first_three_links`: `1 failed` (all five pages requested). |
| L4 | Shallow uses 3 without `min` | Depth `test_context_limits[shallow_under_2]`: `1 failed, 12 passed`. Separately, run `test_shallow_follows_a_lower_server_setting`: `1 failed` (third page requested). |
| L5 | Remove nonpositive-limit guard | `test_context_links.py::test_limit_zero_keeps_no_links`: `1 failed, 11 passed`. |
| L6 | Report fixed 8 Normal pages | Depth `test_link_depth_pages[5-expected1]`, `[2-expected2]`, `[1-expected3]`, API `test_preferences_report_the_server_numbers`: `4 failed, 10 passed`. |
| L7 | Normal uses fixed 8 links | Depth `test_context_limits[normal_server]`: `1 failed, 12 passed`. Separately, run `test_normal_follows_the_server_setting`, unchanged `test_configured_two_link_limit_never_requests_third`: `2 failed`. |
| G1 | Gather ignores the supplied level (resolves Normal) | Run `test_off_makes_no_context_request`, `test_shallow_reads_the_first_three_links`: `2 failed`. |
| R1 | Read level again after source checks, before context | Run `test_level_saved_during_a_run_applies_to_the_next_run`: `1 failed` (page requested in the first run). |
| R2 | Runner omits the level argument | Run `test_off_makes_no_context_request`: `1 failed` (five context requests). |
| R3 | Missing AppSettings defaults to Off | Run `test_run_without_saved_digest_settings_reads_at_normal`: `1 failed` (no page request). |
| A1 | Remove level validation, accept/store any value | API `test_invalid_link_depth[deep]`, `[]`, `[OFF]`, `[none]`: `4 failed` (200 instead of 422). |
| A2 | Read always returns Normal | API `test_link_depth_save_and_read`: `1 failed` (Normal instead of Off). |
| M1 | Migration server default is Shallow | `test_db.py::test_link_depth_migration_defaults_existing_settings_and_downgrades`: `1 failed`. |
| U1 | Save omits `link_depth` | Frontend `saves Off with the other digest preferences`, `loads a saved Off and keeps it when saving without changing it`: `2 failed`, `67 skipped`. |
| U2 | Normal label uses fixed 8 | Frontend `names the server's own numbers`: `1 failed`, `68 skipped`. |
| U3 | Remove description association | Frontend `shows the linked-pages choice with its numbers and cost note`: `1 failed`, `68 skipped` (empty accessible description). |
| U4 | Ignore loaded level | Frontend `loads a saved Off and keeps it when saving without changing it`: `1 failed`, `68 skipped` (Normal instead of Off). |

Mutation commands:

- Group 1: `uv run --offline pytest tests/test_context_depth.py -q` for L1–L4/L7; `uv run --offline pytest tests/test_context_links.py -q` for L5.
- Group 2: `uv run --offline pytest tests/test_context_depth.py tests/test_settings_api.py::test_preferences_report_the_server_numbers --tb=short -q` for L6; the exact named API/migration test node(s) from the table with `uv run --offline pytest <nodes> --tb=short -q` for A1/A2/M1.
- Group 3: `uv run --offline pytest <exact run test nodes from the table> --tb=short -q` for G1, R1–R3, L1, L3, L4, L7.
- Group 4: `DEBUG_PRINT_LIMIT=0 npm test -- --run src/pages/Settings.test.tsx -t "<pattern>" --reporter=dot`. Patterns: U1 `saves Off|loads a saved Off`; U2 `names the server`; U3 `shows the linked-pages choice`; U4 `loads a saved Off`.

### Final verification, actual output

All seven required checks exited 0. Existing tests plus the new tests ran offline. No unrelated test failed, so no isolated concurrency retry was needed.

`backend/`: `uv run --offline pytest`

```text
collected 1299 items
====================== 1299 passed, 2 warnings in 52.49s =======================
```

The two existing Pydantic serializer warnings come from `test_usage_of_the_wrong_shape_is_not_counted[seven-3-expected0]` and `[seven-three-expected2]` in `test_anthropic_client.py`, intentionally passing a string for integer `input_tokens`.

`frontend/`: `npm test -- --run`

```text
 Test Files  14 passed (14)
      Tests  340 passed (340)
   Duration  8.09s (transform 1.50s, setup 4.07s, import 5.89s, tests 20.37s, environment 11.45s)
```

`frontend/`: `npm run build`

```text
> tsc --noEmit && vite build
vite v8.3.5 building client environment for production...
transforming...
✓ 40 modules transformed.
rendering chunks...
computing gzip size...
dist/index.html                   0.82 kB │ gzip:  0.41 kB
dist/assets/index-AAF_ZVq5.css   20.60 kB │ gzip:  5.25 kB
dist/assets/index-ag-Gx8jq.js   321.27 kB │ gzip: 98.43 kB
✓ built in 321ms
```

`extension/`: `npm test -- --run`

```text
 Test Files  7 passed (7)
      Tests  169 passed (169)
   Duration  4.64s (transform 251ms, setup 1.16s, import 1.47s, tests 5.78s, environment 6.85s)
```

`extension/`: `npm run build`

```text
> tsc --noEmit && vite build && node scripts/check-build.mjs
vite v8.3.5 building client environment for production...
transforming...
✓ 10 modules transformed.
rendering chunks...
computing gzip size...
dist/popup.html                    0.45 kB │ gzip: 0.29 kB
dist/icon-192.png                  0.52 kB
dist/readability-LICENSE.md        0.55 kB
dist/options.html                  0.76 kB │ gzip: 0.42 kB
dist/readability.js               89.98 kB
dist/assets/options-CUZyiacw.css   1.48 kB │ gzip: 0.72 kB
dist/assets/popup-DKe_ziKL.css     2.03 kB │ gzip: 0.86 kB
dist/assets/options-0axhCIRv.js    2.06 kB │ gzip: 0.98 kB
dist/assets/popup-DUKAg8vm.js     14.21 kB │ gzip: 5.29 kB
✓ built in 265ms
```

Repository: `DO_NOT_TRACK=1 openspec validate add-link-depth-setting --strict`

```text
Change 'add-link-depth-setting' is valid
```

Repository: `git diff --check`, exit 0, no output.

### Deviations and execution adjustments

- No implementation/scope deviations from the approved plan. Protected planning/process files, existing run tests, extension source, progress formula, caps, and dependency files are unchanged.
- During the red phase, router-wide call assertions were moved inside the active respx context, since exiting it resets its aggregate call history. The focused checks then failed on 5 and 2 actual requests, not on an empty/reset history.
- The first attempt to apply R1 accidentally joined two Python statements because the generated replacement lacked a final newline. Pytest exited 4 with a SyntaxError during collection; this was not counted as a mutation kill. The file was restored and its saved diff matched exactly. The correctly formed R1 was then applied alone, failed the required behavioral assertion, and was restored with the same diff check. No required mutation survived.
- The plan's D-023 fresh-eyes check was already recorded by Claude Code in the preceding plan entry of the AI usage log; this run did not claim an additional independent review.

### Deferred verification, as requested

- Docker smoke (`scripts/docker-smoke.sh`) and Docker build: **not performed**, prohibited in this run. Claude Code performs them at review.
- Live scratch-container check at 1280 px and 375 px with accessibility-tree inspection, one run per level against a stub site and model, and request/context comparison: **not performed**. Claude Code performs it at review with fresh volumes, never port 8800.
- User's Shallow-versus-Normal token comparison on their own instance: **not performed**, reserved for the user after merge.
- No push, merge, tag, PR, archival, running-container interaction, or port-8800 access.

### Commits

1. `2d2ad66` — group 1, define linked-page levels.
2. `d3110b5` — group 2, persist preferences and server limits.
3. `3ee1db8` — group 3, per-run snapshot, context integration, README.
4. `5f6fc2e` — group 4, Settings choice and tests.
5. Group 5 records this report, the AI usage entry, and completed task checklist.
