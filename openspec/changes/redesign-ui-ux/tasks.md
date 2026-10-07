# Tasks

Implementer notes:
- Read `proposal.md`, `design.md` (D2–D8), every file under `specs/`, and `design-review-c7.md` ("Resolution") first. If something looks wrong or contradictory, stop and report rather than redesigning.
- **The prototype is the visual and copy reference.** Port it; do not import or ship its files.
  - C7 = `prototypes/shared/base.css` → `prototypes/directions/c.css` → `c3.css` → `c3b.css` → `c7.css`.
  - Markup and copy for every screen and state come from `prototypes/shared/render.js`; realistic data comes from `prototypes/shared/data.js`.
  - To view it, run `python3 -m http.server 5180 --bind 127.0.0.1` in `openspec/changes/redesign-ui-ux/prototypes/`, then open `/directions/c7.html#<screen>/<state>?theme=light|dark&w=desktop|narrow`.
- Treat these rules as verification criteria, not notes:
  - Tests make no real network calls: mock `fetch` in vitest; respx and the autouse DNS block in backend tests.
  - Tests use **no real sleeps** (fake timers for polling).
  - Tests write nothing outside temp dirs.
  - No new runtime dependencies in `frontend/package.json`. Allowed new dev dependencies: `vitest-axe` and `axe-core`.
  - No color literals in the app's stylesheets and components (`.css` and `.tsx` files and non-test `.ts` files under `frontend/src/`) outside `frontend/src/styles/tokens.css`, except `#fff` for the switch thumb and its `rgba(0, 0, 0, .25)` shadow. The rule does not apply to files that must state colors literally and mirror the D2 tokens: the inline CSS of `offline.html`, the `background_color` and `theme_color` in `manifest.webmanifest`, the `theme-color` meta tags in `index.html` (light `#f4f0e6`, dark `#161513`), `make-icons.py` and the icons it writes, and test files (for example the `#77736a` case in `tokens.test.ts`).
  - Keep the CI job names `backend`, `frontend`, and `docker`.
  - Never push, tag, or open a PR.
- Backend commands run from `backend/` with uv; frontend commands run from `frontend/` with npm.
- Commit after each task group. Do not edit `proposal.md`, `design.md`, `specs/`, or `prototypes/`.
- Each group must leave `uv run pytest`, `npm test -- --run`, and `npm run build` green.

## 1. Snapshot fields for saved digests (backend)

- [x] 1.1 Add Alembic migration `0003` with `digests.language` (String(40), nullable) and `digest_items.source_kind` (String(16), nullable), and add them to `backend/src/catchup/models.py`. In `digest/runner.py`, write `language` (the language read at run start) and each saved item's `Source.kind` at save time, for both topic items and Creator updates items. Return them from `GET /api/digests/{id}` in `api/digests.py`: `language`, `source_kind` on topic items, and `source_kind` on Creator updates groups and items. Verify with pytest:
  - the migration upgrades from `0002` with existing rows reading NULL, and downgrades
  - a run in zh-Hans saves `language='zh-Hans'` and the right kinds
  - changing `digest_language` or deleting the source afterwards does not change the API response (spec `digest-history` scenarios "Language changed after saving" and "Source deleted after saving")
  - an old row returns `null`

## 2. Design system foundation

- [x] 2.1 Create `frontend/src/styles/tokens.css`, `base.css`, `layout.css`, and `components.css` per design.md D2, import them in `frontend/src/main.tsx`, and delete `frontend/src/style.css`. Requirements:
  - `tokens.css` holds every color token in the D2 table with exactly those values, including `--error-border` (light on `:root`, dark under `prefers-color-scheme: dark`), plus the D2 non-color tokens (font stacks, type sizes, radii, spacing and widths) with their values from the C7 cascade.
  - `layout.css` holds the shared container, the 12-column grid with `subgrid` section rows, the rail, the compact masthead, and container queries at 900 and 640 px, ported from `c7.css` and `base.css`.

  Verify that `npm run build` succeeds and a grep finds no color literals outside `tokens.css` (apart from the allowed exceptions).
- [x] 2.2 Add `vitest-axe` and `axe-core` as dev dependencies, a shared test helper that runs `axe` on a rendered container and fails on violations, and `frontend/src/styles/tokens.test.ts`. The token test parses `tokens.css` and asserts these pairs for both themes:
  - text on `--bg` and `--surface`: `--fg`, `--muted`, `--subtle`, `--accent`, `--link`
  - `--accent-fg` on `--accent`
  - each tone on its soft background: `--ok`, `--warn`, `--error`
  - `--muted` on `--neutral-soft`, all ≥ 4.5:1
  - `--muted` on `--disabled` (the switch boundary), ≥ 3:1

  Also assert that `--error`, `--warn`, and `--accent` differ pairwise by at least 20° in HSL hue, in both themes (D2 "Hue check"). Verify that the test passes, and fails if `--subtle` is set to `#77736a`.

