# Save model after test: implementation checks

2026-11-06, branch `save-model-after-test`, starting commit `cd2dc16`.
Implementation commits: `953f8cf` (group 1), `92804ce` (group 2).
Commands below ran in this worktree, not the user's running instance.

## Commands and actual results

Frontend commands ran from `frontend/`; backend commands from `backend/`;
OpenSpec and Docker commands from the repository root.

| Command / stage | Actual result |
| --- | --- |
| `npm ci` | Installed 124 packages; audit reported 0 vulnerabilities. |
| `npm test -- --run src/pages/Settings.test.tsx`, before group 1 implementation | Expected red: **11 failed, 23 passed** (34 total). Nine new tests failed for missing save requests, messages, group alerts, hint text, or the persistent status region. The failed-test guard passed. The two deliberately updated existing tests failed for the old message and missing automatic PUT. No mock errors caused these failures. |
| Same command, after group 1 | **34 passed**. |
| `npm test -- --run`, after group 1 | **273 passed in 14 files**. |
| `npm run build`, after group 1 | Passed TypeScript and Vite; **40 modules** transformed. |
| `npm test -- --run src/pages/Settings.test.tsx`, before group 2 implementation | Expected red: **3 failed, 37 passed** (40 total). Choice-save, ordered-save, and failure-recovery tests failed for missing requests or the missing failure alert. All three edited-field/unsaved-state guards passed. |
| Same command, after group 2 | **40 passed**. |
| `npm test -- --run`, after group 2 and again for final integration | **279 passed in 14 files**, on both runs. |
| `npm run build`, after group 2 and again for final integration | Passed TypeScript and Vite on both runs; **40 modules** transformed. |
| `uv run pytest`, initial environment | Exit 2 during collection: Python **3.11.4** rejected an existing f-string in `tests/test_discovery.py:259` (`f-string expression part cannot include a backslash`); 797 items collected before the collection error. No backend files were changed. |
| `UV_PYTHON=3.12 uv run pytest` | **885 passed in 36.66s**, using the installed Python 3.12 interpreter, matching the Docker image's Python version. |
| `DO_NOT_TRACK=1 openspec validate save-model-after-test --strict` | Passed: change is valid. |
| `docker info --format '{{.ServerVersion}}'` | Docker daemon available, version **29.8.0**. |
| `docker build -t catchup:save-model-after-test-local .` | Passed. |
| `scripts/docker-smoke.sh catchup:save-model-after-test-local` | Passed all 12 reported checks: health, API, HTML, manifest, service worker, offline page, preference write, framing headers, non-root process, database volume, excluded source/secrets, and preference persistence after restart. The script removed its own container and volume. |
| `test -f docs/process/test-report-save-model-after-test.md`, before writing this report | Expected red: exit 1, report absent. |

## Guard mutations

Each mutation was applied alone, its targeted test was run with
`npm test -- --run src/pages/Settings.test.tsx -t "<test name>"`, and the
mutation was restored. Every targeted run exited 1 with **one failed test**.
The full green suites and builds above ran after restoration.

| Mutation | Target test | Observed failure |
| --- | --- | --- |
| Run an automatic PUT in the test-request catch, even after rejection | `does not save a failed test and links the rejection to the key` | One model PUT instead of none. |
| Remove the empty-key condition from the model-choice guard | `waits to save a model choice when the key was edited` | Two model PUTs instead of one. |
| Remove the base-URL comparison from the model-choice guard | `waits to save a model choice when the base URL was edited` | Two model PUTs instead of one. |
| Set `savedBaseUrl` from GET even when `key_set` is false | `does not save a choice when no configuration has ever been saved` | An extra PUT after the failed initial save. |
| Set `savedBaseUrl` in the automatic-save failure path | Same unsaved-configuration test | An extra PUT after the failed initial save. |
| Start each automatic save directly instead of chaining it | `saves quick successive model choices in order` | `live-c` was sent while the deferred `live-b` PUT was still open. |

The corrected plan's two unsaved-state mutations were both killed. The
equivalent `savedBaseUrl !== null` mutation was not reintroduced.

