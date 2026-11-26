# Test report: add-deep-link-level (#54)

## Implementation by Factory Droid

Date: 2026-11-25. Tool/model: Factory Droid, GPT-6.1 Sol.
Starting commit: `54825d3`. Branch: `add-deep-link-level`.

Implemented task groups 1–4 with `openspec-apply-change` and `tdd`.
Tests were written and run before the corresponding implementation, in the
group order required by `tasks.md`. No unplanned existing test was changed.
Proposal, design, spec deltas, decision log, and requirements log were not edited.
No dependencies, environment settings, migrations, or model calls were added.

### Environment and isolation

- Backend commands ran in `backend/` with `uv run --offline`, Python 3.12.13
  and pytest 9.1.1. The first run created the worktree's virtual environment
  from the local cache (62 locked packages); no new package was added.
- Every frontend and extension command used this setup in its own shell:

  ```sh
  export NVM_DIR="$HOME/.nvm"
  . "$NVM_DIR/nvm.sh"
  nvm use 22.17.1
  ```

  Output: `Now using node v22.17.1 (npm v10.9.2)`.
- `npm ci --offline --no-audit --no-fund` succeeded in both `frontend/`
  (124 packages) and `extension/` (120 packages). Both emitted the locked
  `whatwg-encoding@3.1.1` deprecation warning. No manifests or lockfiles changed.
- All new context-run tests use `public_dns` and
  `respx.mock(assert_all_mocked=True, assert_all_called=False)`. The existing
  autouse fixture refuses real DNS and socket connections; model and collection
  boundaries use the existing offline stubs.

## Red/green evidence and verification commands

Paths and working directories below are relative to this worktree. Expected
red and mutation runs deliberately exited nonzero; all ordinary checks passed.

| Task / directory | Command | Actual result |
| --- | --- | --- |
| 1.1, `backend/` | `uv run --offline pytest tests/test_context_depth.py` | Exit 2; 0 collected, 1 collection error: `TypeError: ContextLimits.__init__() takes 4 positional arguments but 6 were given`. |
| 1.1, `backend/` | `uv run --offline pytest tests/test_context_gather.py -k 'test_deep_reads_twice_normals_links or test_page_cut_follows_the_level or test_deep_caps_an_items_linked_context or test_deep_doubles_the_run_limit or test_deep_reads_author_replies'` | Exit 1; 4 failed, 4 passed, 75 deselected. Failures were exactly twice-Normal links, Deep page cut, Deep item cap, and Deep run limit. |
| 1.2, `backend/` | `uv run --offline pytest tests/test_context_depth.py tests/test_context_gather.py` | 99 passed before mutations; 99 passed after restoring all group 1 mutations. |
| 1.2, `backend/` | `uv run --offline pytest` | 1,376 passed, 2 warnings, 35.04s. All other existing tests unchanged. |
| 2.1, `backend/` | `uv run --offline pytest -q --tb=short tests/test_context_depth.py tests/test_settings_api.py tests/test_readme_context.py -k "test_link_depths or test_link_depth_pages or test_preference_save_and_read or test_partial_preference_updates_keep_other_values or test_image_preference_can_be_saved_without_changing_others or test_link_depth_save_and_read or test_invalid_link_depth or test_preferences_report_the_server_numbers or test_preference_numbers_cannot_be_written or test_readme_documents_public_context_limits_and_robots"` | Exit 1; all 17 selected cases failed, 45 deselected. Deep was absent from the level list and page numbers, saving Deep returned 422, the error message named three levels, the new response field and README phrases were absent. |
| 2.2, `backend/` | `uv run --offline pytest tests/test_context_depth.py tests/test_settings_api.py tests/test_readme_context.py` | 62 passed before mutations; 62 passed after restoring all group 2 mutations. |
| 2.2, `backend/` | `uv run --offline pytest` | 1,377 passed, 2 warnings, 32.80s. |
| 2.2, repository root | `bash -n scripts/docker-smoke.sh` | Exit 0, no output. Syntax only; the script was not executed. |
| 3.1, `frontend/` | `npm test -- --run src/pages/Settings.test.tsx` | Exit 1; 4 failed, 79 passed. Exactly the two changed linked-pages tests and the two new Deep tests failed because there was no Deep option. |
| 3.2, `frontend/` | `npm test -- --run src/pages/Settings.test.tsx` | 83 passed before mutations; 83 passed after restoring F1–F4. |
| 3.2, `frontend/` | `npm test -- --run` | 355 passed in 14 files. |
| 3.2, `frontend/` | `npm run build` | Exit 0; `tsc --noEmit && vite build`; 40 modules transformed. |
| 4.1, `backend/` | `uv run --offline pytest` | **1,377 passed, 2 warnings, 36.95s**. |
| 4.1, `frontend/` | `npm test -- --run` | **355 passed in 14 files**, 6.32s. |
| 4.1, `frontend/` | `npm run build` | Exit 0; TypeScript and Vite succeeded, 40 modules transformed, built in 251ms. |
| 4.1, `extension/` | `npm test -- --run` | **169 passed in 7 files**, 3.42s. Existing tests only; extension code unchanged. |
| 4.1, `extension/` | `npm run build` | Exit 0; TypeScript, Vite, and `node scripts/check-build.mjs` succeeded, 10 modules transformed, built in 229ms. |
| 4.1, repository root | `DO_NOT_TRACK=1 openspec validate add-deep-link-level --strict` | Exit 0: `Change 'add-deep-link-level' is valid`. |
| Each group and final documentation, repository root | `git diff --check` | Exit 0, no output. Also checked the complete change against `54825d3` before the report commit. |

