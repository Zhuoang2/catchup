# Design

Status: Proposal 1 chosen by the user on 2026-10-06 (port the C7 prototype CSS as a hand-written design system, with a minimal service worker). Open questions resolved as recommended:
- the theme follows the system only
- the edition number is the digest id
- `prototypes/` stays in the archived change as design evidence

Amended 2026-10-06 after Droid stopped on two contradictions in the plan (approved by the user): `--error` moved from `#a33a00` / `#ff9a62` to `#a34200` / `#ffa65e` so error, warn, and accent differ by at least 20° in hue; a state may have no primary action (No new content); `tokens.css` also carries `--error-border` and the non-color tokens.

Amended 2026-10-07 after the implementation review (approved by the user): `GET /api/digests` also returns topic titles and the language (D4 History, D6); `lang` values are mapped (D5); the running state keeps a disabled primary Generate (D4); review fixes are task group 10.

The two-proposal comparison is in git history (`26c9d64`). The rejected alternative is recorded under D1.

## Context

See `proposal.md` for motivation, `research.md` for the current frontend, `prototypes/` for the chosen design, and `design-review-c7.md` for the verified review and its resolution.

**Today's frontend:**
- React 19.3, React Router 7.18, Vite 8.3, TypeScript 7.0.
- Five pages and no shared components (`frontend/src/pages/*.tsx`).
- A 4-line stylesheet (`frontend/src/style.css:1-4`).
- A small `request()` client (`frontend/src/api/client.ts:1-31`).
- 35 vitest tests that select by role and text.

FastAPI serves `dist/` through an `/assets` mount and an SPA fallback that serves any other file in `dist/` (`backend/src/catchup/main.py:83-102`).

**The prototype is the visual and markup reference:**
- C7's cascade is `shared/base.css` → `directions/c.css` → `c3.css` → `c3b.css` → `c7.css`.
- Screens and states come from `shared/render.js`; sample data from `shared/data.js`.
- It is not shipped or imported; it is ported.

## Goals / Non-Goals

**Goals:**
- **Fidelity:** the real app matches C7 in every prototype state, in both themes, at 1440 px and 420 px.
- **Review outcomes carried into the app**, each measured again in review:
  - the first digest topic starts within 50% of a 900 px viewport
  - the header is ≤ 120 px at 420 px
  - strict AA contrast
  - focus moves, `lang` marks, and a single status region
- **Installable** in Chrome, Edge, and Safari on macOS, with an honest offline page.

**Non-Goals:**
- Precaching the app or the API, or working offline (rejected with Proposal 2).
- A manual theme switch, web fonts, or UI or CSS libraries.
- New API endpoints, new routes, or features not shown in the prototype (bookmarks, likes, editing sources).
- Firefox installation (no desktop install on macOS; it works as a web page).

## Decisions

### D1. A ported, hand-written CSS design system (Proposal 1)
- **Decision.** C7's verified CSS is re-expressed as four owned stylesheets plus small React components, with no runtime dependencies.
- **Alternative considered (Proposal 2):**
  - What it was:
    - CSS Modules per component
    - Radix UI primitives (Switch, AlertDialog, Tooltip, Toast)
    - `vite-plugin-pwa` with Workbox precache and an update prompt
  - Why it was rejected:
    - The prototype's measured contrast, focus, and grid results would have to be re-verified after translating them into modules.
    - Precaching adds a stale-shell risk for an app that cannot work without its server.
    - It adds about 7 dependencies, and a modal dialog departs from the reviewed inline confirmation.

