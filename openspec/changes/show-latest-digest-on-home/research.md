# Research: Show the latest digest on the main screen

- Date: 2026-10-16
- Query: How do the main screen (`/`, Generate), the digest reading view (`/digests/:id`), and History (`/digests`) work today? What backend data can identify the latest digest? Which specs, accessibility behavior, and tests constrain these screens? Input: GitHub issue #27, "Show the latest digest on the main screen". Related: issue #25, single-item topic layout.
- Git ref: main @ 98f651b

## Summary
`/` renders the Generate page. On load it makes four requests: model settings, sources, the full digest list, and the active run. It derives one of seven run states from them, shows the matching primary action, a run card or result card, and a rail. It reaches the latest digest only through links built from the first entry of `GET /api/digests`, never by fetching the digest's content. The reading layout lives in `DigestView.tsx`, in an unexported `DigestBody` component that renders a whole `.page.page-digest` section with its own `<h1>`. It loads the digest by route id from `GET /api/digests/{id}`. The backend has no "latest digest" or "last run" endpoint: the list is ordered newest first and has no limit, and a finished run can be fetched only by its id. Runs are announced through one persistent `role="status"` region on Generate. Specs fix one primary action per state, the rail's content, the digest reading layout, and per-screen document titles.

## Detailed Findings

### Routing, navigation, and document titles
- Routes: `/` → `Generate`, `/sources`, `/settings`, `/digests` → `History`, `/digests/:id` → `DigestView` — `frontend/src/App.tsx:13-19`.
- Navigation items: Generate (`/`), Sources, History (`/digests`), Settings — `frontend/src/components/AppShell.tsx:7-12`.
- `data-screen` is `digest` for `/digests/<id>`, `history` for `/digests`, `sources`, `settings`, and `generate` for anything else, including `/` — `frontend/src/components/AppShell.tsx:17-19`.
- History gets `aria-current="page"` on both `/digests` and a digest page — `frontend/src/components/AppShell.tsx:28-29`.
- The brand links to `/` — `frontend/src/components/AppShell.tsx:24`.
- The masthead shows today's date — `frontend/src/components/AppShell.tsx:25`.
- `.app[data-screen="digest"]` makes the masthead a compact single row and hides the date line. This is the only CSS that uses `data-screen` — `frontend/src/styles/layout.css:47-50`.
- `useDocumentTitle` sets `` `${title} · CatchUp` `` — `frontend/src/components/useDocumentTitle.ts:3-6`.
  - Generate passes `'Generate'` — `frontend/src/pages/Generate.tsx:57`.
  - History passes `'History'` — `frontend/src/pages/History.tsx:16`.
  - DigestView passes `No. {id} · {short date}`, or `'Digest'` while loading or on error — `frontend/src/pages/DigestView.tsx:108-109`.
- The PWA starts at `/`: `"start_url": "/"` and `"scope": "/"` — `frontend/public/manifest.webmanifest:4-5`.
- The backend serves `index.html` for any non-API 404 path, so `/` and `/digests/:id` both load the SPA — `backend/src/catchup/main.py:88-102`.

### Generate page (`/`)
- **Data loading.**
  - On mount it makes four requests through `Promise.allSettled`: `/settings/model`, `/sources`, `/digests`, `/digest-runs/active` — `frontend/src/pages/Generate.tsx:65-84`.
  - A rejected request sets one "Could not load some page details" alert — `frontend/src/pages/Generate.tsx:78-81`.
  - If the settings request fails, `modelReady` is treated as `true` — `frontend/src/pages/Generate.tsx:74`.
  - The digest list is held as `Digest = { id, created_at, item_count, source_count }`, which ignores the extra list fields — `frontend/src/pages/Generate.tsx:20`, `:61`.
- **Polling.** While the run is active it polls `/digest-runs/{id}` every 1000 ms — `frontend/src/pages/Generate.tsx:86-100`.
  - Active statuses are `queued`, `collecting`, `summarizing`, `grouping` — `frontend/src/pages/Generate.tsx:29`.
  - A poll failure shows "Could not check digest progress". The next successful poll clears it — `frontend/src/pages/Generate.tsx:93-97`.
