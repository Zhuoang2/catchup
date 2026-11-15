# Test report: fix-focus-and-result-messages (#71, #72)

2026-11-15. Implementation started at `cb8e3d4`. Groups 1–4 were committed
as `9dde837`, `cc92a86`, `c0781de`, and `ba4e93f`, respectively. Group 5
records the final checks and the Docker results supplied by Claude Code.
`<worktree>` denotes this change's isolated checkout.

## Environment and scope

- Local Node.js: **22.17.1**, npm **10.9.2**. Every local npm invocation
  used `. "$HOME/.nvm/nvm.sh" && nvm use 22` first.
- Backend tests: **CPython 3.12.13**, pytest **9.1.1**.
- The unchanged Dockerfile uses `node:24-slim` for its frontend build and
  Python 3.12 images. The earlier Droid build reported Python **3.12.16**
  in the builder. These are separate from the local test runtimes.
- Missing frontend and extension dependencies were installed with
  `npm ci --prefer-offline`. Backend dependencies were installed from the
  local uv cache, with offline mode and Python downloads disabled.
- Tests used fetch mocks, fake Chrome APIs, and the existing backend test
  fixtures. No real provider, feed, X API, or authenticated page was used.
  Network access was limited to the permitted installs and Docker build;
  the smoke checks used their isolated local container.
- No backend implementation, options page, README, proposal, design, or
  spec delta was changed. The always-disabled first-run and no-sources
  Generate controls were left unchanged.

## Red-first evidence and passing counts

Counts include parameterized cases. Each group's required new or changed
non-guard test failed on an assertion before that group's implementation.
These are the observed test invocations, not counts inferred from the diff.

| Group | Red command and results before implementation | Green results after implementation |
| --- | --- | --- |
| 1, Settings and empty status layout | In `frontend/`: `DEBUG_PRINT_LIMIT=500 npm test -- --run src/pages/Settings.test.tsx src/styles/tokens.test.ts`. **14 failed, 57 passed (71)**: 13 Settings failures and 1 CSS failure. | **71 passed** across Settings (53) and CSS (18); full frontend suite **293 passed**, 14 files. |
| 2, Generate focus and busy styling | In `frontend/`: `DEBUG_PRINT_LIMIT=500 npm test -- --run src/pages/Home.test.tsx src/styles/tokens.test.ts`. **11 failed, 106 passed (117)**: 8 Home failures and 3 CSS failures. | **117 passed** across Home (97) and CSS (20); full frontend suite **299 passed**, 14 files. |
| 3, Sources preview focus | In `frontend/`: `DEBUG_PRINT_LIMIT=500 npm test -- --run src/pages/Sources.test.tsx`. **4 failed, 42 passed (46)**. | **46 Sources tests passed**; full frontend suite **303 passed**, 14 files; frontend build passed after the test-helper typing correction below. |
| 4, Popup status, focus, and busy controls | In `extension/`: `DEBUG_PRINT_LIMIT=500 npm test -- --run`. **17 failed, 114 passed (131)**; all failures were in popup assertions. | Full extension suite **131 passed**, 8 files; extension build passed. |

### Guards and existing checks

The following guards passed before implementation, were marked with code
comments, and were not required to fail:

- `Settings.test.tsx`: `shows the active-run refusal and keeps the confirmation`.
  A refused deletion keeps its confirmation and displays the alert.
- `popup.test.ts`: `does not move focus when the popup opens connected`.
  The active element remains `document.body` on initial connection.

The existing Home test `swaps the %s article after a run, retaining status
and focus` remained unchanged and passed. Existing first-run/no-sources
`toBeDisabled()` checks remain. Busy Generate assertions, invalid-language
and load-failure assertions, and the busy popup Add test were replaced as
the plan required, not retained with contradictory expectations.

New and updated tests use the agreed Settings, Home, Sources, CSS, and popup
seams. Frontend accessibility checks use `expectAccessible`; popup tests
retain the existing `axe` style. The final backend suite was existing
coverage, with no new backend tests or implementation changes.

### Test-authoring and validation corrections

- The first group 1 red run included a CSS matcher TypeError because an
  absent rule produced `undefined`. The test now supplies an empty string;
  the load-title check also uses a query inside its assertion. Before any
  implementation, the rerun produced the **14 assertion failures** counted
  above, with no setup or import failure.
