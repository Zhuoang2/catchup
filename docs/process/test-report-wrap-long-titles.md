# Wrap long titles: implementation checks

2026-11-03, branch `wrap-long-titles`, from plan commit `2ea38a4` (#74). Implemented by Claude Code (a Claude Opus 5.5 sub-agent), because Factory Droid's login had expired.

## Full checks (task 3.1)

Run in the order `tasks.md` lists them.

| Check | Actual result |
| --- | --- |
| `cd frontend && npm run build` | TypeScript and Vite build passed; **41 modules** transformed. |
| `cd frontend && npm test -- --run` | **263 passed** in **14 files** (4 new). |
| `cd backend && uv run --python 3.12 pytest -q -p no:cacheprovider`, with `frontend/dist` present | **776 passed** in 30.78 s. Run with `UV_OFFLINE=1`, so that uv makes no network request. |
| `cd extension && npm test -- --run` | **114 passed** in **8 files** (2 new). `npm run build` also passed. |
| `docker build -t catchup:wrap-long-titles-local .` | Passed. The image's frontend stage rebuilt the app, and its stylesheet has the same hash as the local build (`index-D5TGMFXi.css`). |
| `scripts/docker-smoke.sh catchup:wrap-long-titles-local` | All **11** checks passed: health, `/api/health`, HTML at `/`, manifest, service worker, offline page, saved preference, non-root process, database on the volume, no `.env` or backend source in the image, preference after restart. The script removed its container and volume; the image was removed afterwards. |
| `DO_NOT_TRACK=1 openspec validate wrap-long-titles --strict` | `Change 'wrap-long-titles' is valid`. |

## Red first

**Task 1.1.** `cd frontend && npx vitest run src/styles/tokens.test.ts src/pages/Sources.test.tsx`, before 1.2: **3 failed, 56 passed** (59).

| Check | Test | Result before 1.2 | After 1.2 |
| --- | --- | --- | --- |
| 1. Wrap from the root | `lets unbroken text wrap from the app root` | Failed: the `.app` rule was found, but it has no `overflow-wrap: anywhere` (`expected false to be true`). | Passed. |
| 2. Nothing turns wrapping back off (guard) | `does not turn wrapping back off for titles` | Passed, as planned. Failed under G1 and G2 (below). | Passed. |
| 3. The preview's entry date stays whole | `keeps the date beside a long preview entry title on one line` | Failed: the `.entry-list time` rule was found, but it has no `flex: none` (`expected false to be true`). | Passed. |
| 4. The method line flows as one text | `flows the captions-off method text and its Settings link as one text` | Failed: `expected [ 'svg', 'a' ] to deeply equal [ 'svg', 'span' ]`. | Passed. |

After 1.2 the same run passed **59** tests, including the existing `describes %s preview with captions %s` cases, which still find the paragraph by its text.

**Task 2.1.** `cd extension && npx vitest run src/test/popup.test.ts`, before 2.2: **1 failed, 66 passed** (67).

| Check | Test | Result before 2.2 | After 2.2 |
| --- | --- | --- | --- |
| 1. Wrap from the root | `lets unbroken titles wrap from the popup body` | Failed: the `body` rule was found, but it has no `overflow-wrap: anywhere` (`expected false to be true`). | Passed. |
| 2. Nothing turns it back off (guard) | `does not turn wrapping back off in the popup` | Passed, as planned. Failed under G3 (below). | Passed. |

After 2.2 the run passed **67** tests.

## Named mutations

Each mutation was applied alone, after saving a copy of the file. The guard was run with `-t`, and the file was then restored from the copy. After each revert, `git diff` showed only the planned changes; no mutation is in the final diff.

| Mutation | Command | Result with the mutation | After revert |
| --- | --- | --- | --- |
| G1: `overflow-wrap: normal` on `.item-title` (`components.css:114`) | `npx vitest run src/styles/tokens.test.ts -t "does not turn wrapping back off"` | 1 failed, 16 skipped. Diagnostic: `src/styles/components.css: .item-title { overflow-wrap: normal }`. Failed the same way before and after 1.2. | Passed. |
| G2: `white-space: nowrap` on `.check-title` (`components.css:90`) | same | 1 failed, 16 skipped. Diagnostic: `src/styles/components.css: .check-title { white-space: nowrap }`. Failed the same way before and after 1.2. | Passed. |
| G3: `white-space: nowrap` on the popup's `h2` (`popup.css:34`) | `npx vitest run src/test/popup.test.ts -t "does not turn wrapping back off"` | 1 failed, 66 skipped. Diagnostic: `h2 { white-space: nowrap }`. Failed the same way before and after 2.2. | Passed. |

## Manual checks not performed

These are the browser checks from design D3. They are left to Claude Code's review (D-023's live check). jsdom has no layout, so the tests above pin CSS text and markup, not geometry.

- At 320 px, replace the text of the first `.item-title a`, `.creator-item > a`, `.check-title`, `.source-title`, and `.entry-list a` with an 80-character string without spaces, and check that `document.documentElement.scrollWidth` is 320.
- Open the popup at its 340 px width with such a title in its `h2` and in an entry `li`, and check that it does not scroll horizontally.
- Check that the source preview's entry date stays on one line beside a long title, and that the "Change in Settings" link flows after its text in the YouTube captions-off method line.

## Claude's review and browser check (2026-11-04)

- **Diff.** 4 source lines in `frontend/` (`overflow-wrap: anywhere` on `.app`, `flex: none` on `.entry-list time`, one `<span>` in `Sources.tsx`) and 1 in `extension/src/popup.css`; the rest are tests and docs.
- **Browser check at 320 px.** Claude ran the branch's backend and built frontend locally with a seeded database: one digest whose topic title, item title, item link, source name, and overview were unbroken strings of 60 to 192 characters, and one source with a 75-character unbroken title. At a 320 × 800 viewport, `document.documentElement.scrollWidth` was 320 on `/`, `/digests`, `/digests/1`, `/sources`, and `/settings`, and no element extended past the right edge. With `.app { overflow-wrap: normal !important }` injected on `/digests/1`, `scrollWidth` rose to 1,542, so the check could fail.
- **Not checked in a browser:** the extension popup at 340 px, and the preview's entry date on one line; the CSS checks in `tokens.test.ts` and `popup.test.ts` cover the rules.
