# Tasks

Implementer notes:
- **Read first.** Read `proposal.md`. There is no design document and no spec delta; this change only adds tests.
- **Test-first** with the `tdd` skill (D-016). These guards must pass on today's CSS, so their red step is a deliberate violation. For each new assertion:
  1. Make a temporary edit to a style file that the assertion must catch, and watch the test fail.
  2. Revert the edit and watch it pass.
  3. Name each mutation and its result in the commit message.
  4. Never commit a mutation.
- **Out of scope:** CSS (`frontend/src/styles/*.css`), components, and every other test file.
- **Commits.** Commit after each task group. Do not push, tag, or open a PR.

## 1. Guards over all owned style files

- [x] 1.1 In `frontend/src/styles/tokens.test.ts`, reuse `layoutRules` to parse `src/styles/base.css`, `src/styles/layout.css`, and `src/styles/components.css`. These are the `OWNED` files in `frontend/scripts/check-style-coverage.py`. Keep track of which file each rule came from.
  - In the placement guard, check every file instead of only `layout.css`, using this rule: outside `@container (width > 1100px)`, no rule whose selector targets `.item-meta`, `.item-title`, `.summary`, `.summary-unavailable`, or `.items > .item > *` may set `grid-column` or `grid-row`.
  - Outside that query, no rule whose selector is `.item` or `.items > .item` may set `grid-template-columns` or `grid-template-rows`.
  - On a failure, name the file and the selector.

  Verify:
  - The test passes on today's CSS.
  - It fails, then passes again after reverting, for each of these temporary edits:
    - `components.css` `.summary` gets `grid-column: 2`
    - `components.css` `.item` gets `grid-template-columns: 1fr 1fr`
    - `base.css` gets a new rule `.item-title { grid-row: 3; }`
- [x] 1.2 Add a vertical-rule guard in `frontend/src/styles/tokens.test.ts`. Across the three files, no rule whose selector targets `.item`, `.items > .item`, `.item-meta`, `.item-title`, `.summary`, or `.summary-unavailable` may set:
  - `border-left` or `border-right`
  - `border-inline`, `border-inline-start`, or `border-inline-end`
  - the `border` shorthand

  `border-top` and `border-bottom` stay allowed. On a failure, name the file and the selector.

  Verify:
  - The test passes on today's CSS.
  - It fails, then passes again after reverting, for each of these temporary edits:
    - `border-left: 1px solid var(--border)` on the wide `.items > .item > .summary, …` rule in `layout.css`
    - `border-right: 1px solid` on the wide `.items > .item` rule in `layout.css`
    - `border: 1px solid` on `.item-title` in `components.css`
- [x] 1.3 Run `npm test -- --run` and `npm run build` in `frontend/`, and `python3 frontend/scripts/check-style-coverage.py`.
  - Append the results and the mutation table to `docs/process/test-report-guard-digest-item-layout-css.md`, a new file.
  - Add your entry, with the Droid session id and a faithful prompt excerpt, to `docs/process/ai-usage-log.md` after the latest entry.

  Verify: every command passes, and the report exists with the actual numbers.

## 2. Review fixes, round 1

Notes for this round:
- These tasks come from the review of group 1 (`/code-review` and the spec subagent, with mutations). `proposal.md`'s "Which rules count", "Placement guard", and "Vertical-rule guard" bullets were amended; read them first.
- The `tdd` notes above still apply. Each red step is a named temporary CSS mutation that is never committed.
- Do not edit `proposal.md`.

- [x] 2.1 In `frontend/src/styles/tokens.test.ts`, change how both guards decide that a rule targets the item. Use the rightmost compound of each comma-separated selector, after normalizing whitespace, as the amended proposal describes. Widen the matched properties to the full families in the amended proposal. Failure messages still name the file and the selector.

  Verify:
  - Every group-1 mutation still fails the test, and passes again after reverting.
  - Each of these new temporary mutations fails, then passes after reverting:
    - `layout.css`: a new `.items > .item > p.summary { border-left: 1px solid; }`
    - `components.css` `.summary`: `border-left-style: solid; border-left-width: 1px`
    - `components.css` `.item-title`: `grid-area: 2 / 1`
    - `layout.css`: a new `.items>.item { grid-template: auto / 1fr 1fr; }` outside any query
    - `components.css`: a new `.topic .item { grid-template-columns: 1fr 1fr; }`
    - `components.css`: a new `:is(.summary) { grid-column: 2; }`
  - Each of these temporary edits must leave the tests green; check each, then revert:
    - `components.css`: a new `.item:hover .badge { border: 1px solid; }`
    - `components.css`: a new `.summary li { border-left: 1px solid; }`, the documented limit
    - `components.css` `.item`: `border-radius: 2px`
  - Record every mutation and its result in the commit message.
- [ ] 2.2 Docs:
  - In `docs/process/ai-usage-log.md`, your entry's heading names session `49b78a6b-…`, which is the Claude Code session id. Correct it to your Droid session `2ca2b998`, and add one short sentence on this round.
  - Append a "Review fixes, round 1" section to `docs/process/test-report-guard-digest-item-layout-css.md` with the re-run results (`npm test -- --run`, `npm run build`, the style audit) and the full mutation table, including the green false-positive checks.

  Verify: the log heading names `2ca2b998`, and the report numbers match a fresh run.