The two backend warnings come from the existing
`test_usage_of_the_wrong_shape_is_not_counted[seven-3-expected0]` and
`[seven-three-expected2]` cases: Pydantic warns that the deliberately malformed
`input_tokens='seven'` is not an integer. No unexpected test failed.

Final frontend output:

```text
dist/index.html                   0.82 kB | gzip:  0.41 kB
dist/assets/index-AAF_ZVq5.css   20.60 kB | gzip:  5.25 kB
dist/assets/index-6df0aSA4.js   322.82 kB | gzip: 98.82 kB
```

## Test-to-requirement map

All tests below are the new tests or the existing tests the plan explicitly
allowed changing. Other backend, frontend, and extension tests are unchanged
regression coverage. Mutation claims are limited to the runs actually performed.

| Test | Spec scenario / requirement and observation | Named mutations killed |
| --- | --- | --- |
| `test_context_limits` (all 11 rows, changed) | Content collection, “Choose how many linked pages a run reads”: all five limits are explicit for Off, Shallow, Normal, Deep, server overrides, replies disabled, and unknown/empty fallback. | E1–E5 on Deep rows; E6 on every non-Deep row. |
| `test_deep_reads_twice_normals_links` (new) | “Deep reads twice Normal's links”: first 16 pages and their robots.txt fetched once; seventeenth untouched; progress 16/16. | E1. |
| `test_page_cut_follows_the_level[shallow,normal,deep]` (new, 3 cases) | “Deep keeps more of each page”: one stored context of exactly 3,000 / 3,000 / 6,000 characters. | E3 and G1 at Deep; E6 at Normal and Shallow. |
| `test_deep_caps_an_items_linked_context` (new) | “Deep caps an item's linked context”: lengths `[6000, 6000, 6000, 6000, 6000, 2000]`, with the final two pages never requested. | E4, G1, G2, G3. |
| `test_deep_doubles_the_run_limit[normal,deep]` (new, 2 cases) | “Deep doubles the per-run limit”: with a server budget of 5 and one robots.txt request, Normal reads 4 pages, Deep all 8. | E2 at Deep; Normal is unchanged comparison coverage. |
| `test_deep_reads_author_replies` (new) | “Deep reads author replies”: exactly the A1 author-replies context, containing “Because of the update.” | E5. |
| `test_link_depths` (changed) | Four allowed levels under “Choose how many linked pages a run reads”. | E7. |
| `test_link_depth_pages` (changed, 4 cases) | UI “Default choice” / “Server numbers” API support: Deep reports 16, 10, 4, 2 for server link settings 8, 5, 2, 1. | E8 on the three nondefault cases. |
| `test_link_depth_save_and_read` (changed) | UI “Save Deep” API support: PUT accepts Deep and subsequent GET preserves it, with earlier Off and Shallow checks retained. | E7. |
| `test_invalid_link_depth` (changed, 5 cases) | Four-level API validation: unknown/case-invalid/empty values get 422 and the exact four-level message, without changing stored preferences. | A2, every case. |
| `test_preferences_report_the_server_numbers` (changed) | UI “Server numbers” API support: Deep uses the server's doubled link and request budgets, not fixed defaults. | E8, A1. |
| `test_preference_numbers_cannot_be_written` (changed) | Read-only budget fields in design D3, supporting the server-number requirement: submitted budgets cannot override server settings. | No separate named mutation run. |
| `test_preference_save_and_read` (changed) | Default preferences and digest-language saves return the four-level page map and Deep request budget. | No separate named mutation run. |
| `test_partial_preference_updates_keep_other_values` (changed) | Digest preferences remain independent, with both read-only budget fields returned after partial saves. | No separate named mutation run. |
| `test_image_preference_can_be_saved_without_changing_others` (changed) | Existing image and other preference behavior unchanged while answers expose Deep budgets. | No separate named mutation run. |
| `test_readme_documents_public_context_limits_and_robots` (changed) | Content collection limits documentation (design D5): Deep explanation and small-model guidance, retaining all earlier required phrases. | R1. |
| `shows the linked-pages choice with its numbers and cost note` (changed) | UI “Default choice”: four exact labels, Normal selected, exact accessible cost note, and the existing accessibility audit. | F1, F4. |
| `names the server's own numbers` (changed) | UI “Server numbers”: Deep labels 10 then 2 pages, and accessible description with 40 requests / 80 at Deep. | F2, F3. |
| `saves Deep with the other digest preferences` (new) | UI “Save Deep”: choose Deep, Save, see “Settings saved.”, and inspect the PUT alongside all other Digest preferences. | No separate named mutation run; failed before implementation. |
| `loads a saved Deep and keeps it when saving without changing it` (new) | UI “Save Deep” reopening/preservation: load Deep, Save, keep the selected value and PUT Deep. | No separate named mutation run; failed before implementation. |
| Existing `loads stored images off and preserves off when saving without changing it`, `explains authentication errors`, and `shows the first-run key hint and saves preferences without exposing the key` | Only their applied preferences GET fixtures gained the two Deep fields, as authorized. Existing behavioral assertions unchanged; all passed even in the red Settings run. The shared/default GET fixtures received the same updates. | No separate named mutation run. |

