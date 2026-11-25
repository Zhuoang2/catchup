# Test report: add-reasoning-setting (#4)

## Implementation by Factory Droid

2026-11-25. Factory Droid, GPT-6.1 Sol, using `openspec-apply-change` and
`tdd`, starting at approved plan commit `310e23d`. Groups 1–5 were completed
in order. This is implementation evidence, not Claude Code's independent
review.

### Scope and commits

- Group 1, `f3103cb`: provider request fields, constructor validation,
  immediate `ReasoningRejected` errors, factory forwarding and choice lists.
- Group 2, `04d50d6`: migration `0010_model_reasoning`, stored default,
  backwards-compatible API reads/saves and per-provider validation.
- Group 3, `3cbd879`: both run factories receive the saved choice; summary
  rejection stops the run with pending items; Home offers Check settings;
  README documents the setting.
- Group 4, `eb49e10`: accessible Reasoning select, provider reset/restore,
  automatic/test/manual saves and the shared model-choice queue.
- Group 5: this report, the usage-log entry and final task checkboxes.

New tests use the approved client/factory, API, migration, run and rendered
page seams. Existing tests changed only as permitted by tasks.md, including
the head-revision assertions and expected model PUT bodies. The unchanged
extension suite was also run. All provider traffic used MockTransport/respx
with invented credentials; no real network or model provider was used.
Locked dependencies were installed offline; manifests and lockfiles did
not change.

### Red/green evidence

| Group | Before implementation | After implementation |
| --- | --- | --- |
| 1 | Three collection errors: missing `ReasoningRejected` and `REASONING_CHOICES`, explicitly allowed by task 1.1. | `uv run --offline pytest tests/test_llm_client.py tests/test_anthropic_client.py tests/test_model_providers.py`: **119 passed, 2 warnings in 3.71s**. |
| 2 | `tests/test_db.py tests/test_settings_api.py`: **19 failed, 32 passed**, missing column/migration/response field and missing validation. | Same selection: **51 passed in 3.94s**. |
| 3 | Run/provider/README selection: **14 failed, 4 passed**, missing fifth factory argument and README text. Home primary-action selection: **1 failed, 2 passed, 98 skipped**, Try again instead of Check settings. After implementing only factory forwarding, the rejection test still failed because grouping was called, establishing the missing summary propagation separately. | Full backend: **1307 passed, 2 warnings in 43.02s**. Full frontend: **337 passed in 14 files**, 6.83s. |
| 4 | Settings: **22 failed, 51 passed**, absent Reasoning select and absent reasoning in PUT bodies. All eight new tests failed. | Full frontend: **345 passed in 14 files**, 5.11s; TypeScript/Vite build passed, 40 modules, 200ms. |

### Final verification (task 5.1)

All commands exited **0**. Backend commands ran from `backend/`.
Frontend and extension commands ran from their respective directories
after `export PATH="$HOME/.nvm/versions/node/v22.17.1/bin:$PATH"`.
OpenSpec and diff checks ran from the repository root.

| Directory | Command | Actual result output |
| --- | --- | --- |
| backend | `uv run --offline pytest` | `1307 passed, 2 warnings in 39.06s` |
| frontend | `npm test -- --run` | `Test Files  14 passed (14)`; `Tests  345 passed (345)`; `Duration  7.45s` |
| frontend | `npm run build` | `tsc --noEmit && vite build`; `40 modules transformed.`; `built in 348ms` |
| extension | `npm ci --offline --no-audit --no-fund` | `added 120 packages in 2s` |
| extension | `npm test -- --run` | `Test Files  7 passed (7)`; `Tests  169 passed (169)`; `Duration  1.74s` |
| extension | `npm run build` | `tsc --noEmit && vite build && node scripts/check-build.mjs`; `10 modules transformed.`; `built in 151ms` |
| root | `DO_NOT_TRACK=1 openspec validate add-reasoning-setting --strict` | `Change 'add-reasoning-setting' is valid` |
| root | `git diff --check` | No output. |

Frontend offline installation earlier reported `added 124 packages in 1s`.
Both npm installations reported the existing `whatwg-encoding@3.1.1`
deprecation warning. The backend's two warnings are from the existing
`test_usage_of_the_wrong_shape_is_not_counted[seven-3-expected0]` and
`[seven-three-expected2]` cases: intentional malformed `input_tokens` values
trigger Pydantic serializer warnings. No unrelated test failed, so no
isolated concurrency-related rerun was needed.

