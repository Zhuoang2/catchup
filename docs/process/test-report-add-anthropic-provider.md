# add-anthropic-provider (#12): test report

## Implementation by Factory Droid, 2026-11-22

Approved plan: `2ca7990`, with the README verification-order correction in
`410df93`. U1–U6 use the user's recommended choices. Implementation commits:
`4c9710e` (client), `d351a00` (provider setting, runs, README), and `afa3cc7`
(Settings). Group 4 records the evidence and final task check-offs separately.

All model traffic in the new tests used `httpx2.MockTransport`, with host
assertions for `anthropic.example` and invented credentials. No real model
API, Docker command, container, volume, or port 8800 was used. Docker smoke
and live checks remain for Claude Code's review.

### Final checks (task 4.1)

Every command below exited 0. Backend commands ran in `backend/`. Frontend
and extension commands ran in their respective directories with:

```sh
export PATH="$HOME/.nvm/versions/node/v22.17.1/bin:$PATH"
```

The Node version check printed `v22.17.1`. No dependency manifest or lockfile
was changed. Frontend dependencies were installed before group 3 with
`npm ci --offline --no-audit --no-fund` (124 packages added). The extension
installation below added 120 locked packages offline. Both installations
reported the existing `whatwg-encoding` deprecation warning.

| Directory | Command | Output / result |
| --- | --- | --- |
| `backend/` | `uv run --offline pytest` | **1147 passed, 2 warnings in 48.98s** |
| `frontend/` | `npm test -- --run` | **14 files passed; 321 tests passed**, duration 8.55s |
| `frontend/` | `npm run build` | `tsc --noEmit && vite build`; **40 modules transformed; built in 372ms** |
| `extension/` | `npm ci --offline --no-audit --no-fund` | **added 120 packages in 2s** |
| `extension/` | `npm test -- --run` | **7 files passed; 168 tests passed**, duration 2.55s |
| `extension/` | `npm run build` | `tsc --noEmit && vite build && node scripts/check-build.mjs`; **10 modules transformed; built in 450ms** |
| repository root | `DO_NOT_TRACK=1 openspec validate add-anthropic-provider --strict` | `Change 'add-anthropic-provider' is valid` |
| repository root | `git diff --check` | No output, exit 0 |

The two backend warnings come from the deliberately malformed input-token
usage fixtures (`"seven"`), serialized by Pydantic inside the SDK.
They are not provider requests or test failures. Coverage was not measured.

Final build output:

```text
Frontend:
dist/index.html                   0.82 kB | gzip:  0.41 kB
dist/assets/index-2FHpjrn6.css   20.50 kB | gzip:  5.24 kB
dist/assets/index-DKXktsdU.js   319.16 kB | gzip: 97.82 kB

Extension:
dist/popup.html                    0.45 kB | gzip: 0.29 kB
dist/icon-192.png                  0.52 kB
dist/readability-LICENSE.md        0.55 kB
dist/options.html                  0.76 kB | gzip: 0.42 kB
dist/readability.js               89.98 kB
dist/assets/options-CUZyiacw.css   1.48 kB | gzip: 0.72 kB
dist/assets/popup-DKe_ziKL.css     2.03 kB | gzip: 0.86 kB
dist/assets/options-0axhCIRv.js    2.06 kB | gzip: 0.98 kB
dist/assets/popup-CudKrUKx.js     14.15 kB | gzip: 5.26 kB
```

### SDK probes (task 1.1)

1. In `backend/`:

   ```sh
   uv run --offline python -c "import anthropic; print(anthropic.__version__)"
   ```

   Output: **`1.13.0`**, exit 0. The fresh worktree's environment was
   populated from the existing lockfile and local cache, without adding,
   upgrading, or removing a project dependency.

2. A temporary `/tmp/catchup-anthropic-stream-probe.py` constructed the
   official SDK with an explicit invented key, `https://anthropic.example`,
   `max_retries=0`, and an `httpx2.Client` using `MockTransport`. The handler
   checked the host and `/v1/messages`, returned an HTTP 200 HTML page,
   and the script called `get_final_message()` on the stream.

   ```sh
   uv run --offline python /tmp/catchup-anthropic-stream-probe.py
   ```

   Output: **`AssertionError`**, exit 0, the expected exception class.
   The temporary probe was deleted before the group-1 commit.

