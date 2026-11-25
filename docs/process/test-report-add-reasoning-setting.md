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
