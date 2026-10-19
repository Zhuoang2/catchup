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

- [x] 2.1 Run the full checks:
  - `npm run build`, then `npm test -- --run`, in `frontend/`
  - `uv run pytest` in `backend/`, to confirm that nothing outside the frontend changed
  - `openspec validate show-attention-sources-after-run --strict`

  Write the commands and their real results to `docs/process/test-report-show-attention-sources-after-run.md`. Include the red-first results of 1.1, and any existing test whose fixture changed. Name the manual check that was not performed: a real run on a local instance.

  Add your entry to `docs/process/ai-usage-log.md` after the latest entry, with a faithful excerpt of the prompt you actually received, and the tool and model. Leave out the session id; Claude Code adds it at review.

  Verify: every command passes, and the report has the actual numbers.

## 3. Fix round 1 (test gaps from review)

Review found no wrong behavior. It did find:
- one spec wording problem, which Claude fixed in the user-interface delta: a rate-limited source is shown as rate limited in place of its error;
- ten mutations that the tests do not catch;
- four near-identical test blocks.

This group changes only `frontend/src/pages/Home.test.tsx` and the docs. Do not change `Home.tsx`. The code is already correct, so the red step for each new check is a named temporary mutation of `Home.tsx`, applied by hand:
1. Write the check and see it pass.
2. Apply the mutation, and see the check fail.
3. Revert the mutation, and see the check pass again.

Record each check, its mutation, and the failing result in the report.

- [ ] 3.1 Replace the four ended-run blocks added in 1.1 with one `it.each` table. Use the same three checks (`News` failed with error `offline`, `Blog` with a possible gap, `Docs` fine) and the all-fine variant. The table covers every combination of:
  - **status:** `succeeded`, `no_new_content`, and `failed` (`error_kind: 'run_failed'`);
  - **layout:** the compact run bar, with a latest digest shown, and the result card, with no digest;
  - **variant:** needs attention, and all fine.

  That makes 12 rows. Use one shared set of assertions:
  - **Needs attention:**
    - The label "Needs attention" is a `P` element with class `section-label` in the compact bar, and a level-2 heading in the card.
    - There are exactly two rows.
    - The `News` row has "Failed" and "offline".
    - The `Blog` row has "Possible gap".
    - The region does not contain `Docs` anywhere.
  - **All fine:** there is no `.check-list`, and no element in the region has the exact text "Needs attention" or "Sources".
  - **For `succeeded`:** the result line (`.result-meta`) contains "3 sources".

  Named mutations, each to be seen failing:
  - In the `succeeded`/`no_new_content` branch, pass `run.source_checks` when `!compact`. Seen failing for the `no_new_content` card rows.
  - The same in the `failed` branch. Seen failing for the `failed` card rows.
  - Use the label "Sources" when `!compact`, in each of those two branches.
  - Render the ended compact label as an `h2`.
  - Make the result line count only the checks that need attention.
  - In the `no_new_content` branch, hide error text.

  Verify:
  - All 12 rows pass on the current code.
  - Each named mutation fails at least one row.
  - Every mutation is reverted: `git diff` shows only the test file.
- [ ] 3.2 Add two more tests, each with its named mutation:
  1. **During a run, compact.** A latest digest is shown, and the run is `collecting` with the three checks. The run bar lists all three under a `P` label "Sources". Mutation: use "Needs attention" as the active-run label when `compact`.
  2. **A rate-limited row.** A `no_new_content` run, in the compact bar. `News` has `status: 'failed'`, `rate_limited: true`, `http_status: 429`, and the error "The source is rate limiting requests. Try again in about 120 seconds." The row shows "Rate limited · try later", and does not contain the error text. Mutation: show `check.error` for rate-limited checks too.

  Verify: both tests pass, each mutation fails its test, and the mutations are reverted.
- [ ] 3.3 Run `npm run build` and `npm test -- --run` in `frontend/`, and `openspec validate show-attention-sources-after-run --strict`. Add a "Fix round 1" section to `docs/process/test-report-show-attention-sources-after-run.md`:
  - the real results;
  - the mutation table from 3.1 and 3.2;
  - the test count before and after the restructuring.

  Add a fix-round entry to `docs/process/ai-usage-log.md` after the latest entry, with a faithful excerpt of the prompt you actually received, and the tool and model. Leave out the session id.

  Verify: every command passes, and the report has the actual numbers.