### Red/green evidence

- **1.1:** The new client test file failed collection with
  `ModuleNotFoundError: catchup.llm.anthropic_client`, as planned.
- **1.2:** Client tests then passed **48** cases. The unchanged
  `tests/test_llm_client.py` passed **44** cases. The complete backend suite
  passed **1130** cases before group 2.
- **2.1:** The factory and Anthropic run tests failed collection on the
  missing `catchup.llm.providers` module. The migration test failed on the
  missing `provider` field; migration packaging/head checks also failed.
  Settings tests failed on missing provider fields, validation, key rules,
  context-window clearing, and the new fourth factory argument. The runner
  test failed because factory calls lacked the saved provider. The README
  test failed on the missing "Supported model providers" heading.
- **2.2:** All six named non-README test files passed, **133 cases**.
  `uv run --offline pytest --ignore=tests/test_readme_providers.py` then
  passed **1146** cases.
- **2.3:** `tests/test_readme_providers.py tests/test_readme_context.py
  tests/test_install_docs.py` passed **28** cases, and the full backend suite
  passed **1147** cases.
- **3.1:** Settings tests reported **18 failed, 44 passed**: the seven new
  tests could not find Provider, and the updated body assertions lacked
  `provider` in the actual requests.
- **3.2, initial attempt:** After implementation, **61 passed, 1 failed**.
  The remaining failure was an ambiguous new test selector, not a failed
  provider-body or status assertion. Implementation stopped as instructed.
- **3.2, resumed:** With the approved one-line test correction below, the
  full frontend suite passed **321** cases and the build passed. After
  F1–F4 were restored, the Settings file passed **62** cases.

New checks comprise 65 backend test cases and seven Settings test cases.
Existing suites were preserved except the explicit factory-arity,
head-revision, public-settings-field and request-body updates allowed by
the plan. The unchanged extension suite was run as a regression check.

### Named mutations

Every mutation was applied alone. Its result was inspected before the next
mutation. Source was restored by editing, not a Git restore/reset command,
and the restored diff was checked against the pre-mutation baseline.
Every named mutation was caught; none survived.

All A mutations ran against `tests/test_anthropic_client.py` using
`uv run --offline pytest` (with quiet/traceback display flags where useful).
Names below are test function names in that file.

| Mutation | Change | Tests that failed | Result |
| --- | --- | --- | --- |
| A1 | Remove output floor | `test_json_answer_request_shape_and_no_key_in_logs` | 1 failed, 47 passed |
| A2 | Treat refusal as empty answer | `test_refusal_fails_at_once` (3 calls instead of 1) | 1 failed, 47 passed |
| A3 | Remove 529 from temporary statuses | `test_temporary_errors_retry_then_succeed[529]`; `test_overload_exhaustion` (1 call instead of 3) | 2 failed, 46 passed |
| A4 | Remove spend-limit check | `test_failures_that_do_not_retry[spend-limit]` | 1 failed, 47 passed |
| A5 | Send fallback for every model | `test_json_answer_request_shape_and_no_key_in_logs`; `test_fallback_models[claude-haiku-5-5-False]`; `test_fallback_models[claude-sonnet-4-6-False]` | 3 failed, 45 passed |
| A6 | Omit cache tokens | `test_usage_sums_input_cache_and_output_tokens_across_threads` (40 input tokens instead of 60) | 1 failed, 47 passed |
| A7 | Remove explicit SDK base URL | All 48 cases, including `test_host_environment_credentials_are_never_used` | 48 failed |
| A8 | Disable fence parsing | Both cases of `test_fenced_json_is_accepted_without_retry` | 2 failed, 46 passed |
| A9 | Keep retired models | `test_lists_models_with_positive_context_windows_and_opus_first` | 1 failed, 47 passed |
| A10 | Do not retry stream errors | `test_temporary_errors_retry_then_succeed[stream-overloaded]` and `[stream-api]` | 2 failed, 46 passed |

A7 still used only MockTransport: the host assertions caught the SDK's
default host, or `env.example` in the environment-isolation case. No request
reached either address. Restoring A1 was also checked by exact file
comparison and a new-file Git diff; subsequent client restores were checked
against the staged baseline. The restored client file passed all 48 cases.