- **After success.** When the run status becomes `succeeded`, the page refetches `/digests` to refresh the last-digest links. A failure shows "Could not refresh digest history" — `frontend/src/pages/Generate.tsx:102-111`.
- **Starting a run.** `generate()` POSTs `/digest-runs` — `frontend/src/pages/Generate.tsx:113-127`.
  - On `run_active` it refetches `/digest-runs/active`.
  - On `model_not_configured` it switches to first run.
  - Other errors show "Could not start digest".
- **States.**
  - The state is derived as `first-run` when `modelReady === false`, otherwise `run?.status ?? 'idle'` — `frontend/src/pages/Generate.tsx:129-132`.
  - No sources yet is `modelReady === true && sources?.length === 0 && !run` — `frontend/src/pages/Generate.tsx:131`.
  - Configuration errors are `auth_failed`, `insufficient_balance`, `model_not_configured`, `connection_failed` — `frontend/src/pages/Generate.tsx:30`, `:133`.
- **Hero.** It is `PageHead` with title "Generate digest", a lede counting sources, and `className="hero"` — `frontend/src/pages/Generate.tsx:147-151`.
  - Its actions per state are in `frontend/src/pages/Generate.tsx:152-169`:
    - First run: "Set up your model" (primary) and Generate disabled with a reason.
    - No sources: "Add sources" (primary) and Generate disabled with a reason.
    - Otherwise: a Generate button.
  - The Generate button is primary when running, idle, or failed without a configuration error, and secondary otherwise — `frontend/src/pages/Generate.tsx:163`.
  - The button reads "Generating…" while running and "Try again" after a failure — `frontend/src/pages/Generate.tsx:165`.
- **The hero "Last digest" line.** It reads "No. {id} · {shortDateTime}" and links to `/digests/{id}`, using `digests[0]` — `frontend/src/pages/Generate.tsx:142-144`.
  - It is shown in the no-sources and normal states — `frontend/src/pages/Generate.tsx:161`, `:167`.
  - CSS hides it on wide windows and shows it only at container widths of 900 px or less — `frontend/src/styles/components.css:73`, `:169`.
- **Run card.** While running it shows a Stepper, a Progress bar with an accessible label, and the source checks — `frontend/src/pages/Generate.tsx:176-186`.
- **Result card (succeeded).** It shows "Your digest is ready", the saved item count and split (`savedItems`), the source count, and the tokens — `frontend/src/pages/Generate.tsx:187-196`, with `savedItems` at `:21-28`.
  - "View digest" links to `/digests/{run.digest_id}` as the primary button.
  - Held notes and source checks follow.
- **No new content.** An info result with no primary action, plus held notes and checks — `frontend/src/pages/Generate.tsx:197-203`.
- **Failed.** An error `Alert` with `announce={false}`, so it has no `role="alert"`. It adds "Check settings" for configuration errors. A card explains what was kept — `frontend/src/pages/Generate.tsx:204-217`.
- **Status region.** One persistent region holds the run text: "Checking sources, N of M", "Summarizing, N of M", "Digest ready: …", "No new content", or "Digest generation failed: …" — `frontend/src/pages/Generate.tsx:134-140`, `:218`.
- **Rail.**
  - First run: Getting started steps — `frontend/src/pages/Generate.tsx:219-223`.
  - Otherwise: a "Last digest" box ("No. {id} · {dateTime}", items, sources) when one exists, and "Your sources" with counts by kind — `frontend/src/pages/Generate.tsx:225-235`.
  - Always: "How it works" — `frontend/src/pages/Generate.tsx:237-239`.
- **What the page does not do.** It never requests `GET /api/digests/{id}`. Digest content is reachable only through the links above. A completed run is shown only for the current visit: `run` comes from `/digest-runs/active`, which returns `null` once no run is active, so a reload after success shows the idle state — `frontend/src/pages/Generate.tsx:71`, `:77`; `backend/src/catchup/api/runs.py:21-24`.

