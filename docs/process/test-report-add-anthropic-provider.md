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

## Fix round 1

Factory Droid, GPT-6.1 Sol, 2026-11-22. Started at `01645df` in Claude
Code's review worktree, after the group-5 plan in `2207837` and its
fresh-eyes corrections in `01645df`. Only group 5 was implemented.

### Reproduction and diagnosis (5.1)

Added the tests at the agreed adapter/MockTransport and rendered Settings
seams. Existing tests were unchanged, except extending `stream_body` with
the optional `iterations` keyword and corresponding event usage field.
`BrokenStream` yields only the first `message_start` event, then raises
the supplied read-timeout or dropped-connection exception.

In `backend/`:

```sh
uv run --offline pytest tests/test_anthropic_client.py -k 'stream_cut_by_the_network_names_the_base_url or fallback_usage_counts_every_attempt' -q --tb=short
```

Observed **3 failed, 48 deselected** in 3.97s, exit 1, exactly as planned:

- `test_stream_cut_by_the_network_names_the_base_url[read-timeout]`:
  raw `httpx2.ReadTimeout`, rather than `ConnectionFailed`.
- `test_stream_cut_by_the_network_names_the_base_url[dropped]`:
  raw `httpx2.RemoteProtocolError`, rather than `ConnectionFailed`.
- `test_fallback_usage_counts_every_attempt`: `(12, 5)` instead of
  `(25, 12)`, omitting the declined attempt and its cache usage.

In `frontend/`, with Node 22.17.1:

```sh
DEBUG_PRINT_LIMIT=0 npm test -- --run src/pages/Settings.test.tsx -t "restores the saved model after switching providers without a test|lists the tested models of a saved Anthropic provider|keeps the tested models out of the other provider" --reporter=verbose
```

Observed **1 failed, 2 passed, 62 skipped** in 2.49s, exit 1:

- `restores the saved model after switching providers without a test`:
  passed on the original code, as required.
- `lists the tested models of a saved Anthropic provider`: passed on the
  original code, as required.
- `keeps the tested models out of the other provider's list`: failed,
  listing the two Claude models under OpenAI-compatible instead of
  `['saved-model']`.

Ranked hypotheses after reproduction:

1. Missing raw transport-error mapping, top-level-only token accounting,
   and an unguarded late test response explain the three symptoms. The
   prescribed mapping, iteration aggregation and live-provider guard
   should fix each independently.
2. SDK conversion/merging might lose data, but the raw exceptions and
   top-level `(12, 5)` total point instead to missing adapter handling.
3. Incorrect fixtures or duplicate rendering might explain the Settings
   failure, but the exact wrong options and the two passing controls
   support the late-response explanation instead.

The green checks and isolated mutations below confirmed hypothesis 1.
The reduced tests themselves exercised the locked SDK's exception and
iteration-object behavior; no additional library assumption was needed.

### Fixes and green checks (5.2)

Re-derived the changed units from their invariants: connection failures
cross the adapter as `ConnectionFailed` without retry; usage counts every
reported billed attempt once; visible models belong to the currently
selected provider, while a successful test still saves what it tested.

- `_call` now maps `httpx2.TransportError` with the SDK connection errors.
- `chat_json` uses a non-empty iterations list when present, otherwise
  top-level usage. It reads SDK object fields with `getattr`, retains
  integer-only input/cache/output counting, and adds totals under one lock.
- Settings keeps the live provider in a ref, initializes it from saved
  settings and updates it on selection. Both visible-model setters are
  guarded; chosen/replaced computation, the no-model status and saving
  the tested configuration remain unchanged.

Commands and observed green results, all exit 0:

| Directory | Command | Result |
| --- | --- | --- |
| `backend/` | `uv run --offline pytest tests/test_anthropic_client.py tests/test_anthropic_runs.py tests/test_model_providers.py` | **58 passed, 2 warnings in 4.99s** |
| `backend/` | `uv run --offline pytest` | **1150 passed, 2 warnings in 48.54s** |
| `frontend/` | `npm test -- --run` | **324 passed in 14 files**, 8.97s |
| `frontend/` | `npm run build` | TypeScript and Vite passed, **40 modules**, 399ms |

There are three added backend cases (two parametrized stream cuts and
one usage case) and three added Settings cases. The other regression
tests pre-existed this round. The pending-response test verifies both the
automatic Anthropic save and the later OpenAI-compatible Save body.
Its mock accepts the latter body only to expose the held model value;
the real API would refuse a provider change without a new key.