### Isolated mutations

Each mutation below was applied alone, tested, then restored by file
editing. Before each attempt the full current Git diff was saved in memory;
after restoration another `git diff` was compared byte-for-byte with it.
New migration content was included using `git diff HEAD` after staging the
new file. All valid attempts exited **1**, all expected failures occurred,
and every final restoration matched the saved diff. No survivors.

#### R1–R6: clients and factory

Command for each:
`uv run --offline pytest tests/test_llm_client.py tests/test_anthropic_client.py tests/test_model_providers.py --tb=short`
in `backend/`.

| Mutation | Failed tests | Result |
| --- | --- | --- |
| R1, Off maps to Low | `test_llm_client.py::test_reasoning_choice_sets_reasoning_effort[off-none]` | 1 failed, 118 passed |
| R2, default sends null | `test_llm_client.py::test_reasoning_choice_sets_reasoning_effort[default-None]` | 1 failed, 118 passed |
| R3, reasoning_sent false | `test_llm_client.py::test_refused_reasoning_raises_reasoning_rejected_without_retry[400]` and `[422]` | 2 failed, 117 passed |
| R4, every 400 is ReasoningRejected | `test_llm_client.py::test_other_status_fails_at_once[400]`; `test_refused_reasoning_raises_reasoning_rejected_without_retry[422]`; `test_refusal_with_provider_default_stays_a_provider_error`; `test_model_list_refusal_stays_a_provider_error_with_reasoning_set`; `test_anthropic_client.py::test_failures_that_do_not_retry[400]`; `test_anthropic_refused_reasoning_raises_reasoning_rejected[default-ProviderError]` | 6 failed, 113 passed |
| R5, no beta output_config | `test_anthropic_client.py::test_low_reasoning_sends_output_config_effort[claude-opus-5-5]` | 1 failed, 118 passed |
| R6, factory drops reasoning | `test_model_providers.py::test_factory_passes_the_reasoning_choice[openai_compatible]` and `[anthropic]` | 2 failed, 117 passed |

#### S1–S5: storage and API

Command for each:
`uv run --offline pytest tests/test_db.py tests/test_settings_api.py --tb=short`
in `backend/`.

| Mutation | Failed tests | Result |
| --- | --- | --- |
| S1, migration has no server default | `test_db.py::test_model_reasoning_migration_defaults_existing_config_and_downgrades` | 1 failed, 50 passed |
| S2, all providers accept OpenAI choices | `test_settings_api.py::test_unsupported_reasoning_is_refused[anthropic-off]` | 1 failed, 50 passed |
| S3, omitted/null always defaults | `test_settings_api.py::test_save_without_reasoning_keeps_it[omitted]` and `[null]` | 2 failed, 49 passed |
| S4, provider change keeps old value | `test_settings_api.py::test_provider_change_without_reasoning_resets_it` | 1 failed, 50 passed |
| S5, public response omits reasoning | `test_settings_api.py::test_save_and_read_encrypted_configuration`; `test_save_and_read_anthropic_configuration`; `test_read_without_configuration_reports_default_reasoning`; all four `test_save_and_read_reasoning` cases; both `test_save_without_reasoning_keeps_it` cases; `test_provider_change_without_reasoning_resets_it` | 10 failed, 41 passed |

#### N1–N4 and Doc: runs, Home and README

All pytest selections below used `uv run --offline pytest` and `--tb=short`
from `backend/`. Home used the same Node PATH as final verification.

| Mutation | Selection | Failed tests / result |
| --- | --- | --- |
| N1, summary factory receives default | `tests/test_model_errors.py tests/test_anthropic_runs.py tests/test_digest_runner.py::test_run_passes_the_saved_reasoning_to_every_client` | `test_run_sends_reasoning_effort_on_every_chat_call[low-low]` and `[off-none]`; `test_refused_reasoning_fails_the_run_and_keeps_items_pending`; `test_anthropic_run_sends_low_effort_with_fallback`; `test_run_passes_the_saved_reasoning_to_every_client`. **5 failed, 11 passed**. |
| N2, summary swallows rejection | `tests/test_model_errors.py::test_refused_reasoning_fails_the_run_and_keeps_items_pending` | That test failed because a grouping call was made. **1 failed**. |
| N3, Home omits configuration error | `npm test -- --run src/pages/Home.test.tsx -t "offers the right primary action"` in frontend | `offers the right primary action for reasoning_rejected with reused summary copy`. **1 failed, 2 passed, 98 skipped**. |
| N4, lookup factory gets four arguments | `tests/test_digest_runner.py::test_run_passes_the_saved_reasoning_to_every_client tests/test_digest_runner.py::test_run_passes_the_saved_provider_to_every_client tests/test_anthropic_runs.py::test_anthropic_run_saves_summaries_groups_and_usage` | All three selected tests failed. **3 failed**. |
| Doc, Reasoning paragraph removed | `tests/test_readme_providers.py` | `test_readme_documents_supported_model_providers`. **1 failed**. |