### Digest reading view (`/digests/:id`)
- **Loading.** `DigestView` reads `id` from the route, resets its state, and fetches `/digests/{id}` — `frontend/src/pages/DigestView.tsx:104-118`.
  - On error it shows "Could not load digest" with an alert paragraph and "← All digests" — `frontend/src/pages/DigestView.tsx:119-122`.
  - While loading it shows "Loading digest…" — `frontend/src/pages/DigestView.tsx:123`.
- **`DigestBody` is internal and not exported** — `frontend/src/pages/DigestView.tsx:38`; the only export is `DigestView` at `:104`.
  - It returns a full `<section className="page page-digest">` with its own `PageHead`, which renders an `<h1>` — `frontend/src/pages/DigestView.tsx:42-51`; `frontend/src/components/ui.tsx:4-10`.
  - The headline has the eyebrow "Digest · No. {id}" and the title "{long date} · {time}" — `frontend/src/pages/DigestView.tsx:43-44`.
  - The meta line shows items, sources, model, and tokens — `frontend/src/pages/DigestView.tsx:45-46`.
  - A digest with only Creator updates gets a note that nothing could be summarized — `frontend/src/pages/DigestView.tsx:47-49`.
  - The head ends with "← All digests" — `frontend/src/pages/DigestView.tsx:50`.
- **Index.** "In this digest" appears when there is more than one section — `frontend/src/pages/DigestView.tsx:41`, `:53-61`.
  - Its links move focus with `useJump` — `frontend/src/pages/DigestView.tsx:29-32`; `frontend/src/components/useJump.ts:3-11`.
- **Topics.** Each topic is a `SectionRow` (`section.topic`, `h2.topic-title`) — `frontend/src/pages/DigestView.tsx:63-79`; `frontend/src/components/ui.tsx:12-23`.
  - An item is "wide" when its summary is longer than 140 characters or has a "- " line — `frontend/src/pages/DigestView.tsx:66`.
- **Creator updates.** Grouped by source, each item with its reason — `frontend/src/pages/DigestView.tsx:80-98`.
- **Language.** Generated text carries `lang` from `digestLang(digest.language)` — `frontend/src/pages/DigestView.tsx:39`, `:56`, `:64`, `:76`.

### History (`/digests`)
- It fetches `/digests` once and shows loading, error, and empty states — `frontend/src/pages/History.tsx:15-45`.
  - The empty state has "Generate a digest" linking to `/` — `frontend/src/pages/History.tsx:41-45`.
- Each row links to `/digests/{id}` and shows the edition, date, topics (with `lang`), and counts — `frontend/src/pages/History.tsx:46-65`.
- The rail shows Archive (count and total items, hidden when empty) and "Kept as saved" — `frontend/src/pages/History.tsx:66-74`.

### Layout CSS
- **Page grid.**
  - `.page` is a 12-column grid. By default its children span columns 1–8, and `.page-head` spans all 12 — `frontend/src/styles/layout.css:13-15`.
  - The rail takes columns 9–12 with `grid-row: 2 / span 20` and a left rule — `frontend/src/styles/layout.css:33`.
- **Generate.** `.hero` and `.hero-actions` — `frontend/src/styles/components.css:70-71`.
  - `.page-generate .card` reduces cards to a top rule — `frontend/src/styles/components.css:95`.
  - Run and result cards have no own column rules, so they take columns 1–8.
- **Digest.**
  - `.page-digest .page-head` is a subgrid — `frontend/src/styles/layout.css:16-17`.
  - `.digest-layout` and `.digest-body` are `display: contents`, so the index, topics, and Creator updates are direct grid items — `frontend/src/styles/layout.css:18`.
  - `.toc`, `.topic`, and `.creator` span all 12 columns. `.topic` and `.creator` force this with `!important` — `frontend/src/styles/layout.css:19-20`.
  - A topic's title and overview take columns 1–3. Its items take columns 4–12 as their own 9-column grid — `frontend/src/styles/layout.css:21-22`.
  - Long items span 6 of those 9 columns and short items 3 — `frontend/src/styles/layout.css:24-25`.
  - Two consecutive long items stack — `frontend/src/styles/layout.css:28`.
  - Creator update groups span 3 columns each — `frontend/src/styles/layout.css:31-32`.
