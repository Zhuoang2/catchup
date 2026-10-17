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

- [ ] 1.1 In `frontend/src/styles/tokens.test.ts`, reuse `layoutRules` to parse `src/styles/base.css`, `src/styles/layout.css`, and `src/styles/components.css`. These are the `OWNED` files in `frontend/scripts/check-style-coverage.py`. Keep track of which file each rule came from.
  - In the placement guard, check every file instead of only `layout.css`, using this rule: outside `@container (width > 1100px)`, no rule whose selector targets `.item-meta`, `.item-title`, `.summary`, `.summary-unavailable`, or `.items > .item > *` may set `grid-column` or `grid-row`.
  - Outside that query, no rule whose selector is `.item` or `.items > .item` may set `grid-template-columns` or `grid-template-rows`.
  - On a failure, name the file and the selector.

  Verify:
  - The test passes on today's CSS.
  - It fails, then passes again after reverting, for each of these temporary edits:
    - `components.css` `.summary` gets `grid-column: 2`
    - `components.css` `.item` gets `grid-template-columns: 1fr 1fr`
    - `base.css` gets a new rule `.item-title { grid-row: 3; }`
- [ ] 1.2 Add a vertical-rule guard in `frontend/src/styles/tokens.test.ts`. Across the three files, no rule whose selector targets `.item`, `.items > .item`, `.item-meta`, `.item-title`, `.summary`, or `.summary-unavailable` may set:
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
- [ ] 1.3 Run `npm test -- --run` and `npm run build` in `frontend/`, and `python3 frontend/scripts/check-style-coverage.py`.
  - Append the results and the mutation table to `docs/process/test-report-guard-digest-item-layout-css.md`, a new file.
  - Add your entry, with the Droid session id and a faithful prompt excerpt, to `docs/process/ai-usage-log.md` after the latest entry.

  Verify: every command passes, and the report exists with the actual numbers.
