# Proposal

## Why

Several frontend tests fail now and then and pass on a rerun (#52). One of them kept PR #51 from merging. Any PR can hit them, which also blocks auto-merge.

- **Effect-driven state checked too early.** `document.title` is set in `useDocumentTitle`'s `useEffect`. Focus after a deletion on Sources is also moved in a `useEffect`. Ten assertions read this state synchronously, right after an async wait (`findBy…` or `waitFor`) on the DOM or on fetch calls. That wait returns as soon as the DOM matches. On a slow runner, React can still have the passive effect pending, so the title or the focus has not changed yet.
  - CI on PR #51 failed at `Sources.test.tsx:268`: `activeElement` was `<body>`.
  - `DigestView.test.tsx:185` failed once locally, in about 30 full runs.
  - `Home.test.tsx:130` failed once under load.
- **A subprocess test under the default timeout.** `install.test.ts`, "regenerates byte-identical icons in a temporary directory", runs `python3 scripts/make-icons.py`. That takes 0.42 s alone, under vitest's default 5 s timeout. With 6 parallel full-suite runs on the development machine, it timed out in 18 of 18 runs.

The timing failures could not be reproduced on demand: 40 stressed runs of those test files all passed. The fix is therefore proved by a named temporary mutation that delays each effect.

## What Changes

- **Wait for effect-driven state.** Wrap the ten assertions in `await waitFor(...)`:
  - `DigestView.test.tsx:185`;
  - `Home.test.tsx:130, 150, 377, 406, 631, 920, 1054`;
  - `Sources.test.tsx:230, 268`.
- **Leave alone** the assertions that are already safe:
  - those right after `fireEvent`, which runs inside `act` and flushes effects (`Sources.test.tsx:220, 224, 226`);
  - focus set in a click handler (`ui.test.tsx:60`, `DigestView.test.tsx:314`, and `App.test.tsx:63`; corrected at review: `ui.test.tsx:60` was first listed under `fireEvent`);
  - a title read right after `render`, which runs inside `act` (`App.test.tsx:21`; added at review);
  - a title that does not change (`DigestView.test.tsx:137, 139`);
  - the check that focus stayed where the user put it (`Home.test.tsx:382`). Waiting cannot make a "did not move" check fail.
- **Give the icon test an explicit timeout** of 30 s.
- **No change** to runtime code, behavior, or specs, so `skip_specs: true` is set.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- None. Tests only; `skip_specs: true` is set in `.openspec.yaml`.

## Impact

- Test files only: `frontend/src/pages/DigestView.test.tsx`, `frontend/src/pages/Home.test.tsx`, `frontend/src/pages/Sources.test.tsx`, `frontend/src/install.test.ts`.
- A test report, a coverage-summary line, and an AI usage log entry in `docs/process/`.