- **Issue #25.** `.items > .item:only-child { grid-column: 1 / span 6; }` places a single item in columns 1–6 of the 9, which leaves page columns 10–12 empty — `frontend/src/styles/layout.css:26`. #25 is open.
- **Breakpoints.** There are only container queries; `.app` is the container — `frontend/src/styles/base.css:4`.
  - At 900 px or less, `.page` becomes one column and everything spans it, including `.topic`, `.creator`, and `.toc`; the rail moves below the content — `frontend/src/styles/layout.css:51-68`.
  - At 640 px or less there are further adjustments — `frontend/src/styles/layout.css:69-80`.

### Shared components and accessibility
- **`PageHead`** renders `header.page-head` with an optional eyebrow, an `h1.page-title`, an optional lede, and children — `frontend/src/components/ui.tsx:4-10`.
- **`Rail`** is `<aside class="rail" aria-label="About this page">` — `frontend/src/components/ui.tsx:25-27`.
- **`Alert`** gets `role="alert"` only for `tone="error"` with `announce` true, which is the default — `frontend/src/components/ui.tsx:68-74`.
- **`StatusRegion`** is `<p class="sr-only" role="status" id="run-status">` — `frontend/src/components/ui.tsx:106-108`.
- **`Stepper`** is an `ol` with `aria-label="Run progress"` and `aria-current="step"` — `frontend/src/components/ui.tsx:87-98`.
- **`Progress`** is a native `progress` labelled by visible text — `frontend/src/components/ui.tsx:100-104`.
- **`useJump`** scrolls to the target, with no animation under reduced motion, then focuses it — `frontend/src/components/useJump.ts:3-11`. The skip link and the digest index use it — `frontend/src/components/AppShell.tsx:16`, `:22`.
- **Service worker.** It caches only `/offline.html` and handles only navigations. API responses and digests are not cached — `frontend/public/sw.js:1-43`. It is registered only in production builds — `frontend/src/main.tsx:8-9`.

### Backend: digests and runs
- **`GET /api/digests`.** All digests ordered by `created_at desc, id desc`, with no limit or query parameters — `backend/src/catchup/api/digests.py:14-18`.
  - Entry fields: `id`, `created_at`, `item_count`, `source_count`, `language`, `topics` (titles of non-Creator-updates topics), `creator_updates_only` — `backend/src/catchup/api/digests.py:33-38`.
  - The list costs two queries: digests, then all topics — `backend/src/catchup/api/digests.py:22-31`. A test asserts this constant query count.
- **`GET /api/digests/{id}`.** It returns `id`, `created_at`, `model_id`, `item_count`, `source_count`, `language`, `topics[{title, overview, items}]`, `creator_updates`, `transcript_wait_days`, `prompt_tokens`, `completion_tokens`. The token counts come from the linked run — `backend/src/catchup/api/digests.py:41-89`.
  - A missing id gives `404` with `{"error": {"code": "not_found", ...}}` — `backend/src/catchup/api/digests.py:45`; `backend/src/catchup/errors.py:17-21`.
- **No latest-digest or last-run endpoint exists.**
- **Runs.**
  - `POST /api/digest-runs` returns 202 with the run detail. It returns 409 `run_active` (with `active_run_id`) or 409 `model_not_configured` — `backend/src/catchup/api/runs.py:14-18`; `backend/src/catchup/digest/runner.py:124-130`.
  - `GET /api/digest-runs/active` returns the lowest-id active run, or JSON `null` with status 200 — `backend/src/catchup/api/runs.py:21-24`; `backend/src/catchup/digest/runner.py:110-111`.
  - `GET /api/digest-runs/{id}` returns the run, or 404 — `backend/src/catchup/api/runs.py:27-32`.