P and Doc mutations used `uv run --offline pytest` with the test selections
listed below.

| Mutation | Change | Tests that failed | Result |
| --- | --- | --- | --- |
| P1 | Pass `openai_compatible` at both runner factory calls | `tests/test_digest_runner.py::test_run_passes_the_saved_provider_to_every_client`; both `tests/test_anthropic_runs.py` tests (`test_anthropic_run_saves_summaries_groups_and_usage`, `test_anthropic_rejected_key_fails_the_run`) | 3 failed |
| P2 | Ignore provider in both key guards | `tests/test_settings_api.py::test_provider_change_requires_a_new_key` | 1 failed |
| P3 | Keep context window on provider change | `tests/test_settings_api.py::test_provider_change_clears_the_context_window` | 1 failed |
| P4 | Omit migration server default | `tests/test_db.py::test_model_provider_migration_defaults_existing_config_and_downgrades` (SQLite refuses the NOT NULL column on an existing row) | 1 failed |
| P5 | Ignore body's provider at test endpoint | `tests/test_settings_api.py::test_connection_test_passes_the_provider` | 1 failed |
| P6 | Disable provider validation | `tests/test_settings_api.py::test_unknown_provider_is_refused` | 1 failed |
| Doc | Remove provider heading | `tests/test_readme_providers.py::test_readme_documents_supported_model_providers` | 1 failed |

The initial Doc restore left a misplaced blank line. The diff showed it,
the spacing was edited back immediately, and an empty diff confirmed the
exact restore before continuing. The post-restore provider regression
selection passed **31** cases.

All F mutations ran against the complete Settings file:

```sh
npm test -- --run src/pages/Settings.test.tsx --reporter=dot
```

`DEBUG_PRINT_LIMIT=0` only shortened DOM diagnostics for these runs.

| Mutation | Change | Tests that failed | Result |
| --- | --- | --- | --- |
| F1 | Omit provider from connection-test body | `tests and saves a new provider with its key` | 1 failed, 61 passed |
| F2 | Do not switch base URL | `fills in the Anthropic address and empties the model list when Anthropic is chosen`; `tests and saves a new provider with its key` | 2 failed, 60 passed |
| F3 | Always show saved-key text | `fills in the Anthropic address and empties the model list when Anthropic is chosen` | 1 failed, 61 passed |
| F4 | Always use DeepSeek URL example | `names the Anthropic address in the invalid-URL message` | 1 failed, 61 passed |

Each F restore returned an empty
`git diff --exit-code -- frontend/src/pages/Settings.tsx` against its staged
baseline. The restored file passed all **62** Settings tests.

### Stops, diagnosis, and approved adjustments

1. **Earlier session before implementation.** Session
   `f6a7abdc-b016-4ce6-a56d-a65a90bb84be` stopped without changing anything:
   task 2.2 required README tests from 2.1 to pass before task 2.3 wrote the
   README. Claude Code confirmed that ordering contradiction and committed
   `410df93`, changing only the two verification lines. This implementation
   started from the beginning using that corrected order.

2. **This session at 3.2.** The supplementary assertion in the new-provider
   test used `screen.getByText(/Saved key ending in/)`. Both the required
   success status and the saved-key hint contain that phrase. The green
   attempt failed with "Found multiple elements with the text", with 61
   other Settings tests passing. Droid stopped, activated diagnosing-bugs,
   and ranked:
   1. ambiguous test selector matching the status and hint;
   2. duplicate page rendering producing duplicate hints;
   3. stale asynchronous state retaining an earlier key/status.

   Claude Code agreed with the first hypothesis. The resumed instruction
   authorized exactly one assertion change, following existing tests:

   ```tsx
   expect(document.getElementById('key-saved')).toHaveTextContent('Saved key ending in 7d2e')
   ```

   No other existing test was changed on resume. The complete frontend
   suite and build then passed, confirming the selector cause. Task 3.2
   was checked off only after that verification.

There was no redesign or requirement deviation. The two stops and approved
corrections above are retained as process evidence. The locked Anthropic
SDK and all package manifests/lockfiles stayed unchanged. No protected
proposal, design, spec, decision-log or requirements-change file was edited.
Session metrics are left to Claude Code.