## Spec scenario mapping

New tests are in `frontend/src/pages/Settings.test.tsx` unless another file is
named. There are **16 new Settings tests** and **two updated existing tests**.
They use the agreed global-fetch/UI boundary, separate GET and PUT handling,
request-body echoes, and deferred promises without real network or sleeps.
Existing accessibility checks remain; first-setup coverage adds one.

| Delta scenario | Test / evidence |
| --- | --- |
| Valid credentials | Existing backend `test_can_test_unsaved_key_and_list_provider_models` and `test_lists_provider_models`; the former also proves POST alone saves nothing. |
| Invalid key | Existing Settings `explains authentication errors`; new `does not save a failed test and links the rejection to the key`; existing backend `test_provider_errors_are_safe` authentication case. |
| Unreachable provider | Existing Settings `links a connection failure to the base URL instead of the key`; backend `test_provider_errors_are_safe` connection case, `test_connection_timeout`, and `test_lists_provider_models` (15-second timeout settings). |
| First setup is saved by the test | `saves first setup with the fallback model without saving preferences`. |
| Main screen after only a test | Existing Home `offers %s / %s guidance while keeping a saved digest` covers the `key_set` setup gate; `shows the latest article and one compact action above its headline without a rail` covers the ready primary action. Settings first-setup verifies the separate save. The cross-page live check below is **not performed**. |
| Testing a new key replaces the saved key | `replaces the saved key while keeping a listed selected model`. |
| Test with the saved key | `keeps the saved key when testing with an empty key field`. |
| Failed test saves nothing | `does not save a failed test and links the rejection to the key`, plus its mutation. |
| Provider lists no models | `saves nothing and explains when the provider lists no models`. |
| Saving fails after a successful test | `reports a save failure in the model group and keeps the entered key`. |
| Choosing another model saves it | `saves another model choice immediately after a test`. |
| Edited fields wait for a test | `waits to save a model choice when the key was edited` and `waits to save a model choice when the base URL was edited`, plus their mutations. |
| Quick successive choices | `saves quick successive model choices in order`, plus the queue mutation. |
| Key hint names the new behavior | `explains that testing a new key saves it in the saved-key hint`. |

Additional design coverage: `saves the tested values without clearing a key
typed while testing` also edits the base URL while POST is pending;
`shows test errors without a field in the model group, not at the bottom`
checks error placement; `keeps the same status region mounted before and after
a test` checks node identity. The unsaved-configuration test and
`keeps a failed model choice and saves a later choice after a rejected fetch`
cover saved-state initialization and queue recovery. Existing
`shows the first-run key hint and saves preferences without exposing the key`
now expects automatic model PUT, explicit model PUT, then preferences PUT.

## Review checks not performed

Claude Code must run the design's manual live check on an isolated test
instance, **not port 8800**, with a stub OpenAI-compatible provider and a fake
key:

1. Test only, then confirm Home offers Generate with one source, without Save.
2. Choose another model, reload Settings, and confirm it persisted.
3. Test with a rejected key and confirm the saved configuration is unchanged.

The Docker smoke check does not replace this browser/live flow or verify
screen-reader announcements. No external provider, real key, hosted service,
extension, or X-account flow was exercised. No new statement-coverage
measurement was taken; backend and extension code are unchanged.

## Claude Code review (2026-11-06)

Review of `cd2dc16..2b22004` (Droid run 2, session `420b5b68-fba4-4561-b55c-449e73d2a830`), in a separate worktree. Droid's first run (session `1ccaa6a3-b1c8-47e7-80cc-ca3cabdc78fc`) stopped before coding, because the plan asked for an equivalent mutation; the plan was corrected in `cd2dc16`.

### Checks re-run by Claude Code

| Check | Result |
| --- | --- |
| `npx vitest run` (frontend) | First run after `npm ci`: **1 failed, 278 passed**; the failing test name was not captured. The next 13 full runs passed **279/279**, 8 of them as 4 parallel suites. Recorded as an unidentified one-off flake. |
| Same, after the review tests below | **281 passed** (Settings: 42). |
| `npm run build` | Passed. |
| `uv run -p 3.12 pytest -q` (backend, unchanged) | **885 passed**. |
| `docker build -t catchup:review-85 .` and `scripts/docker-smoke.sh catchup:review-85` | Passed (all PASS lines). |
| `DO_NOT_TRACK=1 openspec validate save-model-after-test --strict` | Valid (also re-run by the spec reviewer). |