### Mutations (5.3)

Saved the complete uncommitted `git diff --binary --no-ext-diff` after
5.1/5.2, before mutation N1. Applied each mutation alone, inspected its
result before proceeding, restored by editing, and compared the complete
Git diff with that saved baseline after every restore: **all six matched
exactly**. The temporary baseline file was removed afterward.

N1 and N2 used `uv run --offline pytest` with the named test node, `-q
--tb=short`. N3–N6 used `DEBUG_PRINT_LIMIT=0 npm test -- --run
src/pages/Settings.test.tsx -t "<named test(s)>" --reporter=dot`, with Node
22.17.1. All mutant commands exited 1 for the expected assertion/exception,
not a syntax or collection failure.

| Mutation | Change | Actual failing test(s) | Result |
| --- | --- | --- | --- |
| N1 | Remove `httpx2.TransportError` from mapping | Both `test_stream_cut_by_the_network_names_the_base_url` cases (`read-timeout`, `dropped`), raw exceptions escape | **2 failed**, 1.16s |
| N2 | Ignore iterations, always use top-level usage | `test_fallback_usage_counts_every_attempt`, `(12, 5)` instead of `(25, 12)` | **1 failed**, 1.16s |
| N3 | Remove the selected-provider guard | `keeps the tested models out of the other provider's list`, Claude options replace the saved model | **1 failed, 64 skipped**, 759ms |
| N4 | Remove page-load `setSavedModels` | `restores the saved model after switching providers without a test` and `keeps the tested models out of the other provider's list`, no model option after switching back | **2 failed, 63 skipped**, 682ms |
| N5 | Remove page-load selected-provider ref assignment | `lists the tested models of a saved Anthropic provider`, only Opus remains instead of both tested options | **1 failed, 64 skipped**, 672ms |
| N6 | Move `setModel(chosen ?? '')` outside the guard | `keeps the tested models out of the other provider's list`, second PUT sends `claude-opus-5-5` instead of `saved-model` | **1 failed, 64 skipped**, 711ms |

No mutation survived. N6 confirms that checking only the displayed select
value would miss the stale held-model defect.

### Final checks (5.4, repeat of 4.1)

All commands exited 0 after the final restore. Both npm installations used
`npm ci --offline --no-audit --no-fund`: frontend added **124** locked
packages before 5.1, extension added **120** during 5.4, both in 2s.
Node printed `v22.17.1`; all npm commands used
`export PATH="$HOME/.nvm/versions/node/v22.17.1/bin:$PATH"`.

| Directory | Command | Actual output / result |
| --- | --- | --- |
| `backend/` | `uv run --offline pytest` | **1150 passed, 2 warnings in 36.02s** |
| `frontend/` | `npm test -- --run` | **14 files passed; 324 tests passed**, 6.85s |
| `frontend/` | `npm run build` | `tsc --noEmit && vite build`, **40 modules**, built in **412ms** |
| `extension/` | `npm ci --offline --no-audit --no-fund` | **added 120 packages in 2s** |
| `extension/` | `npm test -- --run` | **7 files passed; 168 tests passed**, 1.92s |
| `extension/` | `npm run build` | `tsc --noEmit && vite build && node scripts/check-build.mjs`, **10 modules**, built in **302ms** |
| root | `DO_NOT_TRACK=1 openspec validate add-anthropic-provider --strict` | `Change 'add-anthropic-provider' is valid` |
| root | `git diff --check` | No output, exit 0 |

Frontend bundle: `index-PvC2UCdr.js` **319.26 kB**, gzip **97.84 kB**;
CSS remains **20.50 kB**, gzip **5.24 kB**. The unchanged extension build
also passed its packaged-output checker.

The two Pydantic warnings are the existing deliberately malformed usage
fixtures. The existing npm `whatwg-encoding` deprecation warning is
non-fatal. No unexpected red/green result or plan deviation occurred.
No package/lockfile, protected planning artifact, group-1–4 task content,
OpenAI client, prompt, summary/group module or extension source was changed.
No real model call, Docker/container/volume action, port 8800 access,
push, merge, tag or PR occurred. Docker smoke/live review remains with
Claude Code. Session metrics are left to Claude Code.