## Named mutation evidence

Each of the **18 named mutations** was applied alone. Every listed test failed
for its behavioral assertion, not a syntax/collection error. After each run,
the code was edited back and `git diff -- <mutated-file>` was compared with the
exact pre-mutation diff; every comparison matched. No mutation remains.

Backend mutation commands ran in `backend/` as
`uv run --offline pytest -q --tb=short <selectors>`, with every selector below
prefixed by `tests/` and shell-quoted individually. Abbreviations:
`D = test_context_depth.py::`, `G = test_context_gather.py::`,
`A = test_settings_api.py::`, `R = test_readme_context.py::`.
Comma-separated bracket ids below mean separate full selectors, not a single
pytest expression.

| ID | Single mutation | Exact selected tests (abbreviated paths only) | Actual result |
| --- | --- | --- | --- |
| E1 | Deep links use Normal's count. | D`test_context_limits[deep]`, D`test_context_limits[deep_server]`, G`test_deep_reads_twice_normals_links` | Exit 1; 3 failed. |
| E2 | Deep requests use Normal's budget. | D`test_context_limits[deep]`, D`test_context_limits[deep_server]`, G`test_deep_doubles_the_run_limit[deep]` | Exit 1; 3 failed. |
| E3 | Deep page cut uses 3,000. | D`test_context_limits[deep]`, G`test_page_cut_follows_the_level[deep]` | Exit 1; 2 failed. |
| E4 | Deep item cap uses 16,000. | D`test_context_limits[deep]`, G`test_deep_caps_an_items_linked_context` | Exit 1; 2 failed. |
| E5 | Deep author replies disabled. | D`test_context_limits[deep]`, G`test_deep_reads_author_replies` | Exit 1; 2 failed. |
| E6 | `ContextLimits.page_chars` default uses 6,000. | D`test_context_limits` with ids `off`, `shallow`, `shallow_under_2`, `shallow_no_replies`, `normal`, `normal_server`, `unknown`, `empty`; G`test_page_cut_follows_the_level[normal]`, G`test_page_cut_follows_the_level[shallow]` | Exit 1; 10 failed. |
| G1 | Gather cut keeps literal `3000`. | G`test_page_cut_follows_the_level[deep]`, G`test_deep_caps_an_items_linked_context` | Exit 1; 2 failed. |
| G2 | Gather loop check keeps literal `16_000`. | G`test_deep_caps_an_items_linked_context` | Exit 1; 1 failed. |
| G3 | Gather cut keeps literal `16_000`. | G`test_deep_caps_an_items_linked_context` | Exit 1; 1 failed. |
| E7 | Allowed levels omit Deep. | D`test_link_depths`, A`test_link_depth_save_and_read` | Exit 1; 2 failed. |
| E8 | Deep page count fixed at 16. | D`test_link_depth_pages[5-expected1]`, D`test_link_depth_pages[2-expected2]`, D`test_link_depth_pages[1-expected3]`, A`test_preferences_report_the_server_numbers` | Exit 1; 4 failed. |
| A1 | API Deep budget reports Normal's budget. | A`test_preferences_report_the_server_numbers` | Exit 1; 1 failed. |
| A2 | Error message lists only three levels. | A`test_invalid_link_depth` (all 5 cases) | Exit 1; 5 failed. |
| R1 | README Deep limits sentence removed. | R`test_readme_documents_public_context_limits_and_robots` | Exit 1; 1 failed. |
| F1 | Deep option replaced by `{null}`. | `shows the linked-pages choice with its numbers and cost note` | Exit 1; 1 failed, 82 skipped. |
| F2 | Deep label fixed at 16 pages. | `names the server's own numbers` | Exit 1; 1 failed, 82 skipped. |
| F3 | Note's Deep budget fixed at 120. | `names the server's own numbers` | Exit 1; 1 failed, 82 skipped. |
| F4 | Note says 3,000 characters at Deep. | `shows the linked-pages choice with its numbers and cost note` | Exit 1; 1 failed, 82 skipped. |

Frontend mutation commands, after the Node setup above:

```sh
# F1 and F4, each applied and restored separately
npm test -- --run src/pages/Settings.test.tsx -t "shows the linked-pages choice with its numbers and cost note"
# F2 and F3, each applied and restored separately; dot matches the apostrophe
npm test -- --run src/pages/Settings.test.tsx -t "names the server.s own numbers"
```

## Commits and remaining review checks

- Group 1: `3b50c94`, `feat: gather linked context with Deep limits (#54)`.
- Group 2: `209c5e5`, `feat: expose Deep linked-page preferences (#54)`.
- Group 3: `6ec4cb3`, `feat: offer Deep linked pages in Settings (#54)`.
- Group 4: the report/usage-log commit containing this file.

Not performed, explicitly reserved for Claude Code review:

- Docker image build and `scripts/docker-smoke.sh` execution. Only the two
  expected preferences answers were edited, and `bash -n` was run.
- Design “Rollout” live check: fresh scratch volume and non-8800 port, local
  stub model/site, Settings at 1280px and 375px with accessibility-tree reading
  and Deep persistence, then compare Normal versus Deep requests/context
  lengths for 17 links including a long page.
- The user's Normal/Deep token-total comparison with their own model is an
  after-merge user check, not an offline test result.

No Docker command, container operation, port-8800 access, push, merge, tag,
or PR action was performed. No implementation task is blocked.