#### F1–F8: Settings

Command for each, from `frontend/` with the Node PATH above:
`npm test -- --run src/pages/Settings.test.tsx`.

| Mutation | Failed tests | Result |
| --- | --- | --- |
| F1, provider switch keeps shown choice | `offers no Off for Anthropic and restores the saved choice` (next PUT sent Off) | 1 failed, 72 passed |
| F2, Anthropic also offers Off | `offers no Off for Anthropic and restores the saved choice` | 1 failed, 72 passed |
| F3, reasoning save skips field-match checks | `waits to save a Reasoning choice when the key was edited`; `sends the shown Reasoning with Save` | 2 failed, 71 passed |
| F4, Save omits reasoning | `keeps the tested models out of the other provider's list`; `sends the provider with Save`; `sends the shown Reasoning with Save` | 3 failed, 70 passed |
| F5, reasoning request bypasses shared queue | `saves a Reasoning choice and a model choice in order` | 1 failed, 72 passed |
| F6, no aria-describedby | `shows the saved Reasoning after the Model select with its hint` | 1 failed, 72 passed |
| F7, queue does not update savedReasoning | `saves a Reasoning choice right away` | 1 failed, 72 passed |
| F8, Save does not update savedReasoning | `sends the shown Reasoning with Save` | 1 failed, 72 passed |

### Deviations and limits

- One invalid R3 mutation attempt used an indentation-losing patch and
  produced three collection `SyntaxError` errors instead of the intended
  behavioral failures. Its initial restore also lost indentation; the
  exact-diff comparison caught this. The file was edited back and compared
  successfully with the saved pre-mutation diff. R3 was then applied with
  its full indentation, rerun alone, and failed the two expected tests.
  The invalid attempt is not counted as a killed mutation.
- No approved behavior, dependency, or scope deviation was needed. All
  stated red/green checks and all valid named mutations held.
- The plan's two recorded untested survivors (Anthropic list lookup's
  reasoning_sent flag and summary fast-shutdown timing) were not added to
  the named mutation set.
- No protected proposal, design, spec delta, decision log or requirements
  log was edited. Prompts, output limits, grouping logic, fallback model
  list, preferences/Digest/YouTube behavior and extension source were not
  changed.
- Docker build/smoke/live checks were not run, as explicitly prohibited for
  this implementation session. They remain for Claude Code review. No
  container, volume, port 8800, push, merge, tag or PR was touched.

## Fix round 1

2026-11-25. Factory Droid (model not exposed in this completion run),
using `openspec-apply-change` and `tdd`, starting at `078f8e9` in Claude
Code's review worktree. Only task group 6 was implemented.

### Regression and fix (6.1–6.2)

Added the three prescribed tests inside `describe('reasoning settings')`,
using the existing rendered-page and mocked-fetch boundaries. No existing
test was changed. From `frontend/`, with the Node PATH below, ran:

```sh
npm test -- --run src/pages/Settings.test.tsx -t "sends a Reasoning choice made during a connection test|keeps the tested provider.s Reasoning when the provider changes during a test|sends the saved Reasoning with the test.s save"
```

- Before the production fix: exit **1**, **1 failed, 2 passed, 74 skipped**.
  `sends a Reasoning choice made during a connection test with the test's save`
  received `[['saved-model', 'low'], ['live-a', 'default']]` instead of
  `[['saved-model', 'low'], ['live-a', 'low']]`.
  `keeps the tested provider's Reasoning when the provider changes during a test`
  and `sends the saved Reasoning with the test's save` both passed.
- After the fix: same command exited **0**, **3 passed, 74 skipped**, 677ms.
  Full frontend tests also passed **349 tests in 14 files**, 4.97s, and the
  TypeScript/Vite build passed, **40 modules**, 215ms, before mutations.
- Confirmed cause: the connection-test continuation always used the
  Reasoning captured before its await. The approved fix reads a ref updated
  on load, Reasoning choice and provider choice, but uses the captured
  tested-provider choice when another provider is selected.
