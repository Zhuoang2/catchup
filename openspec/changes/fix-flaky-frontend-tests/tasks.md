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

- [ ] 2.1 In `frontend/src/install.test.ts`, give "regenerates byte-identical icons in a temporary directory" an explicit timeout of `30_000` ms, as the third argument of `it`.

  Red check, before the change: start 6 full runs of `npx vitest run` in parallel from `frontend/`, and record how many of them fail this test with "Test timed out in 5000ms". Planning saw 18 of 18.

  Verify: after the change, the same 6 parallel runs all pass. Record the counts.

## 3. Checks and docs

- [ ] 3.1 **Stress check.** Run 3 rounds of 6 parallel full `npx vitest run` from `frontend/`. Record the pass and fail counts per round. If any test fails, report its name and error, and stop before 3.2. Do not raise any other timeout to make it pass.

  Verify: all 18 runs pass.
- [ ] 3.2 **Docs and final checks.**
  - Write `docs/process/test-report-fix-flaky-frontend-tests.md`: the cause of each flake, each mutation and its red and green results, the parallel-run counts from 2.1 and 3.1, and the assertions left alone with the reason for each, from `proposal.md`.
  - Add this change's line to `docs/process/coverage-summary.md`.
  - Run `npm run build` and `npm test -- --run` in `frontend/`, `uv run pytest` in `backend/`, and `openspec validate fix-flaky-frontend-tests --strict`.
  - Add your entry to `docs/process/ai-usage-log.md` after the latest entry, with a faithful excerpt of the prompt you actually received, and the tool and model. Leave out the session id.

  Verify: every command passes, and the report has the actual numbers.
