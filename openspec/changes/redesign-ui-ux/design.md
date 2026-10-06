# Design: redesign-ui-ux

Status: Proposal 1 chosen by the user on 2026-10-06. Open questions resolved as recommended:
- theme follows the system only (no setting)
- the edition number is the digest id
- `prototypes/` stays in the archived change as design evidence

## Solution Proposals

Context:
- **Request.** Turn the chosen visual direction, **C7 · Front page grid**, into the real React frontend, and make CatchUp installable as a PWA with an offline page (D-014, issue #24).
  - The prototype is `prototypes/directions/c7.html`: `shared/base.css` + `c.css` + `c3.css` + `c3b.css` + `c7.css`, with markup from `shared/render.js`.
  - It was refined by the Design plugin review; findings and fixes are in `design-review-c7.md`.
  - It covers six screens and 23 states, light and dark, and a 420 px window.
- **Research source:** `research.md`, sections:
  - Build and dependencies
  - Styling
  - each page section
  - API shapes consumed by the UI
  - Accessibility as implemented
  - Frontend tests
  - How the backend serves the frontend
  - External facts: installable PWA

### Shared by both proposals

- **Scope.**
  - The five pages are rebuilt to C7's structure and copy, plus the offline page: Generate, Sources, Settings, History, Digest (`frontend/src/pages/*.tsx`).
  - They keep today's routes (`frontend/src/App.tsx:8-31`) and the API client (`frontend/src/api/client.ts:1-31`).
  - No new API endpoints. The behaviors from the review are required:
    - compact digest masthead
    - content-driven item widths
    - state-aware rail
    - one primary action per state
    - caption risk note under its toggle
    - `lang` on generated text
    - focus moves for the skip link and the index
    - one `role="status"` region
    - AA tokens with distinct error and warn hues
    - delete confirmation
- **Two snapshot fields (backend).** A saved digest does not record its language, and digest items store only `source_name` (`backend/src/catchup/models.py:128-161`; `api/digests.py:26-70`). C7 needs both:
  - `lang` on summaries, because the digest language can change after saving
  - the source-kind icon and label on items and Creator updates

  Migration `0003` adds `digests.language` and `digest_items.source_kind`, filled at save time (`digest/runner.py`, where the language is read at `:174-175`). Old rows stay NULL: the UI then omits `lang` and the icon. `GET /api/digests/{id}` returns both.
- **Theme.** Follow `prefers-color-scheme` by default. Light and dark tokens are taken from `c3.css` with the review's fixes (light `--subtle #66625a`, error `#a33a00`, warn `#6b5e00`; dark `#ff9a62` / `#d9c25a`).
- **Fonts.** System stacks only, with the C7 CJK fallbacks. Nothing is bundled, because CJK web fonts are tens of MB.
- **PWA shell.**
  - `frontend/public/manifest.webmanifest`: `name`/`short_name` "CatchUp", `start_url: "/"`, `display: "standalone"`, theme and background colors from the tokens.
  - Icons: 192 px, 512 px, a maskable 512 px, and a 1024 px Safari icon from one SVG wordmark (the C7 "C").
  - A `<link rel="manifest">` and `theme-color` in `index.html` (`frontend/index.html:1-12`).
  - Vite copies `public/` into the `dist/` root, and the SPA fallback already serves root files with the right MIME types (`backend/src/catchup/main.py:93-102`; research verified `.webmanifest` → `application/manifest+json` in the published image).
  - `/api/*` is never cached.
  - Specs: new capability **`user-interface`** (layout, states, primary actions, accessibility, themes); **`local-deployment`** modified (installable, offline page); **`digest-history`** modified (a saved digest keeps its language and source kinds).
- **Tests.** Existing vitest tests select by role and text (research, "Frontend tests"), so they are rewritten with the new copy, not deleted. New checks:
  - an automated axe scan per page state (`vitest-axe`, dev only)
  - a token contrast test that fails below 4.5:1 for text and 3:1 for UI boundaries, a port of the prototype check
  - Docker smoke additions: `/manifest.webmanifest` 200 with the manifest MIME type; `/sw.js` 200

---

### Proposal 1 — Port the prototype CSS as a hand-written design system; hand-written minimal service worker

- **Overview.** Flatten C7's five-file cascade into a small, owned stylesheet set: tokens, base, layout grid, components. Build a dozen small React components that reproduce the prototype markup.
  - No runtime dependencies are added; the app stays React + React Router.
  - The service worker is about 40 lines and only serves an offline page when a navigation fails. It never caches the app or the API.
- **Key Changes:**
  - **Styles.** `frontend/src/styles/` replaces the 4-line `style.css` (`frontend/src/style.css:1-4`):
    - `tokens.css`: light/dark custom properties, fonts, spacing; no hard-coded colors elsewhere
    - `base.css`: element defaults, focus ring, `sr-only`, reduced motion
    - `layout.css`: the 78rem container and 12-column grid with subgrid section rows, the rail, the compact masthead, and container queries at 900 px and 640 px
    - `components.css`
  - **Components** in `frontend/src/components/`:
    - `AppShell` (masthead, nav with `aria-current`, skip link that moves focus)
    - `SectionRow`, `Rail`, `Button`, `Chip`/`Badge`, `Alert`, `Switch` (native checkbox with `role="switch"`), `Stepper`, `Progress`
    - `StatusRegion` (one persistent `role="status"`)
    - `SummaryText` (keeps today's bullet handling, `DigestView.tsx:35-50`)
    - `ReasonLabel`
  - **Pages.** The five pages and states are rebuilt to `render.js`. Data comes from today's endpoints. The rail and empty states are computed from the same responses: model configured, sources by `kind`, last digest from `GET /api/digests`.
  - **Service worker.** `frontend/public/sw.js`:
    - `install` caches `/offline.html`, which is a static page with inline CSS
    - `fetch`: for `navigate` requests, try the network and fall back to `offline.html`; other requests pass through
    - registered in `main.tsx` only in production builds

    The app shell is not precached, so an update is just a reload and stale assets are impossible.
  - **Backend.**
    - Migration `0003`, with the snapshot fields written in `runner.py` and returned by `api/digests.py`.
    - No change to static serving.
- **Trade-offs:**
  - **Benefits:**
    - The verified prototype CSS (contrast, small caps, grid) carries over almost one to one, so the review's measurements stay valid.
    - Zero new runtime dependencies, which fits the about 620-line codebase (research, "Build and dependencies").
    - The service worker cannot serve stale code or touch the API.
    - Easy to review and for Droid to follow, because the prototype is the spec.
  - **Costs:**
    - We own accessibility details that a library would provide. That is acceptable here, because the widgets are simple: a native switch, an inline confirm row, no dialogs, menus, or popovers.
    - Global CSS needs naming discipline.
    - Without a precache, the installed window shows the offline page, not a cached UI, when the server is down. That matches the product: nothing works without the backend.
- **Validation:**
  - vitest component and page tests for every prototype state, plus axe scans and the token contrast test.
  - `npm run build`.
  - Docker smoke checks the manifest, `sw.js`, and the offline page.
  - Review (Claude): side-by-side screenshots of prototype vs app for each state at 1440 and 420 px, in both themes. Also a keyboard pass (skip link, index, settings), and JS measurements of the review's metrics: first topic within 50% of a 900 px viewport, header ≤ 120 px at 420 px, 12+ `lang` elements on the zh digest.
  - Manual test with the user:
    - install in Chrome and add to the Dock in Safari
    - stop the container and reopen the app: the offline page appears
    - start it again and reload: the app returns
    - real digest reading in zh-Hans
- **Open Questions:**
  - Manual theme override in Settings, or system only? System only is proposed; it adds no setting.
  - Should the edition number be the digest id? Ids are sequential, and digests are never deleted.
  - Keep `prototypes/` after implementation? It is proposed to stay in the archived change as design evidence.

---

### Proposal 2 — Component-scoped styles with headless accessible primitives and a generated PWA

- **Overview.**
  - Rebuild the UI as CSS Modules per component, with design tokens in one shared file.
  - Use Radix UI primitives for interactive widgets: Switch, AlertDialog for delete confirmation, Tooltip for "Possible gap", Toast for saved messages.
  - Generate the PWA with `vite-plugin-pwa` (Workbox): precache the app shell, show a runtime offline fallback, and generate the icon set with `@vite-pwa/assets-generator`.
- **Key Changes:**
  - **Styling and components.**
    - `*.module.css` per component, plus `tokens.css`.
    - Components similar to Proposal 1, but built on `@radix-ui/react-switch`, `-alert-dialog`, `-tooltip`, and `-toast`.
    - Delete becomes a modal dialog instead of the prototype's inline confirm row.
  - **PWA.**
    - `vite-plugin-pwa` in `frontend/vite.config.ts:1-15` with `registerType: 'prompt'`.
    - The app shell is precached. A `NetworkOnly` rule covers `/api/*`, and an offline fallback is shown for navigations.
    - An "Update available — reload" toast is shown when a new build is deployed.
    - The manifest and icons are generated at build time.
  - **Backend:** same as shared (migration `0003`).
  - **Dependencies:** about 5 runtime packages and 2 dev packages added to `frontend/package.json`.
- **Trade-offs:**
  - **Benefits:**
    - Battle-tested focus management and ARIA for dialogs, tooltips, and toasts.
    - Scoped CSS avoids global naming collisions as the app grows.
    - An installed window opens instantly from the precache.
    - Icon generation is automated.
  - **Costs:**
    - The prototype's CSS must be translated into per-component modules, so the reviewed cascade is re-expressed and the review's measurements must be re-verified rather than carried over.
    - Workbox precache adds the stale-app risk. An old shell can talk to a new API after an upgrade, so this needs an update prompt and testing.
    - Dependencies grow for a local single-user app; the bundle grows and there are more upgrade chores.
    - A modal delete dialog departs from the reviewed inline pattern.
    - With the backend down, a precached UI still loads and then fails every request, which is arguably more confusing than an honest offline page.
- **Validation:**
  - Everything in Proposal 1.
  - Workbox update-flow tests: a build, then a second build, then the prompt and the reload.
  - Radix components in vitest with user-event.
  - Lighthouse installability.
  - Checks that `/api` responses are never cached (DevTools Application panel, during review).
- **Open Questions:**
  - Is the precache wanted at all, given that nothing works offline?
  - Should the dialog replace the inline confirm, and how does it interact with the reviewed copy?
  - Which Radix version supports React 19.3? To be checked before planning.

---

Recommendation: Proposal 1.
- C7 was designed and verified as plain CSS, with measured contrast, focus behavior, and grid alignment. Porting it directly keeps those results, adds no runtime dependencies, and suits a small local app.
- A network-first service worker with only an offline page gives the D-014 install experience without the stale-shell problems that a precaching PWA brings for an app that cannot work offline anyway.