- **Run fields.** `id`, `status`, `items_total`, `items_done`, `error_kind`, `error_message`, `waiting_count`, `deferred_count`, `prompt_tokens`, `completion_tokens`, `digest_id`, `digest_item_count`, `digest_update_count`, `started_at`, `finished_at`, `sources_total`, `source_checks` — `backend/src/catchup/digest/runner.py:382-398`.
- **Which runs save a digest.** Only `succeeded` saves one, and a digest with only Creator updates also counts as `succeeded`. The digest, its snapshot, delivery, and `run.digest_id` are written in one transaction — `backend/src/catchup/digest/runner.py:303-355`.
  - `no_new_content` saves nothing — `backend/src/catchup/digest/runner.py:233`, `:296`.
  - Terminal statuses are `succeeded`, `no_new_content`, `failed`.
- **Data model.**
  - `Digest.run_id` is a unique, non-null foreign key to `digest_runs.id` — `backend/src/catchup/models.py:132`.
  - `DigestRun.digest_id` is a plain integer — `backend/src/catchup/models.py:123`.
  - `Digest.created_at` is set at save time — `backend/src/catchup/models.py:133`.
  - No code deletes digests.

### Tests
- **Mocking.** Each frontend test file stubs `fetch` with its own `respond()` helper. Generate tests route paths with `mockPage()` — `frontend/src/pages/Generate.test.tsx:19-28`.
  - Axe runs through `expectAccessible` (color contrast off) — `frontend/src/test/accessibility.ts`.
- **`Generate.test.tsx`.**
  - States:
    - first run (`:33`), idle (`:48`), no sources (`:57`)
    - running with empty sources (`:74`), progress (`:82`)
    - success with "View digest" as the only primary action (`:100`)
    - no new content (`:115`), failures (`:129`), interrupted (`:145`)
  - Polling and the persistent status region (`:153`); a failure announced only through status (`:172`); saved-count text (`:191`).
  - Last-digest links (`:68`, `:276`); a full run that refreshes the last digest (`:286`).
  - Model-not-configured POST (`:313`); action-specific alerts (`:331`); run-active recovery (`:361`).
  - Several tests run axe.
- **`DigestView.test.tsx`.** Document titles (`'Digest · CatchUp'`, `'No. 3 · 5 Oct 2026 · CatchUp'`); the 140/141-character width boundary; axe scans of several digests.
- **`History.test.tsx`.** Axe on the list and the empty state.
- **`App.test.tsx`.**
  - Titles of Generate, Sources, History, and Settings (`:11`).
  - Nav `aria-current`: History is current on `/digests/1` (`:38`).
  - Skip link (`:48`); shell axe on `/sources` (`:58`).
- **Backend tests.**
  - `backend/tests/test_digest_history.py`: newest-first ordering (`:57`), list fields (`:74`), constant query count (`:95`), detail and source deletion (`:187`).
  - `backend/tests/test_digest_runner.py:408`: `/active` null, 409, run 404.
  - `backend/tests/test_core_flow.py:30` and `backend/tests/test_creator_updates.py:132`, `:144`: the run → digest link and counts.

## Code References
- `frontend/src/pages/Generate.tsx:56-242` — Generate page: loading, polling, states, hero, cards, status region, rail
- `frontend/src/pages/DigestView.tsx:38-102` — `DigestBody`, the reading layout (not exported)
- `frontend/src/pages/DigestView.tsx:104-125` — `DigestView`: route-id fetch, title, error and loading
- `frontend/src/pages/History.tsx:15-76` — History list and rail
- `frontend/src/App.tsx:13-19` — routes
- `frontend/src/components/AppShell.tsx:7-36` — nav, `data-screen`, `aria-current`, skip link
- `frontend/src/components/ui.tsx:4-108` — PageHead, SectionRow, Rail, Alert, Stepper, Progress, StatusRegion
- `frontend/src/styles/layout.css:13-80` — page grid, rail, digest grid, item widths, breakpoints
- `frontend/src/styles/components.css:70-73,95,151,169` — hero, cards, rail boxes, hero-last visibility
- `frontend/public/sw.js:1-43`, `frontend/public/manifest.webmanifest:4-5` — offline page only; start URL `/`
- `backend/src/catchup/api/digests.py:14-89` — digest list and detail
- `backend/src/catchup/api/runs.py:14-32`, `backend/src/catchup/digest/runner.py:110-130,303-398` — runs, the active run, saving, run detail
- `backend/src/catchup/models.py:110-167` — run, digest, topic, and item models

