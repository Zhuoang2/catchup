# Design

Chosen by the user on 2026-10-16: Proposal 1 of the two proposals, with the first navigation item named "Latest". The single-item topic layout (#25) stays a separate change. The research behind this design is in `research.md`.

## Context

See `proposal.md` for the motivation. The current state that shapes the approach (details and line references in `research.md`):

- **Generate never loads digest content.** It requests the full digest list only to link to the first entry (`frontend/src/pages/Generate.tsx:65-84`, `:142-144`, `:225-228`). After a run succeeds, it offers "View digest" (`:193`) and refreshes the list (`:102-111`).
- **The reading layout is the unexported `DigestBody`** (`frontend/src/pages/DigestView.tsx:38-102`). It renders a whole `.page.page-digest` section with its own `<h1>`.
  - Its rows span all 12 grid columns (`frontend/src/styles/layout.css:16-32`).
  - Generate splits the grid into content (columns 1–8) and a rail (9–12, `layout.css:14`, `:33`).
- **The backend has no latest-digest endpoint.** The list is newest first (`created_at desc, id desc`) with no limit (`backend/src/catchup/api/digests.py:14-18`). The detail is `GET /api/digests/{id}` (`:41-89`). `/api/digest-runs/active` returns `null` when no run is active (`backend/src/catchup/api/runs.py:21-24`).
- **One persistent status region announces runs** (`frontend/src/components/ui.tsx:106-108`, `Generate.tsx:218`).

## Goals / Non-Goals

**Goals:**
- `/` shows the newest saved digest in the same layout as `/digests/:id`, with the run controls in a bar above it.
- Every run state keeps its progress, outcomes, and announcements, and the shown digest stays visible through them.
- After a successful run, the new digest replaces the shown one without a click, a reload, or a focus move.

**Non-Goals:**
- The single-item topic layout (#25).
- The last run's outcome surviving a reload. There is no runs-list or last-run endpoint.
- Any change to run behavior, the reading layout's content, the service worker, or the PWA manifest.
- A Generate shortcut on other screens.

## Decisions

### D1. `GET /api/digests/latest`
- **Response.** The same JSON as `GET /api/digests/{id}` for the first digest in the list's order (`created_at desc, id desc`), or JSON `null` with status 200 when none is saved.
- **Serialization.** `get_digest`'s serialization moves into one helper used by both routes, so the two responses cannot drift.
- **Route order.** `latest` is declared before `/{digest_id}`, so `"latest"` is never parsed as an id.
- **Alternatives:**
  - The first list entry plus `GET /api/digests/{id}`. Rejected: two requests, and the list grows without limit (`digests.py:14-18`). The main screen needs only one digest.
  - 404 when none is saved. Rejected: an empty history is a normal state for a new install, and `/digest-runs/active` already uses `null` for "nothing".

### D2. One shared reading component
- `DigestBody` moves to `frontend/src/components/DigestArticle.tsx` as the exported `DigestArticle`, together with the `Digest` types.
- **Markup is unchanged.** It keeps the `<section className="page page-digest">` and its own `PageHead` (`h1`).
- **Optional props:**
  - `className`: appended to the section.
  - `before`: rendered as the section's first child, before the head.
  - `headEnd`: rendered at the end of the head. DigestView passes "← All digests" (`DigestView.tsx:50`).
- `DigestView` keeps its loading, error, and title logic (`DigestView.tsx:104-125`) and renders `DigestArticle`.
- **Alternative:** an embedded variant with shifted heading levels (Proposal 2). Rejected: every heading in the layout would need a level parameter, and the 8 + 4 grid would be mixed with the 12-column digest grid.

### D3. The main-screen page
- **Files.** `Generate.tsx` becomes `Home.tsx` (`git mv`, and the same for its test file) with default export `Home`. `App.tsx` routes `/` to it.
- **What it keeps.** Generate's state logic, polling, `generate()`, error handling, and status texts (`Generate.tsx:22-140`).
- **What it requests.** `/settings/model`, `/sources`, `/digests/latest`, and `/digest-runs/active`, still through one `Promise.allSettled`. It no longer requests `/digests`.
- **Layouts:**
  - **Loading** (until the four requests settle): a page head "Loading…", the same pattern as `DigestView.tsx:123`.
  - **A digest is shown:** `DigestArticle` with `className="page-home"` and the run bar (D4) as `before`. There is no `Rail`.
  - **No digest saved** (`/digests/latest` returned `null`): today's Generate layout, with its hero, its run and result cards, and its rail (Getting started on first run; otherwise Your sources and How it works). The "Last digest" hero line and rail box are removed, because this layout exists only when no digest is saved.
    - When a run saves the first digest, the result card offers no "View digest" and no primary action. It says "Loading the new digest…" until the digest replaces this layout (D5).
    - If that fetch fails, the D5 alert is the only link to the new digest.
  - **The latest digest failed to load:** the no-digest layout with an error `Alert`, "Could not load the latest digest", and a "View History" link. Generate keeps working.
    - The alert's message is the error of the `/digests/latest` request. When only other requests fail, the title is "Could not load some page details".
    - The alert belongs to the no-digest layout. Once a run's digest is shown, it is gone, and the run bar does not repeat it.
- **The status region** is rendered once, at a fixed position outside the layout branches. It is never remounted between layouts, so the announcement survives the switch from the no-digest layout to the first saved digest.
- **Shared run-state content.** One component renders the content of the running, succeeded, no-new-content, and failed states: the stepper, the progress bar, the result line, held notes, the failure text, and source checks. The run bar and the no-digest layout's cards both use it. Only the wrapper and the labels differ: the cards keep their headings, and the bar uses paragraphs (D4).

### D4. The run bar
`<section className="run-bar" aria-label="Digest run">`. It contains no heading elements, so the digest's `<h1>` stays the page's first heading. Labels are paragraphs, and `SourceChecks` gets a non-heading label for this use. Content by state:

| State | Primary | Secondary and content |
|---|---|---|
| Ready to generate | Generate digest | "{N} sources · Manage sources" |
| First run (no model) | Set up your model | Generate disabled, with its reason |
| No sources yet | Add sources | Generate disabled, with its reason |
| Running | "Generating…" (disabled) | Stepper, named progress bar, source checks (`Generate.tsx:176-186`) |
| Succeeded | — | Generate digest; "Your digest is ready · {saved items} · {sources} · {tokens}" (`savedItems`, `Generate.tsx:22-28`); held notes; source checks. No "View digest" |
| No new content | — | Generate digest; "No new content · Nothing new since your last digest · {tokens}"; held notes; source checks |
| Failed (configuration) | Check settings | Try again; the error `Alert` with `announce={false}`; the "what was kept" text; source checks |
| Failed (other) | Try again | The same alert, text, and source checks |

The digest below stays rendered in every state.

### D5. Replacing the digest after a run
- When the polled run reaches `succeeded` with a `digest_id`, the page fetches `/digests/{digest_id}` and shows it. It does not fetch `/digests/latest`, because the run identifies its own digest.
- No element is focused programmatically, and the page does not scroll.
- The status region text is today's "Digest ready: …" (`Generate.tsx:138`).
- If the fetch fails, an error `Alert`, "Could not load the new digest", links to `/digests/{digest_id}`, and the previous digest stays shown. Starting another run clears this alert.
- A fetched digest is shown even if another run has started in the meantime. It never replaces a digest with a higher id.
- The `/digests` refresh effect (`Generate.tsx:102-111`) is removed.

### D6. Navigation, masthead, and titles
- **Navigation.** The item for `/` reads "Latest" and keeps the `generate` icon. `AppShell`'s screen key for `/` becomes `latest` (`data-screen="latest"`), and that item is `aria-current="page"` on `/`. History stays current on `/digests/:id` (`AppShell.tsx:17-29`).
- **Masthead.** No CSS change is needed: the compact masthead applies only to `data-screen="digest"` (`layout.css:47-50`), so `/` keeps the full masthead with the date.
- **Titles.** "Latest · No. {id} · CatchUp" when a digest is shown, otherwise "Latest · CatchUp". `/digests/:id` keeps "No. {id} · {date} · CatchUp".

### D7. Styles
- `.page-home > .run-bar` spans `1 / -1` in the digest grid. At 900 px and below, the existing `.page > *` rule in the single-column block already spans it, so there is no second rule.
- A rule under the bar separates it from the digest head. It is the only line there: the bar's last source-check row has no bottom border.
- The `.hero-last` rules are removed together with the "Last digest" line.
- In the ready state, the bar's controls sit on one row.
- The bar reuses the existing hero-action, stepper, progress, and check-list styles. It adds only the classes it needs, each with a rule (`frontend/scripts/check-style-coverage.py` reports any without one).

### D8. Alternative considered: keep Generate and embed the digest below it (Proposal 2)
Rejected:
- Reading would stay secondary, below the hero, the cards, and the rail's height.
- It mixes two grids on one page.
- It needs heading-level variants for the whole reading layout.
- It duplicates the rail's "Last digest".

## Risks / Trade-offs

- **[Lost tests]** `Generate.test.tsx` has 21 tests (`it` and `it.each`), and the redesign once lost tests during a move. → Task 3.1 requires `Home.test.tsx` to keep every behavior and to count at least as many tests. Any test that is replaced is named in the commit message.
- **[First digest]** The first saved digest switches the page from the no-digest layout to the article. The disabled "Generating…" button unmounts, so focus may fall back to the document. → No digest was shown, so none is being replaced. The status region does not remount (D3), so the announcement is kept. A test covers this transition.
- **[Stale digest]** The shown digest can go stale when another tab saves a digest. → Accepted. A reload shows the newest one, and the active-run check already covers runs started elsewhere (`Generate.tsx:71`).
- **[#25 more visible]** Single-item topics leave the right third of the row empty, and this becomes the first thing users see. → Tracked as #25 and planned right after this change.

## Migration Plan

- No data migration. The backend and frontend ship together in one image.
- Rollback is a revert. `/` and `/digests/:id` keep their URLs, and the manifest's `start_url` stays `/`.

## Testing

- **Backend** (`backend/tests/test_digest_history.py`):
  - `latest` returns `null` when no digest is saved.
  - It returns exactly the detail JSON of the newest digest, including a Creator-updates-only digest.
  - Ties on `created_at` resolve to the higher id.
  - `/api/digests/{id}` is unaffected.
- **Frontend:**
  - `DigestArticle` slot order.
  - The `DigestView` tests pass unchanged.
  - `Home.test.tsx`:
    - every state in both layouts
    - one primary action per state
    - the bar has no headings
    - the replacement after success: digest swapped, focus unchanged, one announcement, the persistent status node, failure paths
    - no request to the list
    - titles
    - axe in each state
  - `App.test.tsx`: the nav label, `aria-current`, `data-screen`, and titles.
- **Review step** (D-016): `/code-review`, the spec sub-agent, and live checks on the e2e container. The live checks are a real run, `queued` → `succeeded` with the digest swapped in place, and the layout at 1440, 900, and 420 px.
