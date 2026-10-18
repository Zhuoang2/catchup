# Tasks

Implementer notes:
- **Read first.** Read `proposal.md`, `specs/user-interface/spec.md`, and `specs/digest-generation/spec.md`. There is no design document. If something looks wrong or contradictory, stop and report instead of redesigning.
- **Work test-first with the `tdd` skill** (D-016). Write the tests in 1.1, watch them fail, then make them pass in 1.2. The seam is the rendered main screen in `frontend/src/pages/Home.test.tsx`: use its `mockPage` helper with a mocked `/api/digest-runs/active` run.
- **Needs attention** means a check with `status === 'failed'`, which includes rate-limited checks, or with `possible_gap === true`.
- **Test rules.** Mock `fetch` as the existing tests do. Use no real timers, and run `expectAccessible` on each new rendered state.
- **Out of scope:**
  - the backend and the run API (`source_checks` keeps every source)
  - the Sources page
  - CSS
  - the list shown while a run is active
  - the status-region announcements
- **Commits.** Commit after each task group. Do not push, tag, or open a PR.

## 1. Main screen: only sources that need attention after a run

- [x] 1.1 In `frontend/src/pages/Home.test.tsx`, add failing tests. Each uses three checks: `News`, failed with error `offline`; `Blog`, `new_items` with `possible_gap: true`; and `Docs`, `no_new_items` with no gap. Each case also has a variant where all three are fine: `News` and `Blog` change to `new_items` without a gap.
  1. **Saved digest, run bar.**
     - The latest digest is shown, and the run has `succeeded`.
     - The `Digest run` region lists `News` with "Failed" and "offline", and `Blog` with "Possible gap", under the label "Needs attention". It does not contain `Docs`.
     - In the all-fine variant, the region has no `.check-list`, and no element in it has the exact text "Needs attention" or "Sources". The result line still says "3 sources".
  2. **No new content, run bar.** The run has `no_new_content`, with `News` rate limited (`rate_limited: true`, `http_status: 429`) and `Docs` fine. The region shows `News` as "Rate limited · try later", and does not list `Docs`.
  3. **Failed run, run bar.** The run has `failed`, with `error_kind: 'run_failed'`. The region lists `News` and `Blog`, but not `Docs`. In the all-fine variant, it shows no source list.
  4. **No-digest layout.** There is no latest digest, so the result card is shown. Repeat case 1 there, with both variants. The heading is "Needs attention".
  5. **During a run, unchanged.** The run is `collecting`, and all three checks are present. The region lists all three, under the label "Sources".

  Keep the existing after-run tests passing. Where one asserts a source that no longer needs attention, change its fixture rather than its intent, and name each change in the report.

  Verify: cases 1–4 fail before 1.2. Case 5 passes before 1.2, as a guard; the report says so.
- [x] 1.2 Implement this in `frontend/src/pages/Home.tsx`:
  - For ended runs (`succeeded`, `no_new_content`, `failed`), `RunStateContent` passes only the checks that need attention to `SourceChecks`.
  - `SourceChecks` takes a label: "Needs attention" for ended runs, and "Sources" while a run is active. Keep its heading level (an `h2` in the card, a `p.section-label` in the compact bar), its chips, its error text, and its "render nothing for an empty list" behavior.

  Verify:
  - The 1.1 tests pass.
  - `npm test -- --run` passes in `frontend/`.
  - `npm run build` passes in `frontend/`.

## 2. Checks and report

- [ ] 2.1 Run the full checks:
  - `npm run build`, then `npm test -- --run`, in `frontend/`
  - `uv run pytest` in `backend/`, to confirm that nothing outside the frontend changed
  - `openspec validate show-attention-sources-after-run --strict`

  Write the commands and their real results to `docs/process/test-report-show-attention-sources-after-run.md`. Include the red-first results of 1.1, and any existing test whose fixture changed. Name the manual check that was not performed: a real run on a local instance.

  Add your entry to `docs/process/ai-usage-log.md` after the latest entry, with a faithful excerpt of the prompt you actually received, and the tool and model. Leave out the session id; Claude Code adds it at review.

  Verify: every command passes, and the report has the actual numbers.