- The first frontend build in group 3 caught four TypeScript diagnostics
  from the Settings test helper returning `Element` instead of
  `HTMLElement`. An explicit `closest<HTMLElement>` generic fixed the test
  typing without changing behavior. The rerun passed **303 tests** and the
  build; this correction is included in `c0781de`.
- Droid's earlier Docker build passed, but the smoke command was blocked
  by its execution permission level. No smoke result was claimed from that
  attempt. Claude Code subsequently completed task 5.2 as recorded below.

## Ranked hypotheses and confirmed causes

The planned causes were reproduced with the red checks above. Rankings
and confirmed causes were also recorded in each implementation commit.

| Group | Ranked hypotheses | Confirmed cause and change |
| --- | --- | --- |
| 1 | (1) Save routes errors away from Save and updates key state too late; (2) conditional controls/status regions lose focus and continuity; (3) empty status regions add layout gaps. | Field and save-bar assertions, focus checks, status identity checks, and the CSS rule assertion reproduced the issues. Save now reports locally, updates the stored-key display immediately after model save, keeps status nodes mounted, and sets post-render focus targets. |
| 2 | (1) Native disabled loses browser focus; (2) replacing the Generate screen removes its focused button; (3) disabled-only CSS misses aria-disabled controls. | Tests reproduced missing aria-disabled state, focus targets, and styling. Guarded aria-disabled controls and explicit focus handoffs address these. Native browser disabled behavior was established by the plan's probe; jsdom assertions also require `not.toBeDisabled()` rather than relying on focus alone. |
| 3 | (1) The token form disappears before preview resolves; (2) removed preview controls have no focus target; (3) the result status mounts with its message. | A deferred preview request reproduced premature form removal. Focus and identity checks reproduced the other lifecycle issues. The form now remains until the response, then focus moves to the preview heading or address; the result status stays mounted. |
| 4 | (1) Root replacement detaches the status line; (2) new views lack focus targets; (3) native disabled and missing guards break busy controls. | MutationObserver records detected status removal despite stable node identity. Focus, busy-control, and CSS assertions reproduced the remaining issues. Views now replace only `.popup-content`, choose focus targets, and guard aria-disabled buttons. |

## Final checks, task 5.1

Droid ran these against the implementation at `ba4e93f`. All exited 0.

| Directory | Command | Actual result |
| --- | --- | --- |
| `<worktree>/backend` | `UV_OFFLINE=1 UV_PYTHON=3.12 UV_PYTHON_DOWNLOADS=never uv run pytest` | **922 passed** in 30.29 seconds. |
| `<worktree>/frontend` | `npm test -- --run` | **303 passed**, 14 files. |
| `<worktree>/frontend` | `npm run build` | Passed: `tsc --noEmit` and Vite production build. |
| `<worktree>/extension` | `npm test -- --run` | **131 passed**, 8 files. |
| `<worktree>/extension` | `npm run build` | Passed: `tsc --noEmit`, Vite production build, and `scripts/check-build.mjs`. |
| `<worktree>` | `DO_NOT_TRACK=1 openspec validate fix-focus-and-result-messages --strict` | Passed: change is valid. |

The npm commands in this table used the Node 22 setup above. No coverage
percentage was measured in this run.

## Docker checks, task 5.2

**Claude Code ran task 5.2 in this worktree at `ba4e93f`.** The user supplied
the following successful results when resuming Droid. Droid records that
handoff as the task's verification and did not rerun either Docker command
in the completion run.

| Directory | Command | Reported result and executor |
| --- | --- | --- |
| `<worktree>` | `docker build -t catchup:fix-focus-local .` | Passed, Claude Code. |
| `<worktree>` | `scripts/docker-smoke.sh catchup:fix-focus-local` | Passed all **12 checks**, Claude Code; script unchanged. |

The 12 passing checks were:

1. Container healthy.
2. `GET /api/health`.
3. `GET /` returns HTML.
4. Manifest responds with the expected type.
5. `sw.js` responds with the expected type.
6. `offline.html` responds as expected.
7. Saved `zh-Hans` preference.
8. Responses refuse framing.
9. Process is non-root.
10. Database exists on the volume.
11. Image excludes `.env` and the backend source tree.
12. Preference survives restart.