## 3. App shell and shared components

- [x] 3.1 Build `frontend/src/components/AppShell.tsx` per design.md D3 and use it in `frontend/src/App.tsx` (routes unchanged):
  - skip link, masthead (wordmark, today's long date, nav with `aria-current`, with Digest counting as History), and `main#main[tabindex=-1]`
  - compact masthead on `/digests/:id` and below 900 px
  - `useJump` for the skip link

  Verify:
  - the App test checks nav links and `aria-current`
  - a test checks that activating the skip link moves `document.activeElement` to `#main`
  - an axe scan passes
- [x] 3.2 Build the D3 components: `PageHead`, `SectionRow`, `Rail`, `Button`, `Chip`, `KindBadge`, `ReasonLabel`, `Alert`, `Switch`, `Stepper`, `Progress`, `StatusRegion`, `SummaryText`, `Icon`, `useJump`. Styles go in `components.css`, ported from the prototype. Verify with component tests:
  - `Switch` exposes `role="switch"`, its label box contains only the track and text, and `describedBy` is applied
  - `Stepper` exposes "(done)", "(in progress)", and "(next)"
  - `Progress` is named by its label
  - `SummaryText` renders paragraphs and "- " lists in order and applies `lang`
  - `ReasonLabel` renders the five reasons in sentence case
  - `KindBadge` renders "YouTube channel" with that case
  - `useJump` focuses its target and uses `behavior: 'auto'` under a mocked reduced-motion media query
  - an axe scan passes for each component

## 4. Digest and History

- [x] 4.1 Rebuild `frontend/src/pages/DigestView.tsx` per design.md D4 "Digest", ported from `render.js digest()`:
  - the headline "No. {id}", long date, and " · HH:MM"
  - the meta line
  - the index only for 2 or more sections, with links focusing their sections through `useJump`
  - topic section rows with long/short item spans
  - `lang` from `digest.language`
  - kind icons and hidden labels from `source_kind`
  - Creator updates rows, and the Creator-updates-only line

  Verify with tests covering the `user-interface` scenarios "Long transcript summary", "Only Creator updates", "Caption reason", and "Chinese digest":
  - an English digest has no `lang="zh-Hans"`
  - an old digest with `language: null` and `source_kind: null` renders without `lang` or icons
  - an axe scan passes
- [x] 4.2 Rebuild `frontend/src/pages/History.tsx` per design.md D4 "History": rows with "No. {id} · long date · time", topic previews, counts, and the rail. Verify with tests for the list and the empty state (Archive hidden when empty), plus an axe scan.

## 5. Generate

- [x] 5.1 Rebuild `frontend/src/pages/Generate.tsx` per design.md D4 "Generate", ported from `render.js generate()`, with today's polling and the `run_active` handling kept (`Generate.tsx:37-73`). The states are first run, idle, collecting, summarizing, succeeded, no new content, and failed, with:
  - the primary-action table from D4
  - a disabled Generate with a visible reason on first run
  - the failed-run copy about reused summaries
  - the state-aware rail
  - the `StatusRegion` messages

  Verify with fake-timer tests:
  - each state renders the primary action from the D4 table and no other `.btn-primary`; No new content renders none
  - the status region text changes from "Summarizing, 5 of 12" to "Digest ready: 12 items" when polling returns `succeeded`
  - the first-run rail shows "Getting started" and no counts
  - the progress bar has an accessible name
  - an axe scan passes for each state

## 6. Sources

- [x] 6.1 Rebuild `frontend/src/pages/Sources.tsx` per design.md D4 "Sources", ported from `render.js sources()`:
  - the add form with `aria-describedby`/`aria-invalid`
  - Preview as secondary while a preview is open
  - preview card
  - rows with `KindBadge`, wrapped feed URL with `title`, chips ("Rate limited · try later"; "Possible gap" with `title`), and time
  - the inline delete confirmation replacing `window.confirm`
  - the empty state and the rail

  The existing error copy is kept (`Sources.tsx:16-32`). Verify with tests:
  - the spec scenario "Delete confirmation" (the confirm row text; Cancel restores the row; Delete calls the API and refreshes)
  - the error state links the error and the hint and sets `aria-invalid`
  - kind labels are visible
  - only one primary button while a preview is open
  - an axe scan passes for the list, preview, error, confirm-delete, and empty states

## 7. Settings

- [x] 7.1 Rebuild `frontend/src/pages/Settings.tsx` per design.md D4 "Settings", ported from `render.js settings()`:
  - three section rows with `aria-hidden` step numbers and hidden "Step N: "
  - the privacy margin note
  - "Saved key ending in {last4}" as text, with the empty replace input and `aria-describedby`
  - the caption risk note directly under its switch, linked by `aria-describedby`
  - Skip Shorts

  Today's load, test-connection, and save flows are kept (`Settings.tsx:43-102`). Verify with tests:
  - the spec scenario "Saved key" (the input value and placeholder never contain the key or last4)
  - the risk note is the switch's description
  - headings' accessible names read "Step 1: Model provider" etc.
  - the existing flows still pass
  - an axe scan passes for the saved, first-run, tested, and error states

## 8. Installable app and offline page

- [x] 8.1 Add `frontend/scripts/make-icons.py` per design.md D7 (standard-library PNG writer), and commit its outputs to `frontend/public/`: `icon.svg`, `icon-192.png`, `icon-512.png`, `icon-maskable-512.png`, `icon-1024.png`. Add `frontend/public/manifest.webmanifest`, and the manifest link, theme-color metas, and apple-touch-icon in `frontend/index.html`. Verify:
  - a test reads the manifest and checks `name`, `start_url`, `display`, and the four icons with sizes and purposes
  - it checks each PNG's header for its declared size
  - re-running the script produces byte-identical files
- [x] 8.2 Add `frontend/public/sw.js` and `frontend/public/offline.html` per design.md D7, and register the worker in `frontend/src/main.tsx` only in production builds. Verify with a vitest test that evaluates `sw.js` with fake `self`, `caches`, and `fetch`:
  - install caches only `/offline.html`
  - a navigation whose fetch rejects gets the cached `offline.html`
  - a navigation returning 500 passes through
  - `/api/...` and `/assets/...` requests are not intercepted
  - `cache.put` is never called for any other URL
  - activate deletes old caches

  Also verify that `offline.html` contains both start commands and a Reload button, and that `npm run build` copies the files to `dist/`.
- [x] 8.3 Extend `scripts/docker-smoke.sh`: `/manifest.webmanifest` returns 200 with `application/manifest+json`, `/sw.js` returns 200 with a JavaScript content type, and `/offline.html` returns 200. Add a README section "Install as an app" covering:
  - Chrome/Edge install and Safari "Add to Dock"
  - that `localhost` and `127.0.0.1` count as separate installs
  - the offline page
  - how to unregister the worker in DevTools

  Verify that the smoke script passes against a locally built image (or report that Docker is unavailable).

## 9. Integration checks

- [x] 9.1 Run the full checks and record the results in `docs/process/test-report-redesign-ui-ux.md`:
  - `uv run pytest` (with coverage)
  - `npm test -- --run` (count the axe-scanned states)
  - `npm run build`
  - `openspec validate redesign-ui-ux --strict`
  - `docker build` plus `scripts/docker-smoke.sh` if Docker is running; otherwise say so explicitly

  Verify that all pass, and report any skipped check with its reason.

## 10. Review fixes (added 2026-10-07 after the implementation review)

The same implementer notes apply. Every finding below was verified by the reviewer against the code or in a browser. Fix them in order; commit after each task.

- [x] 10.1 **Digest list API and History (D4 History, D6; spec `digest-history` "List saved digests").** In `backend/src/catchup/api/digests.py`, `GET /api/digests` also returns `language`, `topics` (topic titles in order, excluding Creator updates), and `creator_updates_only`, loaded with one query for all listed digests. In `frontend/src/pages/History.tsx`, use these fields and remove the per-digest detail requests. Verify:
  - a pytest checks the new fields, including an old row (`language: null`) and a Creator-updates-only digest
  - a pytest shows the number of SQL statements does not grow with the number of digests (for example with a SQLAlchemy `before_cursor_execute` counter for 1 and 5 digests)
  - a vitest checks that History issues exactly one request, and that previews and the "Creator updates only" row render
- [ ] 10.2 **`lang` mapping (D5).** Add a helper, for example `frontend/src/components/lang.ts`, and use it everywhere `digest.language` reaches a `lang` attribute (`DigestView.tsx`, `History.tsx`). Verify with unit tests for `en`, `zh-Hans`, `original`, `null`, "Japanese", "日本語", "Français", "繁體中文", and an unknown "Klingon" (no `lang`). Add a DigestView test with `language: 'original'` asserting that no element in the digest has a `lang` attribute other than the app root, and an axe scan on it. Also tighten the old-digest test so it asserts that no `lang` attribute appears in the digest content at all, not just no `zh-Hans`.
- [ ] 10.3 **Generate loading and state (`Generate.tsx`).**
  - Load the four startup requests independently (for example `Promise.allSettled`), so one failure does not hide an active run or keep Generate disabled. Only the first-run state depends on `/settings/model`.
  - Refetch `/digests` when a run reaches `succeeded`, so the hero and the rail show the new edition.
  - While a run is collecting or summarizing, the Generate button is a disabled **primary** "Generating…" (D4 "Running"), as in `render.js generate()`.
  - Use `plural()` in the lede ("Check your 1 source").
  - Use a title that fits the context for POST and polling errors instead of "Could not load this page".

  Verify with fake-timer tests:
  - `/digests` failing still shows an active summarizing run and its progress
  - clicking Generate sends one POST, shows collecting, then polls to succeeded and refetches `/digests` (the rail shows the new "No. {id}")
  - a POST answering `model_not_configured` switches to the first-run state
  - the succeeded state shows the token text
  - the `run_active` test asserts exactly one POST
  - the running state has exactly one `.btn-primary`, which is disabled
- [ ] 10.4 **Field-level errors only for field problems.**
  - In `Sources.tsx`, keep load and delete errors in a separate page-level alert. Only preview and confirm errors set `aria-invalid` and `aria-describedby` on the URL input.
  - In `Settings.tsx`, mark the key field invalid only for key-related codes (`auth_failed`, `insufficient_balance`, and the codes the API uses for a missing or required key; check `backend/src/catchup/api/settings.py`), and the base URL only for `connection_failed`. Show other errors, including load errors, form-wide. Remove the unreachable `loading && error` line or make the load error render.

  Verify with tests: a failed delete leaves the URL input without `aria-invalid`, keeps the row, and shows the page-level alert; an `invalid_language` save error does not mark the key field; a load error is visible.
- [ ] 10.5 **Focus in the inline delete confirmation (`Sources.tsx`).** When the confirmation opens, focus its Cancel button. On Cancel, return focus to that row's Delete button. After a successful delete, focus the "Your sources" heading (make it focusable with `tabIndex={-1}`). Verify with tests asserting `document.activeElement` after each step.
- [ ] 10.6 **Unported prototype styles.** Port the missing rules from the C7 cascade into `components.css` and `layout.css`, using the cascade's effective values:
  - `.nav-link .icon { display: none }` (`c.css:23`)
  - `.topic > .topic-title { font-size: 1.45rem }` (`c7.css:21`)
  - the body font on `.app-nav`, `.digest-meta`, `.masthead-line`, `.section-label`, `.field-label`, `.btn`, `.source-feed` (`c3b.css:4`)
  - `.digest-meta { font-size: .92em }`
  - `.eyebrow` weight 600
  - `.title-time` muted
  - `.empty-state`, `.examples`, `.icon-empty`, `.icon-xs`, `.icon-result`, `.result-ok`, `.result-none`
  - `.inline-msg`, `.msg-ok`, `.msg-error`
  - `.rail-steps` numbering
  - `.notice`, `.preview-method`, `.key-saved .icon`, `.count`, `.check-status`
  - `.history-topics` single-line ellipsis

  Fix the 900 px rule that sets `--margin` on `.app` (a container cannot query itself) by setting it on `.page-frame` inside the query. Verify:
  - a script or test lists every class used in `render.js` output and in `frontend/src`, and reports any class with prototype rules but no app rules; include its output in the test report
  - in the browser at 320 px wide, all four nav links are fully visible and `document.documentElement.scrollWidth` is 320
- [ ] 10.7 **Markup and copy from the prototype.**
  - Use the prototype's short date format (`render.js fmt()`, for example "1 Oct 2026, 09:00") for item meta, Creator updates, and source check times. Keep the long date where the prototype uses it (headlines, history rows, the "Last digest" line).
  - The digest index shows each section's item count (`toc-count`).
  - Digest item and Creator-update links end with a visually hidden " (opens the original)".
  - Creator-update items do not repeat the kind icon; the group heading carries it.
  - The no-new-content card has its `result-head` with the info icon.
  - The masthead `<time dateTime>` uses the local date.
  - `Alert` sets `role="alert"` only for the `error` tone.
  - The Digest page keeps an `h1` while loading and on error.
  - `frontend/public/offline.html` matches the prototype's offline state (`render.js offline()` with the C7 styles: serif wordmark and heading, centered, small-caps Reload button), still self-contained with inline CSS.

  Verify with tests for the index counts, the hidden link text, the single kind label per Creator-updates group, the `Alert` roles, and the loading `h1`, plus axe scans. Re-run the `offline.html` checks from 8.2.
- [ ] 10.8 **Re-run the integration checks** from 9.1 and update `docs/process/test-report-redesign-ui-ux.md` with a "Review fixes" section.
