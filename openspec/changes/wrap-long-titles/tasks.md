# Tasks

Implementer notes:
- **Read first.** Read `proposal.md`, `design.md` (D1–D3), and the delta in `specs/user-interface/spec.md`. If something looks wrong or contradictory, stop and report instead of redesigning.
- **Use the `tdd` skill** (D-016). Write each task's checks as failing tests first, watch them fail, then implement. Checks marked as guards pass today. Each guard gets its named mutation as the red step: apply it, see the check fail, then revert it.
- **Test rules.**
  - CSS checks read the CSS text, as the existing tests do. jsdom has no layout, so do not try to measure widths in tests.
  - In `frontend/src/styles/tokens.test.ts`, reuse `layoutRules`, `ownedLayoutRules`, and `splitSelectors` (`:156-203`). Do not add a CSS parser dependency.
  - In `frontend/src/pages/Sources.test.tsx`, mock `fetch` as the existing preview tests do (`:161-181`).
- **OpenSpec commands** always run with the `DO_NOT_TRACK=1` prefix, for example `DO_NOT_TRACK=1 openspec validate wrap-long-titles --strict`.
- **Out of scope:**
  - the extension's options page, and the standalone `frontend/public/offline.html`;
  - truncating titles, and the backend;
  - removing the existing, now redundant `overflow-wrap: anywhere` rules (design D1).
- **Commits.** Commit after each task group. Do not push, tag, or open a PR.

## 1. The web app

- [ ] 1.1 **Tests first.**

  In `frontend/src/styles/tokens.test.ts`:
  1. **Wrap from the root.** The rule in `src/styles/base.css` whose selector is exactly `.app` declares `overflow-wrap: anywhere`.
  2. **Nothing turns wrapping back off for titles.** This is a guard. Across `ownedLayoutRules()`:
     - every `overflow-wrap` or `word-wrap` declaration has the value `anywhere`;
     - no rule whose selector contains `.item-title`, `.creator-item`, `.check-title`, `.source-title`, or `.entry-list` declares `white-space` with any value other than `normal`, or `word-break: keep-all`.

     Mutations:
     - G1, add `overflow-wrap: normal` to `.item-title` (`components.css:114`);
     - G2, add `white-space: nowrap` to `.check-title` (`components.css:90`).
  3. **The preview's entry date stays whole.** The rule whose selector is `.entry-list time` declares `flex: none`.

  In `frontend/src/pages/Sources.test.tsx`:

  4. **The method line flows as one text.** For a YouTube preview with captions off, the `.preview-method` paragraph has exactly two element children: the icon's `svg`, then one `span`. That `span` contains the text "Caption fetching is off; videos will be listed without summaries" and the link "Change in Settings". The existing `it.each` (`:161-181`) still finds the paragraph by its text.

  Verify: checks 1, 3, and 4 fail before 1.2. Check 2 passes, and fails under G1 and under G2.
- [ ] 1.2 **Implement design D1 and D2:**
  - `frontend/src/styles/base.css:4`: add `overflow-wrap: anywhere` to the `.app` rule;
  - `frontend/src/styles/components.css:151`: add `flex: none` to `.entry-list time`;
  - `frontend/src/pages/Sources.tsx:78-80`: wrap `{method}` and the optional `{' '}<Link to="/settings">Change in Settings</Link>` in one `<span>`, after the `<Icon>`, as `frontend/src/pages/Settings.tsx:301-303` does.

  Verify:
  - all 1.1 checks pass;
  - G1 and G2 each fail check 2, and are reverted;
  - `git diff` shows no change left from the mutations;
  - in `frontend/`, `npm test -- --run` and `npm run build` pass.

## 2. The extension popup

- [ ] 2.1 **Tests first**, in `extension/src/test/popup.test.ts`, next to "links the styled %s page" (`:153-159`):
  1. **Wrap from the root.** In `src/popup.css`, the rule whose selector is exactly `body` (`:31`) declares `overflow-wrap: anywhere`.
  2. **Nothing turns it back off.** This is a guard. No rule in `src/popup.css` declares `overflow-wrap` with a value other than `anywhere`, or `white-space` with a value other than `normal`. Mutation G3: add `white-space: nowrap` to the `h2` rule (`:34`).

  Strip CSS comments before matching, because `popup.css:1` is a comment.

  Verify: check 1 fails before 2.2. Check 2 passes, and fails under G3.
- [ ] 2.2 **Implement design D1** in `extension/src/popup.css:31`: add `overflow-wrap: anywhere` to the `body` rule.

  Verify:
  - the 2.1 checks pass, and G3 is reverted;
  - in `extension/`, `npm test -- --run` and `npm run build` pass.

## 3. Checks and report

- [ ] 3.1 Run the full checks:
  - in `frontend/`: `npm run build`, then `npm test -- --run`;
  - in `backend/`: `uv run --python 3.12 pytest`, with `frontend/dist` present;
  - in `extension/`: `npm test -- --run`;
  - from the repository root: `docker build -t catchup:wrap-long-titles-local .`, then `scripts/docker-smoke.sh catchup:wrap-long-titles-local`;
  - `DO_NOT_TRACK=1 openspec validate wrap-long-titles --strict`.

  Write `docs/process/test-report-wrap-long-titles.md`, a new file, with:
  - the commands and their real results;
  - the red-first results of 1.1 and 2.1;
  - the mutation table for G1–G3;
  - the manual checks that were not performed, from design D3:
    - at 320 px, an 80-character title without spaces in `.item-title a`, `.creator-item > a`, `.check-title`, `.source-title`, and `.entry-list a`, with `document.documentElement.scrollWidth` equal to 320;
    - the popup at its 340 px width, with such a title in its `h2` and in an entry `li`;
    - the preview's entry date on one line beside a long title, and the "Change in Settings" link flowing after its text.

  Add this change's line to `docs/process/coverage-summary.md`, in the style of the existing lines. The backend is not remeasured.

  Add your entry to `docs/process/ai-usage-log.md` after the latest entry, with a faithful excerpt of the prompt you actually received, and the tool and model. Leave out the session id; Claude Code adds it at review.

  Verify: every command passes, and the report has the actual numbers.
