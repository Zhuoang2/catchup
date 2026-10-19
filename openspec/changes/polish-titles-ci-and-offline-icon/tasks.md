# Tasks

Implementer notes:
- **Read first.** Read `proposal.md`, `specs/content-collection/spec.md`, and `specs/local-deployment/spec.md`. There is no design document. If something looks wrong, stop and report.
- **Work test-first with the `tdd` skill** (D-016). Write each task's checks first, watch them fail, then implement.
- **Test rules.** Backend tests use the existing fixtures and no real network. Frontend tests read files from `public/` as `src/install.test.ts` does.
- **Out of scope:**
  - #43 part 2, the 16 px legibility of the icon
  - caching files in the service worker
  - `ci.yml`
  - titles that come from the feed, or texts of 80 characters or fewer
- **Commits.** Commit after each task group. Do not push, tag, or open a PR.

## 1. One ellipsis in derived titles (#15)

- [x] 1.1 In `backend/tests/test_discovery.py`, next to the existing derived-title test (the "Happy opening day, hockey fans!" case), add failing tests for `_entry_title`, either through `parse_feed` or directly:
  1. A text longer than 80 characters whose cut falls on "..." (three dots right before the cut) gives a title that ends with exactly one "…" and no "." before it.
  2. The same with a "…" character at the cut.
  3. A text of 80 characters or fewer that ends in "..." is returned unchanged, without an added ellipsis.
  4. The existing hockey case still gives the same title.

  Verify: cases 1 and 2 fail before 1.2. Cases 3 and 4 pass, as guards; the report says so.
- [x] 1.2 In `backend/src/catchup/sources/feeds.py`, `_entry_title`: after the cut, strip trailing whitespace, dots, and "…" from the prefix before appending "…".

  Verify: the 1.1 tests pass, and `uv run pytest` passes in `backend/`.

## 2. Release builds skip documentation-only pushes (#21)

- [x] 2.1 In `.github/workflows/release.yml`, add `paths-ignore` to the `push` trigger with `docs/**`, `openspec/**`, `assets/**`, and `**/*.md`. Keep `branches: [main]` and `tags: ['v*.*.*']` as they are. GitHub does not evaluate path filters for tag pushes, so releases still build.

  Verify:
  - `actionlint .github/workflows/release.yml` passes.
  - Parsing the file shows the trigger has the four `paths-ignore` patterns, `branches: [main]`, and `tags: ['v*.*.*']`. For example, use `node -e` with the `yaml` package if it is installed, or a short Python check. Record the command and its output.
  - No other workflow file changes.

## 3. Icon on the offline page (#43, part 1)

- [x] 3.1 In `frontend/src/install.test.ts`, add a failing test: `public/offline.html` declares `<link rel="icon">` whose `href` is a `data:image/svg+xml` URI. Decode the URI and check that it is an `<svg>` with `viewBox="0 0 1024 1024"` and the same two fills (`#f4f0e6`, `#151412`) as `public/icon.svg`. Also check that the page loads no other external resource for the icon.

  Verify: the test fails before 3.2.
- [x] 3.2 In `frontend/public/offline.html`, add the inline icon link in `<head>`. Use the artwork of `public/icon.svg`, URL-encoded or base64-encoded.

  Verify: the 3.1 test passes, the existing install tests pass, and `npm test -- --run` and `npm run build` pass in `frontend/`.

## 4. Checks and report

- [x] 4.1 Run `npm run build` in `frontend/` first, then:
  - `uv run pytest --cov=catchup --cov-report=term` in `backend/`
  - `npm test -- --run` in `frontend/`
  - `actionlint`
  - `openspec validate polish-titles-ci-and-offline-icon --strict`

  Write the commands and their real results to `docs/process/test-report-polish-titles-ci-and-offline-icon.md`, with the red-first results of 1.1 and 3.1. Name the checks that cannot run before merge:
  - a documentation-only push to `main` not starting "Release image";
  - the offline page's tab icon in a real browser with the server stopped.

  Add your entry to `docs/process/ai-usage-log.md` after the latest entry, with a faithful excerpt of the prompt you actually received, and the tool and model. Leave out the session id.

  Verify: every command passes, and the report has the actual numbers.

## 5. Fix round 1 (review findings)

Review found no wrong behavior against the plan, but two edge cases of the title rule and some test gaps. The delta in `specs/content-collection/spec.md` now names the CJK dots and the fallback cut, and adds one scenario.

Use `tdd`. Behavior changes get a failing test first. Checks of behavior that is already correct get a named temporary mutation as their red step, applied by hand: see the test pass, apply the mutation and see it fail, then revert it. Record every check and its red result in the report.

- [ ] 5.1 In `backend/tests/test_discovery.py`, add tests for `_entry_title`:
  1. **CJK full stops at the cut** (behavior change, red first). A Chinese text longer than 80 characters with "。。。" right at the cut gives a title that ends with exactly one "…", with no "。" before it. Add the same for "．．．" and "⋯⋯".
  2. **Nothing left after stripping** (behavior change, red first):
     - "... " followed by one 100-character word gives the first 80 characters, with trailing dots and spaces stripped, plus "…". The title begins with "... " and contains part of the word.
     - A text of 100 dots gives "…". (Amended: this already passes today, so it is a guard, not a red-first case. After 5.2, check it with a named mutation: skip the strip after the fallback 80-character cut. The title then ends in dots before "…".)
  3. **Space before the dots** (pin). "B" × 75 + " ... more text follows here" gives "B" × 75 + "…". Mutation: `rstrip(".…")` without the space.
  4. **A text just over 80 characters** (pin). "A" × 78 + "..." + " more" gives "A" × 78 + "…". Mutation: strip trailing dots from the whole text before cutting.

  Verify: case 1 and the first case of 2 fail before 5.2. The 100-dots guard and each pin fail under their mutations, which are then reverted.
- [ ] 5.2 In `backend/src/catchup/sources/feeds.py`, `_entry_title`:
  - strip trailing spaces, ".", "…", "。", "．", and "⋯" from the cut text;
  - if nothing is left, cut the text at 80 characters, without the word-boundary rule, and strip again;
  - then append "…".

  Verify: the 5.1 tests and all existing title tests pass, and `uv run pytest` passes in `backend/`.
- [ ] 5.3 In `frontend/src/install.test.ts`, extend the offline-page test: no element in `offline.html` other than the inline icon link refers to an icon file. That is, no `img`, `link`, or `source` with a `src` or `href` containing "icon". Mutation: add `<img src="/icon.svg">` to the body.

  Verify: the test passes on the current page, and fails under the mutation, which is then reverted. `npm test -- --run` passes in `frontend/`.
- [ ] 5.4 Add a "Fix round 1" section to `docs/process/test-report-polish-titles-ci-and-offline-icon.md`, with the commands, the real results, and the red results. Also add these two known limits:
  - An entry with no guid, no unique link, and no title gets its identity key from its derived title and date. When such an entry's title changes under the new rule, it is collected once more after the upgrade.
  - `release.yml` has no committed test; the trigger was checked with `actionlint` and a one-off parse.

  Add a fix-round entry to `docs/process/ai-usage-log.md` after the latest entry, with a faithful excerpt of the prompt you actually received, and the tool and model. Leave out the session id.

  Verify: every command passes, and the report has the actual numbers.