- Diagnostic ranking from the supplied review finding: (1) stale captured
  Reasoning, confirmed by the wrong second body and T1; (2) save-queue
  reordering, ruled out by the observed PUT order; (3) cross-provider value
  mixing, ruled out on the original code by the second regression test.
  The review already supplied the cause and exact minimal fix, so no
  independent exploratory instrumentation or further minimization was needed.

### Isolated mutations T1–T4 (6.2)

Each mutation was applied alone to `Settings.tsx`. For each, ran
`DEBUG_PRINT_LIMIT=0 npm test -- --run src/pages/Settings.test.tsx` in
`frontend/` with the Node PATH below. This environment setting only
suppresses verbose failure DOM dumps. All runs exited **1** for behavioral
assertion failures, with no other failed tests.

| Id | Mutation | Actual failed tests | Actual result |
| --- | --- | --- | --- |
| T1 | Test save always sends `testedReasoning` | `sends a Reasoning choice made during a connection test with the test's save` | 1 failed, 76 passed |
| T2 | Test save always sends `selectedReasoning.current` | `keeps the tested provider's Reasoning when the provider changes during a test` | 1 failed, 76 passed |
| T3 | `chooseReasoning` does not update the ref | `sends a Reasoning choice made during a connection test with the test's save`; `waits to save a Reasoning choice when the key was edited` | 2 failed, 75 passed |
| T4 | Page load does not update the ref | `sends the saved Reasoning with the test's save` | 1 failed, 76 passed |

Before each mutation, saved the complete `git diff --binary` in memory.
After each run, restored by editing, then compared the entire diff with
that mutation's saved diff byte-for-byte. **All four matched exactly**.
No mutation survived and no invalid mutation attempt occurred.

### Full verification (6.3)

All commands below exited **0**, after all mutations were restored.
Backend commands ran in `backend/`, frontend/extension commands in their
respective directories, and OpenSpec/diff checks at the repository root.
Every npm command used
`export PATH="$HOME/.nvm/versions/node/v22.17.1/bin:$PATH"`.

| Directory | Command | Actual result output |
| --- | --- | --- |
| backend | `uv run --offline pytest` | `1309 passed, 2 warnings in 33.28s` |
| frontend | `npm test -- --run` | `Test Files  14 passed (14)`; `Tests  349 passed (349)`; `Duration  6.36s` |
| frontend | `npm run build` | `tsc --noEmit && vite build`; `40 modules transformed.`; `built in 293ms` |
| extension | `npm test -- --run` | `Test Files  7 passed (7)`; `Tests  169 passed (169)`; `Duration  3.58s` |
| extension | `npm run build` | `tsc --noEmit && vite build && node scripts/check-build.mjs`; `10 modules transformed.`; `built in 129ms` |
| root | `DO_NOT_TRACK=1 openspec validate add-reasoning-setting --strict` | `Change 'add-reasoning-setting' is valid` |
| root | `git diff --check` | No output. Repeated after evidence/checklist edits. |

The two backend warnings remain the intentional malformed-input-token
Pydantic serializer warnings from the existing Anthropic usage-shape tests.
All other suites were existing checks; this round added only the three
Settings regressions above.

### Deviations and limits

No behavior or task-plan deviation was needed. Both `node_modules`
directories already existed, so installation was skipped as permitted by
the fix-round prompt; no manifest, lockfile or dependency was changed.
All tests used mocked provider traffic and invented credentials.
Only Settings source/tests, this report, the AI usage log and group 6
checkboxes were edited. No temporary helper files or debug instrumentation
were created. No Docker/smoke/live check, real-provider request, secret
access, port 8800, container/volume change or publishing action occurred.
Docker smoke and live checks remain with Claude Code review.

## Review by Claude Code

Reviewed in worktree `review4` on the branch. Droid's first run started at the plan commit `310e23d` and ended at `0c9e593`; fix round 1 started at its plan commit `9794c2a` (with fresh-eyes fixes in `078f8e9`) and ended at `b7a82e8`.

### Checks