### D2. Stylesheets and tokens
- **Files** in `frontend/src/styles/`, imported in this order from `main.tsx`. `style.css` is deleted.
  - `tokens.css`: custom properties on `:root`, dark values under `@media (prefers-color-scheme: dark)`. No color literals appear in the app's stylesheets and components outside this file, except `#fff` for the switch thumb and its `rgba(0, 0, 0, .25)` shadow. Files that must state colors literally mirror these tokens: `offline.html`, the manifest, the `theme-color` meta tags, the icon script and icons (D7), and tests.
  - `base.css`: element defaults, the focus ring (2 px `--accent` outline, 2 px offset), `.sr-only`, reduced-motion rules, and `::placeholder { color: var(--muted) }`.
  - `layout.css`:
    - the `.page-frame` container (`max-width: 78rem`, `--margin: 2rem`, `--gutter: 1.5rem`), shared by the header and `main`
    - the 12-column page grid, with section rows on `subgrid`, and the rail (columns 9–12 with a left rule)
    - the compact masthead
    - container queries on the root wrapper at 900 px (single column, compact masthead everywhere, rail below content) and 640 px (vertical stepper, nav labels kept on one row)
  - `components.css`: one block per component in D3.
- **Effective C7 values** (merged from the prototype cascade, including the review fixes):

  | Token | Light | Dark |
  |---|---|---|
  | `--bg` | `#f4f0e6` | `#161513` |
  | `--surface` | `#f8f5ed` | `#1c1b18` |
  | `--fg` | `#151412` | `#ece7dc` |
  | `--muted` | `#4a4741` | `#b8b2a5` |
  | `--subtle` | `#66625a` | `#8c8679` |
  | `--border` | `#d4cdbd` | `#33302a` |
  | `--border-strong` | `#151412` | `#ece7dc` |
  | `--hover` | `#ebe5d7` | `#24221e` |
  | `--accent` | `#8a1c14` | `#e0796d` |
  | `--accent-fg` | `#fbf7ef` | `#161513` |
  | `--accent-soft` | `#efdcd5` | `#3a211d` |
  | `--link` | `#151412` | `#ece7dc` |
  | `--ok` / `--ok-soft` | `#1e6b34` / `#e2f0e5` | `#7fd08f` / `#1a2b1e` |
  | `--warn` / `--warn-soft` | `#6b5e00` / `#f1ecc8` | `#d9c25a` / `#2f2b16` |
  | `--error` / `--error-soft` | `#a34200` / `#fbe3d6` | `#ffa65e` / `#3a2418` |
  | `--error-border` | same as `--error` | same as `--error` |
  | `--neutral-soft` | `#e9e3d5` | `#24221e` |
  | `--info-soft` | `#ece6d8` | `#22201c` |
  | `--disabled` | `#dcd9d0` | `#33322f` |

- **Hue check.** In HSL hue, accent vs error is 20.2° / 20.6° and error vs warn is 28.4° / 22.3° (light / dark). Error text contrast stays ≥ 5.1:1 on `--bg`, `--surface`, and `--error-soft`.
- **Non-color tokens** come from the same cascade and also live in `tokens.css`: the font stacks (`--font-body`, `--font-heading`, `--cjk`), type sizes (`--text`, `--title-size`, `--title-tracking`, `--topic-size`, `--heading-weight`), radii (`--radius`, `--radius-sm`, both 0 in C7), and spacing and widths (`--gap`, `--gutter`, `--margin`, `--content`, `--page`). `--nav-active` is `transparent`.
- **Fonts.**
  - Body: `"Iowan Old Style", "Hoefler Text", Georgia, "Songti SC", "STSong", "Noto Serif CJK SC", "Source Han Serif SC", "PingFang SC", "Hiragino Sans GB", "Noto Sans CJK SC", "Microsoft YaHei", serif`.
  - Heading: the same, starting with `"Big Caslon", "Baskerville"`.
  - Inputs use the system sans.
  - Labels, chips, badges, and nav use `font-variant-caps: all-small-caps`, never `text-transform: lowercase`. Reasons use sentence case at `0.88em`.
- **Visual rules:**
  - rules instead of boxes for run results, the add form, source rows, and history rows
  - boxes only for the source preview, alerts, and the delete confirmation
  - a 3 px rule above each topic and settings section
  - a double rule under the masthead
  - the switch has a 1.5 px `--muted` boundary in the off state

