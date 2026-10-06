# Research: Current frontend UI/UX and what an installable PWA needs (#24)

- Date: 2026-10-05
- Query: How is the CatchUp frontend built and presented today (pages, routing, styling, data, states, copy, accessibility, build, tests, backend serving), which API shapes does it consume, and what does an installable PWA require in this setup (D-014)?
- Git ref: main @ 799bee6
- Change: `redesign-ui-ux`
- Issue: [#24](https://github.com/Zhuoang2/catchup/issues/24)

## Summary

The frontend is a React 19 + React Router 7 single-page app built with Vite 8 and TypeScript 7. It has five routes (Generate, Sources, Settings, History, Digest), no shared components, and about 620 lines of non-test code. Its only styling is a 4-line global stylesheet (system font, 64 rem centered column, blue links), so pages render as plain semantic HTML.

All server state is fetched with a small `request()` wrapper over `fetch('/api…')`. Each page holds its own state with `useState`/`useEffect`. The run page polls every second while a run is active.

The FastAPI backend serves the built `dist/` (an `/assets` mount plus an SPA fallback that also serves any other file in `dist/`) behind an allowed-Host middleware. There is no web app manifest, icon, service worker, `public/` directory, or dark-mode styling.

Chrome and Edge install a site that has a manifest (name, 192/512 px icons, `start_url`, a standalone-type `display`) served from a secure context, and `http://localhost`/`127.0.0.1` count as secure. Safari on macOS can add any site to the Dock. Firefox desktop does not install PWAs on macOS.

## Detailed Findings

### Build and dependencies
- `package.json` scripts: `dev` (vite), `build` (`tsc --noEmit && vite build`), `test` (vitest) — `frontend/package.json`.
- Locked versions (`frontend/package-lock.json`):
  - runtime: react / react-dom 19.3.0, react-router-dom 7.18.4
  - build: vite 8.3.2, @vitejs/plugin-react 6.1.1, typescript 7.0.2
  - test: vitest 4.1.11, jsdom 26.1.0
- The only runtime dependencies are react, react-dom, and react-router-dom. There is no UI, CSS, icon, or state library.
- Vite config: the React plugin, a dev proxy `/api` → `http://127.0.0.1:8000`, and vitest with jsdom plus `src/test/setup.ts` (jest-dom, cleanup) — `frontend/vite.config.ts:1-15`, `frontend/src/test/setup.ts:1-5`.
- TypeScript: strict, ES2022, `jsx: react-jsx`, `types: ["vite/client"]` — `frontend/tsconfig.json:1-15`.
- `index.html`: `lang="en"`, charset, viewport, `<title>CatchUp</title>`, and `#root`. There is no favicon, theme-color, or manifest link — `frontend/index.html:1-12`.
- There is no `frontend/public/` directory.

### App shell and routing
- `App` wraps `BrowserRouter`:
  - a `<header>` with `<h1>CatchUp</h1>`
  - `<nav aria-label="Main">` with links Generate `/`, Sources `/sources`, Settings `/settings`, History `/digests`
  - `<main>` with `Routes`, including `/digests/:id` for DigestView
  - `frontend/src/App.tsx:8-31`
- There is no active-link styling, 404 route, layout component, or document title per page.
- Entry: `createRoot(...).render(<App />)` and `import './style.css'` — `frontend/src/main.tsx:1-5`.

### Styling
- All CSS — `frontend/src/style.css:1-4`:
  - `body`: margin 0, `system-ui, sans-serif`, color `#172331`, background `#f8fafc`
  - `header, main`: `max-width: 64rem`, auto margins, 1 rem padding
  - `nav`: flex, 1.5 rem gap
  - `a`: `#165cac`
- One inline style: `white-space: pre-line` on summary paragraphs — `frontend/src/pages/DigestView.tsx:48`.
- There are no CSS variables, dark mode (`prefers-color-scheme`), or responsive rules beyond the max-width. No fonts are loaded (system fonts only).

### API client
- `request<T>(path, options)` fetches `/api${path}`. On a non-2xx response it throws `ApiError(code, message, status, retryAfter)` from the body `{error: {code, message, retry_after?}}`, falling back to `request_failed` and "Request failed (N)". It returns `undefined` on 204 — `frontend/src/api/client.ts:1-31`.
- Backend error envelope: `{"error": {"code", "message", ...details}}` — `backend/src/catchup/errors.py:17-20`.

### Generate page (`/`) — `frontend/src/pages/Generate.tsx`
- **Loading.** On mount it fetches `GET /api/digest-runs/active` (`:37-43`). When a run is active it polls `GET /api/digest-runs/{id}` every 1000 ms (`:45-53`).
- **Button.** "Generate Digest" (`POST /api/digest-runs`) is disabled while a run is active (`:78`).
- **Start errors:**
  - `run_active` → refetch the active run
  - `model_not_configured` → "Set up your model in Settings first." with a link
  - other errors → their message (`:55-73,79-80`)
- **Run section** (`:81-110`):
  - "Stage: {status}" shows the raw status value: `queued`, `collecting`, `summarizing`, `grouping`, `succeeded`, `failed`, `no_new_content`.
  - While collecting: "Sources checked: N of M". Otherwise: "Items summarized: N of M".
  - `no_new_content` → "No new content."
  - "{n} items waiting for transcripts or captions" and "{n} videos deferred to the next run", each shown when non-zero.
  - On succeeded, failed, or no_new_content: "Tokens: N in / M out", or "Tokens: not reported".
  - `failed` → the error message (role alert). `succeeded` → a "View digest" link.
  - "Source checks" list: "{title}: {status}", or "rate limited (try later)", plus " (possible gap)" and ": {error}".
- The page shows no history or last digest when no run is active, and no time or duration.

### Sources page (`/sources`) — `frontend/src/pages/Sources.tsx`
- **Form.** "Website or feed URL" (`type=url`, required, placeholder `https://example.com`) with a "Preview" button. Editing the URL clears the preview (`:97-102`).
- **Error copy** by code (`:16-32`):
  - `invalid_url`, `blocked_address`, `fetch_failed`, `no_feed`, `not_a_feed`
  - `rate_limited`, with "about N seconds" when known
  - fallback: the server message (for example the duplicate message naming the source)
  - "Could not connect to CatchUp."
- **Preview** (`:105-129`):
  - title, then "Feed:" and "Site:" links
  - "Source type: YouTube channel / Podcast / Website feed"
  - podcast → "Transcripts published by the show"
  - YouTube → captions on ("Captions fetched from YouTube on this computer") or off ("Caption fetching is off; videos will be listed without summaries")
  - whole-site or whole-show notice
  - up to 5 entries with link and local date
  - a "Confirm source" button
- **After confirm.** "Source saved." (role status), then the list refreshes (`:66-81`).
- **Saved sources** (`:130-143`):
  - "Loading sources…", or "No sources added yet."
  - Each row: bold title, feed URL link, "Last check: {status | Never checked} ({local datetime})", "Rate limited", "Possible gap", and a "Delete {title}" button.
  - Delete uses `window.confirm("Delete X? Saved digests will remain available.")`.
- The list type has no `kind`, although the API returns it (`:10-14`). There is no source count and no editing.

### Settings page (`/settings`) — `frontend/src/pages/Settings.tsx`
- **Loading.** It loads `GET /api/settings/model` and `GET /api/settings/preferences` together, showing "Loading settings…" (`:43-59,107`).
- **One form** (`:108-132`):
  - the privacy line "Content will be sent to your configured model provider."
  - "Provider base URL", defaulting to `https://api.deepseek.com`
  - "API key" (password, placeholder `•••• {last4}` when set)
  - a "Test connection" button
  - "Model" select, filled from the test result
  - "Digest language" select: English / 简体中文 / Same as original / Other, with a text input
  - "Fetch captions locally" checkbox with the ToS paragraph, and a "Skip Shorts" checkbox
  - one "Save" button
- **Messages** (`:72,98,14-27`):
  - "Connection succeeded. Choose a model and save."
  - "Settings saved."
  - error copy for `auth_failed`, `connection_failed`, `insufficient_balance`, `rate_limited`, `provider_error`, `secret_not_configured`
- Save makes two sequential PUTs, model then preferences (`:78-102`).
- There is no first-run onboarding, step order, or grouping into sections.

### History page (`/digests`) — `frontend/src/pages/History.tsx`
- `GET /api/digests`: "Loading digests…", an error, or "No saved digests yet." (`:17-31`).
- Each row: a local datetime link to `/digests/{id}`, "N item(s)", "M source(s)" (`:32-42`).
- There are no titles or topic previews per digest.

### Digest page (`/digests/:id`) — `frontend/src/pages/DigestView.tsx`
- `GET /api/digests/{id}` (`:57-63`).
- **Header:** "Digest", "Created {local datetime}", "Tokens: N in / M out" or "not reported" (`:67-76`).
- **Topics:** `<h3>` title, overview paragraph, then items (`:77-95`). Each item shows:
  - a title link (new tab, `noopener`)
  - source name · local datetime
  - the summary, or "Summary unavailable"
- **`SummaryText`:** splits on newlines. Runs of "- " lines become `<ul>`; other lines become `<p>` with `pre-line` (`:35-50`). Long transcripts produce an overview paragraph plus 3–6 bullets.
- **Creator updates** (`:96-114`): the section "Creator updates", with `<h4>` per source. Each item: title link · datetime, then a reason label:
  - "Caption fetching is off"
  - "This video has no captions"
  - "Blocked by YouTube"
  - "Captions could not be fetched"
  - "No transcript within N days" (`:24-33`)
- The page has no table of contents, item counts, source filter, read state, or back link.

### API shapes consumed by the UI
- `GET /api/digest-runs/active` → a run, or `null`. `POST /api/digest-runs` → 202 with a run. `GET /api/digest-runs/{id}` → run. A run has (`backend/src/catchup/digest/runner.py:369-388`):
  - `id`, `status`, `items_total`, `items_done`, `error_kind`, `error_message`, `digest_id`
  - `waiting_count`, `deferred_count`, `prompt_tokens`, `completion_tokens`
  - `started_at`, `finished_at`, `sources_total`
  - `source_checks[]`: `source_id`, `source_title`, `status`, `possible_gap`, `error`, `http_status`, `rate_limited`
- `POST /api/sources/preview` (`backend/src/catchup/api/sources.py:60-87`) → `feed_url`, `site_url`, `title`, `follows_site_feed_notice`, `kind`, `captions_enabled`, and `entries[≤5]` (`title`, `link`, `published_at`).
- `POST /api/sources` → 201 with `id`, `title`, `site_url`, `feed_url`, `kind`, `last_check_at`, `last_check_status`, `possible_gap` (`sources.py:157-161`).
- `GET /api/sources` → a list of `id`, `title`, `feed_url`, `kind`, `site_url`, `last_check_at`, `last_check_status`, `possible_gap`, `http_status`, `rate_limited` (`sources.py:164-181`). `DELETE /api/sources/{id}` → 204.
- `GET /api/digests` → a list of `id`, `created_at`, `item_count`, `source_count` (`backend/src/catchup/api/digests.py:14-23`).
- `GET /api/digests/{id}` (`digests.py:26-70`) has:
  - `id`, `created_at`, `model_id`, `prompt_tokens`, `completion_tokens`, `transcript_wait_days`
  - `topics[]`: `title`, `overview`, `items[]` (`title`, `link`, `source_name`, `published_at`, `summary`, `summary_unavailable`)
  - `creator_updates[]`: `source_name`, `items[]` (`title`, `link`, `published_at`, `reason`)
- `GET/PUT /api/settings/model` → `base_url`, `model_id`, `key_set`, `api_key_last4`. `POST /api/settings/model/test` → `{ok, models[]}`. `GET/PUT /api/settings/preferences` → `digest_language`, `youtube_captions`, `youtube_skip_shorts`, with all PUT fields optional (`backend/src/catchup/api/settings.py:77-160`).

### Accessibility as implemented
- Semantic landmarks are present (`header`, `nav aria-label="Main"`, `main`, `section aria-label`), along with `role="alert"` for errors and `role="status"` for confirmations, labels wrapping inputs, and `<time dateTime>`.
- Missing:
  - focus styles beyond browser defaults, and a skip link
  - `aria-current` on nav, and `aria-live` on run progress (the stage text updates every second without a live region)
  - visible distinction between link and button roles
- Dates use `toLocaleString()` and `toLocaleDateString()` with the browser locale. UI copy is English only, while summaries and topic titles follow the digest language (for example zh-Hans).

### Frontend tests
- 35 vitest tests in 6 files cover these behaviors:
  - **App, History:** nav links; history list, empty, and error states
  - **Digest:** topics, safe links, unavailable digest, Creator updates labels, key-point lists, mixed prose and bullets
  - **Generate:** resume progress, rate-limited labels, follow progress to the digest link, no new content with failures, the model-not-configured link, provider failure, the run-active conflict
  - **Settings:** captions and Shorts defaults with the risk notice, key not revealed, model options from a test, auth error copy, other-language input
  - **Sources:** preview with scope notice, duplicate error, rate-limited preview and confirm, outcomes and gaps, delete confirmation

  Files: `frontend/src/App.test.tsx`, `frontend/src/pages/*.test.tsx`.
- Tests select by role, label, and text, so copy and roles are part of the tested contract.

### How the backend serves the frontend
- `create_app()` (`backend/src/catchup/main.py:83-102`):
  - It resolves `frontend_dist` (argument, then `CATCHUP_FRONTEND_DIST`, then `frontend/dist` in a source checkout) and serves it only when `index.html` exists.
  - It mounts `/assets` with StaticFiles.
  - A middleware turns other 404s outside `/api` and `/assets` into the matching file in `dist/` (path-contained), else `index.html`.

  So files Vite copies from `public/` to the `dist/` root (for example `/manifest.webmanifest`, `/sw.js`, icons) are served at the root.
- The allowed-Host middleware rejects requests whose Host is not in `CATCHUP_ALLOWED_HOSTS` (default `localhost,127.0.0.1,[::1]`) with 400 `invalid_host` (`main.py:50-77`).
- MIME types (Python `mimetypes`, which `FileResponse` uses): `.webmanifest` → `application/manifest+json`, on the host and in the published `ghcr.io/zhuoang2/catchup:edge` image. `.js` → `text/javascript`, `.png` → `image/png`.
- The Docker image serves the built frontend from `/app/frontend` (`CATCHUP_FRONTEND_DIST`), and compose binds `127.0.0.1:8000` (`local-deployment` spec; `compose.yaml`).

## External facts: installable PWA (checked 2026-10-05)
- **Chrome and Edge desktop** (https://web.dev/articles/install-criteria, updated 2024-09-19):
  - The manifest needs `short_name` or `name`, 192 px and 512 px icons, `start_url`, and `display` of `fullscreen`, `standalone`, `minimal-ui`, or `window-controls-overlay`. `prefer_related_applications` must be absent or false.
  - The page must be served over HTTPS (secure context).
  - Engagement: at least one click, and 30 seconds on the page.
  - A service worker is not listed as a requirement.
- **Secure contexts** (https://developer.mozilla.org/en-US/docs/Web/Security/Secure_Contexts): resources from a loopback address are secure, including `http://localhost` and `127.0.0.0/8`. `http://localhost:8000` and `http://127.0.0.1:8000` are different origins, so each is installed separately.
- **Safari on macOS** (Sonoma and later) can "Add to Dock" any website; a manifest only customizes the result. Apple recommends an opaque, full-bleed square icon (SVG, or 1024×1024 bitmap); `start_url` and `scope` decide which links stay in the app window (https://support.apple.com/en-us/104996; WWDC23 "What's new in web apps", via search summaries).
- **Firefox desktop** does not install PWAs from a manifest. "Taskbar tabs" are being tested on Windows only; there is no macOS support announced (MDN "Making PWAs installable"; news reports 2025–2026, via search summaries).
- **Offline page.** Showing a page while the backend is down requires a service worker that serves a cached page. Without one, an installed window shows the browser's connection error when the server is not running.

## Code References
- `frontend/package.json`, `frontend/package-lock.json` — dependencies and versions
- `frontend/vite.config.ts:1-15`, `frontend/tsconfig.json:1-15`, `frontend/index.html:1-12` — build and entry
- `frontend/src/style.css:1-4` — all global styles
- `frontend/src/App.tsx:8-31` — shell, nav, routes
- `frontend/src/api/client.ts:1-31` — fetch wrapper and `ApiError`
- `frontend/src/pages/Generate.tsx:30-113` — run start, polling, states, source checks
- `frontend/src/pages/Sources.tsx:16-146` — add, preview, confirm, list, delete, error copy
- `frontend/src/pages/Settings.tsx:12-138` — model, language, YouTube options, messages
- `frontend/src/pages/History.tsx:12-45` — digest list
- `frontend/src/pages/DigestView.tsx:24-119` — topics, summaries, key points, Creator updates
- `backend/src/catchup/main.py:50-102` — allowed hosts, static assets, SPA fallback
- `backend/src/catchup/digest/runner.py:369-388` — run detail shape
- `backend/src/catchup/api/sources.py:60-181`, `api/digests.py:14-70`, `api/settings.py:77-160` — response shapes
- `backend/src/catchup/errors.py:17-20` — error envelope

## Current Specs
- `digest-generation`:
  - "Start a digest run on demand" (one active run; refuse with the active run)
  - "Show run progress and per-source outcomes" (stage, N of M, outcomes)
  - "No digest when nothing is new" (message plus waiting/deferred counts)
  - "Summaries focus on substance" (2–4 sentences; long transcripts as overview plus key points)
  - "Creator updates" (section after topics, grouped by source, reasons)
  - "Report model token usage" (totals; 0 without calls; "not reported")
  - "Require model setup before generating"
- `source-management`:
  - "Preview a source from a pasted URL" (title, feed and site URL, kind, transcript method, 5 entries, scope notices)
  - "Explain unsupported and duplicate sources"
  - "Confirm and save a source"
  - "List and delete sources" (title, feed URL, last outcome and time; deleting keeps digests)
- `digest-history`: "List saved digests"; "Reopen a saved digest" (topics, summaries, Creator updates as saved).
- `model-settings`: "Configure an OpenAI-compatible provider"; "Test the connection and list models"; "Protect the stored API key" (key never shown back).
- `transcripts`: "Opt in to fetching YouTube captions locally" (off by default; the setting states the ToS conflict); "Skip YouTube Shorts by default".
- `local-deployment`: "Local-only access by default"; "Report health".

## Related History
- The UI was scaffolded in `0da6d26` (add-core-digest-flow) and extended per change. `style.css` has not changed since the scaffold.
- D-006: React/Vite/TypeScript served by FastAPI in one container. D-011: local deployment only. D-014: local web app, installable as a PWA, no native packaging.
- The manual test of `add-podcast-and-video-sources` (2026-10-05) used these pages. The user's screenshots show the unstyled layout: raw status values such as "Stage: no_new_content", default form controls, and plain lists.