| Check | Result |
| --- | --- |
| Backend `uv run --offline pytest` | 1307 passed on `0c9e593`; 1309 with Claude's review tests (`e3c8abc`) and after fix round 1 |
| Frontend `npm test -- --run`, `npm run build` | 345 passed on `0c9e593`, 346 with Claude's review test, 349 after fix round 1; build passed |
| Extension `npm test -- --run`, `npm run build` | 169 passed; build passed |
| `DO_NOT_TRACK=1 openspec validate add-reasoning-setting --strict` | valid |
| `git diff --check 310e23d..HEAD` | clean |
| `scripts/docker-smoke.sh catchup:fix4-local` (built from `0c9e593`, then from `b7a82e8`) | 12 of 12 both times |

### Live check

A scratch container from `catchup:fix4-local` (built from `0c9e593`) ran on its own volume and port 8844, with a local stub on the host that answered both the OpenAI-compatible chat API and the Anthropic Messages API (as a stream) and recorded every request body. Each run summarized two pages saved through the extension API.

| Setting | Requests | Run |
| --- | --- | --- |
| OpenAI-compatible, Low | every chat call had `reasoning_effort: "low"`, none had `thinking` | succeeded |
| OpenAI-compatible, Off | every chat call had `reasoning_effort: "none"` | succeeded |
| OpenAI-compatible, Low, stub answers 400 | each summary call made once, no grouping call | failed with `reasoning_rejected` and "The model provider rejected a request with the Reasoning setting. Choose Provider default in Settings, then generate again."; items stayed pending and were summarized by the next run |
| OpenAI-compatible, Provider default | no call had `reasoning_effort` | succeeded |
| Anthropic, Off | — | the save was refused with 422 `invalid_reasoning` |
| Anthropic, Low (`claude-opus-5-5`) | every Messages call went to the beta endpoint with `server-side-fallback-2026-07-01`, `output_config: {"effort": "low"}`, and `fallbacks: "default"`, and none had `thinking` | succeeded |

In the browser, with Anthropic and Low saved, Settings showed the Reasoning select after Model, with the options "Provider default" and "Low" and the hint linked by `aria-describedby`; choosing "Provider default" sent one `PUT` and announced "Saved reasoning: Provider default."

After fix round 1, a second scratch container from `catchup:fix4-local` (built from `b7a82e8`) ran on port 8845 against a stub whose model list answered after 6 seconds. With Provider default saved, Claude clicked "Test connection" in the browser and chose "Low" while the test was still waiting. Two `PUT`s followed: the Reasoning choice's, then the test's; both answered `reasoning: "low"`, the select read Low, and the saved configuration read Low.

The containers, their volumes, the stubs, and the browser tab were removed afterwards.

### Findings

- **`/code-review` (high) on `310e23d..0c9e593`** (none changed):
  - with Reasoning on, any 400 or 422 fails the run with the Reasoning message, even when another cause made the provider refuse: this is decision U2, option A, as the user approved;
  - an invalid value stored by hand fails the run with a generic error: the API refuses such values (design D5);
  - a Reasoning choice made before any model is saved is sent by the next test or Save, without a message: as design D6 says.
- **Spec sub-agent** (independent, detached worktree; all 26 named mutations failed their tests):
  - **Fixed in fix round 1 (Droid; D-023 class b):** a Reasoning choice made while a connection test ran was saved at once and then overwritten by the test's save, which sent the value shown at the test's start. The select then read "Low" while Provider default was saved. Design D6 had said "the value shown when the test started", against the spec's "the Reasoning choice shown when that save starts". Task group 6 added three tests and a ref (`selectedReasoning`) that the test's save reads; when another provider was chosen during the test, the save keeps the tested provider's value, a rule now in the spec delta with the scenario "Choice made during a connection test". A fresh sub-agent's check of group 6 added the page-load test (T4). Claude re-ran T1–T4 on `b7a82e8`: each failed its named tests (T3 also `waits to save a Reasoning choice when the key was edited`), and the code was restored exactly.
  - **Fixed by Claude (test only, D-023 class c):** the Anthropic refusal rule is now tested at 422 as well as 400 (mutation "400 only" had passed); a model choice followed by a Reasoning choice is now tested (mutation X12, which saved the saved model instead of the chosen one, had passed). Both mutations fail the new tests.
  - **Recorded, not fixed:** leaving `ReasoningRejected` out of the fast pool shutdown only delays the failure (a probe measured 0.05 s against 3.01 s); the Anthropic model list passing the flag has no visible effect; merge calls and long-item part and combine calls send the setting through the same `chat_json` (a probe saw all 17 calls carry it), with no committed test of their own.
  - **Plan wording:** the F7 and F8 rows of task 4.3 lost their indent in Claude's plan fix; restored.