### Live check (performed)

On an isolated container (`catchup:review-85`, port 8786, a random secret passed by process substitution), with a stub OpenAI-compatible provider on the host that accepts only fake keys. One public feed (Simon Willison's Weblog) was added as the source. The user's instance on port 8800 was not touched.

1. **Rejected key.** In Settings, a fake rejected key and the stub's base URL were entered, and Test connection was clicked. The server log shows one `POST /api/settings/model/test` (401) and no PUT. `GET /api/settings/model` still reported `key_set: false`. The page showed "The provider rejected the API key." at the key field.
2. **Test only.** With a fake accepted key, Test connection showed "Connection succeeded. Saved key ending in 1111 with model stub-a. Choose another model to change it." The log shows the 200 test and one `PUT /api/settings/model` (200), and the API reported `stub-a`, `key_set: true`. Save was not clicked. Home then offered **Generate digest** as its action, and "Set up your model" was gone.
3. **Model choice.** Choosing `stub-b` showed "Saved model stub-b." and sent one more PUT. After reloading Settings and Home, the API still reported `stub-b`.

The container log contained no part of the fake keys. Screen-reader announcements were not checked with a screen reader; the tests check that the status region stays mounted.

### Findings and outcomes

`/code-review` (6 findings) and an independent spec reviewer (42 mutations: 25 killed, 4 equivalent, 7 real test gaps, 6 marginal) found no real defect in behavior. Each finding was checked against the code.

- **Fixed in the review commit (test-only gaps, each verified by a named mutation that now fails a test):**
  - M23: a model choice after a **first-setup** test (`savedBaseUrl` comes from the automatic save's response, not from GET). Every earlier choice test started from a saved key. New test: `saves a model choice after a first-setup test`.
  - M39: keeping a listed selection was tested only when it was listed first. `replaces the saved key while keeping a listed selected model` now lists it second.
  - M21: the no-models message is now asserted in the model group's status region, not by any element's text.
  - M08: a fallback when only one model is listed has no "Choose another model" sentence. New test: `does not offer another model when the fallback is the only listed model`.
  - M16a: a failed model choice clears the earlier success message (assertion added to the rejected-fetch test).
- **Recorded, not fixed:**
  - Plan gap, low (`/code-review` 1, spec reviewer §3). If the menu changes while a test or its automatic save is running, the user's pick is not kept.
    - During the test, the save sets the menu back to the saved model, as D2 intends.
    - During the save's own PUT, which takes milliseconds locally, a pick while the new key is still in the field leaves the menu showing a model that was not saved.
    - M22 (menu always set to the saved model) has no test for the same reason.
  - The bottom **Save** sends its PUT outside the queue (`/code-review` 2). It usually carries the same model as a pending choice save.
  - The no-models message uses the success style and check icon of the status region (`/code-review` 3). The design puts it there.
  - An empty model list clears the selection, so a later **Save** sends an empty model ID and shows the error at the bottom of the page (`/code-review` 4). This behavior existed before; it is #71's area.
  - The status still reads "Saved …" while the user edits the key or base URL afterwards (`/code-review` 5). The spec accepts that these edits wait for a test.
  - M24 (`savedBaseUrl` set by the bottom Save) is not tested, and neither are the marginal M13 and M25–M30.
  - Equivalent mutations: M15 and M18 (the queue's second `then` argument is unreachable, because each save catches its own errors), and M35 and M38 (whitespace in the base URL, which the server strips). So the "queue recovery" test shows that a later choice still saves after a failed one, not that the second argument matters.
  - Simplification (`/code-review` 6): the remaining `message` state and the `showError` flag. Churn; skipped.

Mutation details: `scratchpad/mutation-results-85.txt` from the spec reviewer (not committed).
