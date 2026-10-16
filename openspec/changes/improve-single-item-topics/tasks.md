# Tasks

Implementer notes:
- **Read first.** Read `proposal.md`, `design.md` (D1–D5), and `specs/user-interface/spec.md` before starting. If something looks wrong or contradictory, stop and report instead of redesigning.
- **Work test-first with the `tdd` skill** (D-016). For each task, first write its verification items as failing tests and watch them fail, then implement until they pass. The seams to test are the ones named in each task; they count as agreed.
- **Test rules.** Tests make no real network calls (mock `fetch` in vitest), use no real sleeps, and write nothing outside temp dirs.
- **Out of scope:**
  - the backend
  - the grouping prompt (Option G, a later change)
  - the topic column's width
  - the Creator updates layout (`frontend/src/styles/layout.css:30-33`)
  - the run bar
  - the order or content of an item's markup
- **Commits.** Commit after each task group. Do not push, tag, or open a PR.

## 1. One item layout in the markup

- [x] 1.1 In `frontend/src/pages/DigestView.test.tsx`, write the failing tests first:
  - Replace the length-based class assertions (`:234-235`) and the 140/141-character test (`:250-264`) with one test. It renders a topic with four items: a summary with "- " key points, a 141-character summary, a 140-character summary, and a "Summary unavailable" item.
  - The test checks that each item is an `article` whose class list is exactly `item`, with no `item-long` or `item-short`.
  - It also checks each item's children in DOM order: `p.item-meta`, then `h3.item-title`, then `div.summary` or `p.summary-unavailable`.
  - Keep the rest of the Chinese test at `:218-248`: `lang` marks, key points as a list, the index, focus, and `expectAccessible`.

  Verify: the new test fails before 1.2, because the classes are still rendered.
- [x] 1.2 In `frontend/src/components/DigestArticle.tsx:67-68`, remove the `wide` computation and render `className="item"`. The markup is otherwise unchanged.

  Verify:
  - The 1.1 test passes.
  - Every other `DigestView.test.tsx`, `DigestArticle.test.tsx`, and `Home.test.tsx` test passes unchanged, including "shows the same digest reading markup on Home and the saved digest page".
  - `npm test -- --run` passes.

## 2. Item row layout and the style audit

- [x] 2.1 In `frontend/src/styles/tokens.test.ts`, add failing CSS assertions on `layout.css` (design D1–D4):
  - `.items > .item` spans `1 / -1`, uses `grid-template-columns: subgrid`, and has rows `auto auto 1fr`.
  - `.item-meta` and `.item-title` inside an item take `1 / span 3`.
  - `.summary` and `.summary-unavailable` inside an item take `4 / -1` and span all rows (`1 / -1`).
  - Consecutive items are separated by a top rule (`border-top: 1px solid var(--border)`), with no `border-left` rule between items.
  - `layout.css` no longer contains `.item-long`, `.item-short`, or `.item:only-child`.
  - Inside `@container (max-width: 900px)`, the item is one column (`grid-template-columns: minmax(0, 1fr)`), and its children reset to `grid-column: 1 / -1` and `grid-row: auto`.

  Verify: the new assertions fail before 2.2.
- [x] 2.2 Implement the placements in `frontend/src/styles/layout.css` (`:23-29` and the 900 px block at `:65-68`), following design D1–D4.
  - Remove the length, `:only-child`, long-after-long, and vertical-rule rules.
  - Keep `.topic > .items` (`:23`) and the topic column (`:22`) as they are.
  - Adjust `frontend/src/styles/components.css:112` (`.item` gap) only if the subgrid needs it.

  Verify: the 2.1 assertions pass, and `npm test -- --run` and `npm run build` pass.
- [x] 2.3 Update the style audit (design D5):
  - In `frontend/scripts/check-style-coverage.py`, add `item-long` and `item-short` to `PROTOTYPE_ONLY`, each with a reason, because the archived C7 prototype still uses them.
  - In `frontend/scripts/test_check_style_coverage.py`, assert the new entries, as for `.hero-last`.

  Verify: first run `python3 frontend/scripts/check-style-coverage.py` without the new entries and note that it fails. Then add them, and both that command and `python3 -m unittest discover -s frontend/scripts -p test_check_style_coverage.py` pass.

## 3. Integration checks and report