## Current Specs
- `user-interface`
  - **One grid for masthead, navigation, and content.** A 12-column grid on wide windows and one column below 900 px; no horizontal scroll at 320 px — `openspec/specs/user-interface/spec.md:8-17`.
  - **Digest reading layout.** It defines:
    - a compact masthead
    - a headline with the edition number, date, and time
    - counts, the model, and tokens
    - an index when there is more than one section
    - section rows with each item's fields
    - wider columns for long items, not depending on position
    - a note for digests with only Creator updates
    
    `openspec/specs/user-interface/spec.md:30-50`.
  - **One primary action per state.** At most one primary action per state: set up the model on first run, add sources when there are none, view the digest for a finished digest, check settings on a configuration error. No primary action when nothing needs doing, such as no new content. Scenario "Digest ready": "View digest" is the only primary action — `openspec/specs/user-interface/spec.md:59-79`.
  - **Side information reflects the state.** Generate, Sources, and History show side information on wide windows. On first run it shows getting-started steps; otherwise the last digest with its edition number and time, and sources by kind. On narrow windows it follows the main content — `openspec/specs/user-interface/spec.md:81-91`.
  - **Keyboard and screen-reader support.** It requires:
    - the skip link and the digest index move focus
    - generated text carries its language
    - run progress and results are announced through one persistent status region
    - the progress bar has a name
    - each screen has its own document title, and a digest's title includes its edition number
    
    Scenarios cover the run finishing, the run failing (announced once), and the page title — `openspec/specs/user-interface/spec.md:110-137`.
- `digest-history`
  - **List saved digests.** Newest to oldest, with the edition, time, counts, and topic titles; Creator-updates-only digests listed as such; the list comes from a single request — `openspec/specs/digest-history/spec.md:8-17`.
  - **Reopen a saved digest.** The saved content is shown as it was saved, without regenerating it; it keeps the language and source kind recorded at save time — `openspec/specs/digest-history/spec.md:19-42`.
  - **Persist across restarts** — `openspec/specs/digest-history/spec.md:44-49`.
- `digest-generation`
  - **Start a digest run on demand.** At most one active run; a request during a run is refused and points to the active run — `openspec/specs/digest-generation/spec.md:8-17`.
  - **Show run progress and per-source outcomes** — `openspec/specs/digest-generation/spec.md:19-24`.
  - **No digest when nothing is new.** No digest is saved; the user sees "no new content", each source's outcome, and the counts of held items — `openspec/specs/digest-generation/spec.md:45-54`.
  - **Require model setup before generating** — `openspec/specs/digest-generation/spec.md:89-94`.
  - **Report model token usage.** The run view and the saved digest show the totals — `openspec/specs/digest-generation/spec.md:185-198`.
- `local-deployment`: the PWA's start URL is `/`, set in the manifest above; this spec was not read further for this topic.

## Related History
- The UI redesign (archived as `openspec/changes/archive/2026-10-14-redesign-ui-ux/`, PR #26) defined Generate's state table, the rail's contents, the status region texts, and the document title formats — `openspec/changes/archive/2026-10-14-redesign-ui-ux/design.md:139-161`, `:189`.
- Recent commits to the two pages: `275b8d2` (split ready count), `99973d9`, `757f583`, `9688975` (saved counts on detail), `b46d7c1` (no-sources state), `37aa736` (document titles), `bca742a` (failed runs announced only through status), `95869b2` (saved digest count in run results).
- Issue #27 was raised by the user on 2026-10-14 after the redesign's manual test. Its open questions:
  - Should `/` become the latest digest plus a compact generate bar, or keep Generate with the digest below?
  - After a run, should the new digest replace the one shown, in place?
  - How should navigation and document titles change?
  - What happens to the rail?
- Issue #25 (open) concerns the single-item topic layout rule at `frontend/src/styles/layout.css:26`.