### D3. Components (`frontend/src/components/`)
- **`AppShell`.**
  - Contains the skip link, the masthead (wordmark, today's date line, nav with `aria-current`), and `main#main[tabindex=-1]`.
  - It is compact on the digest route and below 900 px.
- **Layout and content:**
  - `PageHead` (title, lede, actions)
  - `SectionRow` (title column, content columns, optional margin note)
  - `Rail` (receives content per state)
  - `Stepper` (steps with visually hidden "(done)", "(in progress)", "(next)")
  - `Progress` (`aria-labelledby` its visible label)
  - `SummaryText` (paragraphs, plus "- " lines as `<ul>`; keeps today's logic, `frontend/src/pages/DigestView.tsx:35-50`; accepts `lang`)
- **Controls and status:**
  - `Button` (variants `primary`, `secondary`, `ghost`, `danger`, `danger-solid`; sizes `sm`, `lg`)
  - `Chip` (tones `ok`, `neutral`, `warn`, `error`)
  - `KindBadge` (Website feed / Podcast / YouTube channel, with icon)
  - `ReasonLabel`
  - `Alert` (`info`, `error` with `role="alert"`)
  - `Switch` (a native checkbox with `role="switch"`; the label holds only the track and text; optional `describedBy`)
  - `StatusRegion` (one persistent visually hidden `role="status"` per page)
- **Helpers:**
  - `Icon` (the inline SVG set from `render.js`)
  - `useJump(id)`: scrolls with `behavior: 'auto'` under reduced motion and `'smooth'` otherwise, then calls `focus({ preventScroll: true })`.

### D4. Pages and their states
Each page reproduces the corresponding `render.js` function, including its copy. The state comes from the existing endpoints (`research.md`, "API shapes consumed by the UI").

- **Generate** (`render.js generate()`).
  - Its state is derived from:
    - `GET /api/settings/model`: `key_set` false means first run
    - `GET /api/sources`: none means an "add sources" hint
    - `GET /api/digest-runs/active` and polling, as today (`Generate.tsx:37-53`)
    - the run `status`
  - Primary action per state:

    | State | Primary action | Secondary |
    |---|---|---|
    | First run | Set up your model | Generate, disabled with reason |
    | Idle | Generate digest | — |
    | Running (collecting, summarizing) | "Generating…", disabled | — |
    | Succeeded | View digest | Generate digest |
    | No new content | — | Generate digest |
    | Failed (`auth_failed`, `insufficient_balance`, `model_not_configured`, `connection_failed`) | Check settings | Try again |
    | Failed (other) | Try again | — |

  - The failed copy states that summaries are reused and nothing was saved.
  - The rail shows Last digest (from `GET /api/digests`[0]: "No. id · date, time"), Your sources by kind, and How it works. On first run it shows Getting started instead.
  - The status region text is "Checking sources, N of M", "Summarizing, N of M", "Digest ready: N items", or "No new content".
- **Digest** (`render.js digest()`).
  - Compact masthead. The headline shows "No. {id}", the long date, and " · HH:MM".
  - The index is shown only when there are 2 or more sections.
  - Topic section rows: the title and overview (body color) in columns 1–3, items in 4–12 as a 9-column subgrid.
    - An item is long when it has `points` or its summary is longer than 140 characters. Long items span 6 columns, short ones 3.
    - A long item following a long item starts a new row with a top rule.
    - Short items next to each other get a 1 px vertical rule.
  - Creator updates: a section row with groups in columns of 3. A Creator-updates-only digest has a 3 px rule and the line "Nothing could be summarized this time. Here is what your sources published."
  - `lang` uses `digest.language` (D6) on topic titles, overviews, summaries, and index entries. Item titles have no `lang`.
  - The source kind uses `item.source_kind`: the icon plus a visually hidden kind label.
- **History.**
  - Rows show "No. {id} · long date · time", the topic previews, and the counts. Previews come from `GET /api/digests` (D6) in the same single request; History makes no per-digest detail requests.
  - The rail shows Archive (hidden when empty) and "Kept as saved".
- **Sources.**
  - Add form (rule style). The URL input has `aria-describedby` set to the hint id, plus the error id in the error state with `aria-invalid="true"`.
  - Preview becomes `secondary` while a preview is open.
  - Rows show the `KindBadge`, a feed URL wrapped to 2 lines with `title`, the status chip (rate limited reads "Rate limited · try later"; "Possible gap" has an explanatory `title`), the time, and Delete.
  - Delete swaps the row for an inline confirmation in place of `window.confirm` (`Sources.tsx:83-92`).
  - The rail shows "What you can add" and Checks (Checks is hidden when there are no sources).
- **Settings.**
  - Three section rows (Model provider, Digest, YouTube). Step numbers are `aria-hidden`, followed by visually hidden "Step N: ".
  - The privacy note sits in the margin (columns 10–12).
  - A saved key shows "Saved key ending in {last4}" as text, with an empty input "Paste a new key to replace it" (`aria-describedby` links the saved text, the hint, and the error).
  - The caption risk note sits directly under its switch and is linked by `aria-describedby`.
  - Today's save flow and error copy are kept (`Settings.tsx:14-27,78-102`).

### D5. Accessibility mechanics
- **`lang` mapping.** `digest.language` stores the setting as chosen, which may be `original` or free text from "Other". A single helper maps it to a BCP 47 tag: `en` and `zh-Hans` map to themselves; free text maps through a small case-insensitive table of language names in English and in the language itself (for example "Japanese" or "日本語" to `ja`, "Français" to `fr`, "Traditional Chinese" or "繁體中文" to `zh-Hant`); `original`, `null`, and anything else get no `lang` attribute.
  - *Amended 2026-10-07 (tasks 11.4 and 12.2):* a value that is a well-formed BCP 47 tag with a supported primary language subtag is also accepted, in canonical case (for example `zh-hant` becomes `zh-Hant`). Names are looked up in a `Map`, so built-in object keys such as `constructor` are never treated as names.
- **The prototype's verified behaviors carry over:**
  - `lang` (D4)
  - focus moves (`useJump` for the skip link and the index)
  - `StatusRegion`
  - `Progress` names
  - linked hints and errors
  - reduced motion
  - switch hit area
  - stepper text
  - visible kind labels
- **Tests:**
  - `vitest-axe` runs `axe` on every page state in the tests, and fails on any violation.
  - A token test parses `tokens.css` and asserts the contrast pairs listed in the review (text ≥ 4.5:1, the switch boundary ≥ 3:1) for both themes. It is a port of the prototype check, with the correct cascade.

### D6. Snapshot fields and the digest list (backend)
- Alembic `0003`:
  - `digests.language` (String(40), nullable)
  - `digest_items.source_kind` (String(16), nullable)
- `digest/runner.py` writes `language` (the language read at run start, `runner.py:174-175`) and, for every saved digest item, the item's `Source.kind` at save time.
- `GET /api/digests/{id}` returns `language`, and `source_kind` on topic items and on Creator updates groups and items (`api/digests.py:26-70`).
- `GET /api/digests` also returns, for each digest, `language` and `topics` (the titles of its topics, in order; "Creator updates" is not included, and `creator_updates_only` is true when the digest has only Creator updates). It uses one query for the topics of all listed digests, not one per digest.
- Old rows return `null`; the UI then omits `lang` and the kind icon.
- Downgrade drops both columns.

### D7. Installable app and offline page
- `frontend/public/manifest.webmanifest`:
  - `name` and `short_name` "CatchUp", `start_url` and `scope` "/", `display: "standalone"`
  - `background_color: #f4f0e6`, `theme_color: #151412`
  - icons `icon-192.png`, `icon-512.png`, `icon-maskable-512.png` (`purpose: "maskable"`, mark inside the 80% safe zone), `icon-1024.png`
- `index.html` adds the manifest link, `theme-color` meta tags, and `apple-touch-icon` (`frontend/index.html:1-12`). The meta tags use `--bg` (light `#f4f0e6` with `media="(prefers-color-scheme: light)"`, dark `#161513` with `media="(prefers-color-scheme: dark)"`) so the window bar blends with the masthead once the page has loaded; the manifest `theme_color` applies before that.
- **Icon:**
  - The C7 mark is a `--fg` square with two `--bg` horizontal rules, like the prototype's `.logo`.
  - It is drawn by `frontend/scripts/make-icons.py`, a standard-library Python PNG writer (zlib, no dependencies), which also writes `icon.svg`.
  - The generated PNGs are committed, and the script is re-runnable.
- **`frontend/public/sw.js`** (about 40 lines, plain JS):
  - `CACHE = 'catchup-offline-v1'`
  - `install`: cache `/offline.html`, then `skipWaiting()`
  - `activate`: delete other caches, then `clients.claim()`
  - `fetch`: only for `request.mode === 'navigate'`, `fetch(request)`, and on a network error (rejection) respond with the cached `/offline.html`. Responses (4xx/5xx) pass through, and all other requests are not intercepted. It never calls `cache.put` for anything else, so app code and `/api` are never cached.
- **`frontend/public/offline.html`:** a self-contained page with inline CSS that uses the D2 tokens (both themes through `prefers-color-scheme`), the wordmark, the message and the two commands from the prototype, and a Reload button.
- **Registration:** in `main.tsx`, only when `import.meta.env.PROD` and `'serviceWorker' in navigator`, register `/sw.js` with scope `/`.
- **Serving:** no backend change. Vite copies `public/` to the `dist/` root, and the SPA fallback serves those files (`main.py:93-102`). The manifest MIME type was verified in research.

### D8. Tests and parity
- **Frontend tests:**
  - Existing tests are rewritten for the new copy and roles, with no lower coverage.
  - New tests per component, one test per prototype state per page, an axe scan in each, and the token test.
  - `sw.js` is tested in vitest by loading it with a fake `self`, `caches`, and `fetch`:
    - a navigation with a network error gets `offline.html`
    - API and asset requests are not intercepted
    - nothing besides `offline.html` is put in the cache
- **Backend tests:** the migration upgrades and downgrades, the runner writes the snapshot fields, the API returns them, and old rows return `null`.
- **Docker smoke** (`scripts/docker-smoke.sh`): `/manifest.webmanifest` returns 200 with `application/manifest+json`, `/sw.js` returns 200 with a JavaScript type, and `/offline.html` returns 200.
- **Parity review (Claude):**
  - screenshots of the prototype and the app side by side for every state, in both themes, at 1440 and 420 px
  - the D5 measurements again
  - a keyboard pass
  - Chrome installability (DevTools) and the offline page with the container stopped

## Risks / Trade-offs

- [Pixel drift from the prototype during porting] → the prototype is the reference, and parity screenshots and the D5 measurements are part of review. Tasks quote the prototype function and CSS for each part.
- [Global CSS naming collisions as the app grows] → one block per component, with class names prefixed by component, in `components.css`.
- [Tests coupled to copy] → copy comes from the prototype and is intentional. Tests use roles first and text second.
- [`subgrid` support] → supported in current Chrome, Edge, Safari, and Firefox. Narrow windows fall back to a single column regardless.
- [Service-worker mistakes can trap users on old code] → the worker caches only `offline.html`, has a test that nothing else is cached, and uses `skipWaiting` + `clients.claim` with a versioned cache name. To remove a broken worker, unregister it in DevTools; this is documented in the README.
- [CJK fallbacks differ by OS] → the stacks list macOS, Linux, and Windows faces. Review checks macOS; the others are documented as best effort.

## Migration Plan

- **Deploy:** migration `0003` runs at startup. Older digests show without a language mark or kind icons. The new frontend ships in the same image.
- **Rollback:** an image without the change ignores the new columns, or downgrade `0003`. An installed worker keeps serving only the offline page on network errors, which is harmless; unregister it if needed.

## Open Questions

- None blocking. Exact screenshots for the README install section are produced during the manual test.