- [x] 3.1 Run the full checks:
  - `uv run pytest` in `backend/` (unchanged; record the count and coverage)
  - `npm test -- --run` in `frontend/` (record the test count and the axe scans)
  - `npm run build`
  - the style audit and its unit test
  - `openspec validate improve-single-item-topics --strict`
  - a local `docker build`, if available

  Write the commands and their real results to `docs/process/test-report-improve-single-item-topics.md`. List the manual checks that were not performed: the live measurements at 1440, 1000, 901, 900, and 420 px on the real Chinese digests and an English digest.

  Add an entry for this run to `docs/process/ai-usage-log.md`, after the latest entry: the prompt as a faithful excerpt, the outcome, and the problems.

  Verify: every command passes, and the report exists with the actual numbers.

## 4. Review fixes, round 1

Notes for this round:
- These tasks come from the review of groups 1–3 (`/code-review`, the spec subagent, and live checks in a browser). Each finding was confirmed by rendering, a screenshot, or a mutation.
- On 2026-10-16 the user decided to stack items at 1100 px and below. `design.md` (D1, D4, Risks, Testing), `proposal.md`, and the spec delta were amended, the latter with a new "Medium window" scenario. Read those passages first.
- **Use `diagnosing-bugs`** for 4.1 and **`tdd`** for 4.2. Task 4.3 is a refactor step with no red test.
- Do not edit `proposal.md`, `design.md`, or the spec deltas.

- [ ] 4.1 Items overlap at 900 px and below (design D1, D4).
  - Cause: the narrow reset `.items > .item > * { grid-column: 1 / -1; grid-row: auto; }` (`layout.css:67`) has specificity (0,2,0), and the wide placements at `:25-27` have (0,3,0). They still apply inside the container query.
  - Effect, measured live at 420 and 900 px on real digests: the item's columns become `0px 170px 170px`, and each summary is painted over its source line and title.
  - **Fix:** move every side-by-side rule into one `@container (width > 1100px)` block, and delete the narrow reset. The side-by-side rules are the item's `subgrid`, `column-gap`, and `grid-template-rows`, plus the meta, title, and summary placements. Outside any query, keep only the item's `grid-column: 1 / -1` and the top rule between items.

  Verify with a failing-first test in `frontend/src/styles/tokens.test.ts`. It replaces the two tests added in 2.1 and parses `layout.css` by block. It asserts:
  - Inside `@container (width > 1100px)`: `.items > .item` has `grid-template-columns: subgrid`, `column-gap: var(--gutter)`, and `grid-template-rows: auto auto 1fr`. The meta and title take `1 / span 3` with rows 1 and 2. The summary and unavailable note take `4 / -1` and `1 / -1`.
  - Outside that block: none of these placements or that row template appears anywhere in `layout.css`. No rule targets `.items > .item > *`, `.item-meta`, `.item-title`, `.summary`, or `.summary-unavailable` for placement.
  - Outside any query: `.items > .item` spans `1 / -1`, and `.items > .item + .item` has the top rule.
  - The test fails on the current `layout.css`. Removing `column-gap: var(--gutter)` from the wide block makes it fail.
- [ ] 4.2 Keep the earlier assertions that still apply: no `.item-long`, `.item-short`, or `.item:only-child` rules, and no `border-left` between items. Fold them into the 4.1 test or keep them separately.

  Verify: `npm test -- --run`, `npm run build`, and the style audit with its unit test all pass.
- [ ] 4.3 Refactor step, with no red test: in `frontend/src/components/DigestArticle.tsx:66-67`, turn the `{ return … }` arrow body that has nothing else in it into an expression body.

  Verify: `npm test -- --run` passes with no test changes in this task.
- [ ] 4.4 Docs:
  - Append a "Review fixes, round 1" section to `docs/process/test-report-improve-single-item-topics.md`, with the re-run commands and their real results, including the axe scan count.
  - In `docs/process/ai-usage-log.md`, correct your entry's false outcome claim "preserved one-column stacking below 900 px". The first version did not; say so, and point to 4.1.
  - Add the Droid session id (`92a71026`) to that entry's heading or prompt line, as the previous Droid entry does, and add one short sentence on this round.

  Verify: the report has the actual numbers, and the log entry no longer claims working narrow stacking for the first version.