Claude Code reported that the script's own EXIT cleanup left no container
or volume. No protected Docker resources were touched, no request was sent
to port 8800, and no prune, push, Git tag, or release was performed.
The requested local image build used the specified `-t` image name; it was
not published.

## Spec scenario mapping

Names below identify the test titles in the named files; `%s` denotes the
existing parameterized test title.

### `specs/user-interface/spec.md`

| Scenario | Test file and test |
| --- | --- |
| Save before choosing a model | `frontend/src/pages/Settings.test.tsx`: `links invalid model configuration %s to %s`, empty-model / Model case. |
| Server without an instance secret | `frontend/src/pages/Settings.test.tsx`: `shows the missing instance secret once in the save bar without marking a field`. |
| Settings saved | `frontend/src/pages/Settings.test.tsx`: `announces Settings saved in the status region present before Save`. |
| Model saved, other settings refused | `frontend/src/pages/Settings.test.tsx`: `shows the newly saved key and partial save when preferences cannot connect`. |
| Settings cannot be loaded | `frontend/src/pages/Settings.test.tsx`: `shows load failures above the Model provider heading`, including the document-order assertion. |
| Generate keeps focus during a run | `frontend/src/pages/Home.test.tsx`: `keeps busy Generate focusable in the %s and ignores a second activation`, both Generate-screen and run-bar cases. |
| Delete all X data with the keyboard | `frontend/src/pages/Settings.test.tsx`: `moves focus through X deletion and announces counts in the existing status region`, including Cancel and return focus. |
| X data deleted | `frontend/src/pages/Settings.test.tsx`: `moves focus through X deletion and announces counts in the existing status region`, including the heading focus and persistent counts region. |
| Save and preview on the Sources page | `frontend/src/pages/Sources.test.tsx`: `keeps Save and preview focused until the repeated preview answers, then focuses its heading`, including the mounted form while pending and persistent X-token status. |
| Confirm a source | `frontend/src/pages/Sources.test.tsx`: `focuses the empty address after Confirm source and announces in the existing status region`. |
| First digest replaces the Generate screen | `frontend/src/pages/Home.test.tsx`: `moves focus to run-bar Generate when the first digest replaces the Generate screen`. |
| Generate finds no model set up | `frontend/src/pages/Home.test.tsx`: `moves focus to model setup when focused Generate finds no model configured`. |

Additional requirement coverage includes the Base URL case of the Settings
configuration test, the linked Other-language partial-save test, both
Test-connection clearing cases, empty Settings status regions, Disconnect
focus/status identity, X-token status identity, Sources preview failure and
Cancel focus, and `frontend/src/styles/tokens.test.ts` checks for empty
status layout, separate busy button styles, and hover exclusions.

### `specs/browser-extension/spec.md`

All tests in this table are in `extension/src/test/popup.test.ts`.

| Scenario | Tests |
| --- | --- |
| Save a page with the keyboard | `focuses Add after saving and removing a page`; `keeps one status line attached while saving, removing, previewing, and following`; `keeps busy Add focusable, ignores another click, and shows a run_active conflict`. |
| Preview and cancel | `focuses the preview heading, then Follow this %s after Cancel and Confirm`, site and account cases. |
| One status line | `keeps one status line attached while saving, removing, previewing, and following`, including identity after each step and MutationObserver records plus `takeRecords()` showing no removal of the status element. |

Additional popup requirements are covered by the token-field and post-token
preview-heading focus tests; the five 401 action cases (Add, Remove, Follow,
Confirm, Save); the initial-focus guard; the busy Remove and X-token Save
tests; and the three CSS checks for busy appearance, hover exclusions, and
the content-container grid/host selectors.

## Review limits and leftovers

jsdom cannot verify actual browser layout, native disabled focus behavior,
or screen-reader speech. The plan assigns real keyboard/browser checks to
Claude Code at review. No such checks or screen-reader review are claimed here.
Docker smoke verifies the running packaged application, not those
interactive focus and announcement details.

Nothing was deleted manually. Generated worktree directories left for
review are `<worktree>/backend/.pytest_cache`, `<worktree>/backend/.venv`,
`<worktree>/frontend/node_modules`, `<worktree>/frontend/dist`,
`<worktree>/extension/node_modules`, and `<worktree>/extension/dist`.
The local image `catchup:fix-focus-local` and Docker build cache remain.
No temporary helper scripts were created.
