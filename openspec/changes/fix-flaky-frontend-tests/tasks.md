# Tasks

Implementer notes:
- **Read first.** Read `proposal.md`. There are no spec deltas and no design document. If something looks wrong, stop and report.
- **Use the `tdd` skill.** The flakes cannot be reproduced on demand, so each red step is a named temporary mutation of the runtime code that makes the race certain, applied by hand:
  1. Apply the mutation, and see the **current** assertion fail.
  2. Change the test, and see it pass with the mutation still applied.
  3. Revert the mutation, and see the test pass again.

  Record each check, its mutation, and the failing result in the report. Before each commit, `git diff` must show only test files and docs.
- **Test rules.** Mock `fetch` as the existing tests do. Keep the existing fake-timer setup (`vi.useFakeTimers({ shouldAdvanceTime: true })`), with which `waitFor` works. Add no new real timers to the tests.
- **Out of scope:**
  - any change to runtime code, including moving effects to `useLayoutEffect`;
  - the assertions that `proposal.md` lists as already safe.
- **Commits.** Commit after each task. Do not push, tag, or open a PR.

## 1. Wait for effect-driven state

- [x] 1.1 **Titles** (`frontend/src/pages/DigestView.test.tsx:185`, and `frontend/src/pages/Home.test.tsx:130, 150, 377, 406, 631, 920, 1054`). Change each `expect(document.title).toBe(...)` to `await waitFor(() => expect(document.title).toBe(...))`. Import `waitFor` where it is missing.

  Mutation: in `frontend/src/components/useDocumentTitle.ts`, set the title inside `setTimeout(() => { … }, 50)`.

  Verify:
  - under the mutation, each of the eight current assertions fails, and each changed one passes;
  - after the revert, `npm test -- --run src/pages/DigestView.test.tsx src/pages/Home.test.tsx` passes.

  If one of the eight still passes under the mutation, say so in the report and explain why, for example because the previous test left the same title.
- [x] 1.2 **Focus after a deletion** (`frontend/src/pages/Sources.test.tsx:230, 268`). Change each `expect(document.activeElement).toBe(...)` to `await waitFor(() => expect(document.activeElement).toBe(...))`, as line 247 already does.

  Mutation: in `frontend/src/pages/Sources.tsx`, inside the `focusAfterDelete` effect, call `focus()` inside `setTimeout(() => { … }, 50)`.

  Verify:
  - under the mutation, both current assertions fail, and both changed ones pass;
  - after the revert, `npm test -- --run src/pages/Sources.test.tsx` passes.

## 2. The icon test's timeout

- [x] 2.1 In `frontend/src/install.test.ts`, give "regenerates byte-identical icons in a temporary directory" an explicit timeout of `30_000` ms, as the third argument of `it`.

  Red check, before the change: start 6 full runs of `npx vitest run` in parallel from `frontend/`, and record how many of them fail this test with "Test timed out in 5000ms". Planning saw 18 of 18.

  Verify: after the change, the same 6 parallel runs all pass. Record the counts.

## 3. Checks and docs

- [x] 3.1 **Stress check.** Run 3 rounds of 6 parallel full `npx vitest run` from `frontend/`. Record the pass and fail counts per round. If any test fails, report its name and error, and stop before 3.2. Do not raise any other timeout to make it pass.

  Verify: all 18 runs pass.
- [x] 3.2 **Docs and final checks.**
  - Write `docs/process/test-report-fix-flaky-frontend-tests.md`: the cause of each flake, each mutation and its red and green results, the parallel-run counts from 2.1 and 3.1, and the assertions left alone with the reason for each, from `proposal.md`.
  - Add this change's line to `docs/process/coverage-summary.md`.
  - Run `npm run build` and `npm test -- --run` in `frontend/`, `uv run pytest` in `backend/`, and `openspec validate fix-flaky-frontend-tests --strict`.
  - Add your entry to `docs/process/ai-usage-log.md` after the latest entry, with a faithful excerpt of the prompt you actually received, and the tool and model. Leave out the session id.

  Verify: every command passes, and the report has the actual numbers.

## 4. Fix round 1 (review findings)

The review found two more gaps of the same kind, and one unneeded change. Keep the rules above: tests only, a named red step for each check, and a commit after each task.

- [x] 4.1 **Reset the title between tests** (`frontend/src/test/setup.ts`). Today `document.title` carries over from one test to the next. A title check can therefore pass on the title that an earlier test left: under the 1.1 mutation, `Home.test.tsx:130` passed in the full file for this reason.

  Test first: add `frontend/src/test/setup.test.ts` with two tests in order. The first sets `document.title = 'Left by an earlier test'`. The second expects `document.title` to be `''`. See the second fail. Then set `document.title = ''` in a `beforeEach` in `setup.ts`, and see it pass.

  Verify: `npm test -- --run` passes. If a test relied on a title left by another test, report it and fix that test.
- [x] 4.2 **Wait for the poll timer before advancing time** (`frontend/src/pages/Home.test.tsx`). The poll `setInterval` (`Home.tsx:170`) is registered in a `useEffect`. Many tests `await findBy…` and then advance the fake clock at once. Right after the `findBy`, no poll timer is registered yet: on review, `vi.getTimerCount()` was 0 there in "keeps a startup latest-digest error visible through successful progress polls". The tests pass only because `advanceTimersByTimeAsync` yields once before it ticks.
  - Add a helper that waits until a 1000 ms interval has been registered, for example by spying on `window.setInterval` and waiting for a call whose delay is 1000. Do **not** use `vi.getTimerCount()` inside `waitFor`: `waitFor` registers its own timers, so the count is never 0 while it waits.
  - Call the helper before the first `advanceTimersByTimeAsync` of each test that expects a poll. Later advances do not need it: when the run status changes, the effect clears the old interval and registers a new one in the same flush, so an interval is always registered.

  Red step: in one of these tests, add a temporary assertion right after the `findBy` that a 1000 ms interval is registered. See it fail on the current code. Then call the helper before the assertion, and see it pass. Remove the temporary assertion.

  Verify: `npm test -- --run src/pages/Home.test.tsx` passes. Name in the report every test that now calls the helper. If the spy does not work with the fake timers, stop and report.
- [ ] 4.3 **Undo the unneeded change** at `Home.test.tsx:406` (old numbering), "keeps the previous article and links to the new edition when detail loading fails". The title does not change in that test, so it goes back to the synchronous `expect(document.title).toBe('Latest · No. 4 · CatchUp')`.

  Verify: the test passes.
- [ ] 4.4 **Checks and docs.**
  - **Stress check:** rerun 3 rounds of 6 parallel full `npx vitest run` from `frontend/`, and record the counts.
  - **`docs/process/test-report-fix-flaky-frontend-tests.md`:**
    - Add a "Fix round 1" section, with the red and green results of 4.1 and 4.2, and the stress counts.
    - Correct the reason given for `ui.test.tsx:60`: focus is set in the click handler (`useJump`), not by an effect that `fireEvent` flushes.
    - Add `App.test.tsx:21` (a title right after `render`) and `App.test.tsx:63` (focus set by a handler) to the assertions left alone.
  - **`docs/process/coverage-summary.md`:** add a fix-round line.
  - **Final checks:** run `npm run build`, `npm test -- --run`, and `openspec validate fix-flaky-frontend-tests --strict`.
  - **`docs/process/ai-usage-log.md`:** add a fix-round entry after the latest entry, with a faithful excerpt of the prompt you actually received, and the tool and model. Leave out the session id.

  Verify: every command passes, and the report has the actual numbers.
