# Tasks

Implementer notes:
- **Read first.** Read `proposal.md`, `design.md` (D1–D7), and both files under `specs/` before starting. If something looks wrong or contradictory, stop and report instead of redesigning.
- **Work test-first with the `tdd` skill** (D-016). For each task, first write its verification items as failing tests and watch them fail, then implement until they pass. The seams to test are the ones named in each task; they count as agreed.
- **Test rules:**
  - Tests make no real network calls: mock `fetch` in vitest; use respx and the autouse DNS block in backend tests.
  - Tests use no real sleeps (fake timers for polling) and write nothing outside temp dirs.
- **Out of scope.** Do not change run behavior, the reading layout's content, the service worker, the manifest, or the single-item topic rule (`frontend/src/styles/layout.css:26`, issue #25).
- **Commits.** Commit after each task group. Do not push, tag, or open a PR.

## 1. Latest-digest endpoint

- [x] 1.1 In `backend/tests/test_digest_history.py`, add failing tests for `GET /api/digests/latest`:
  - JSON `null` with status 200 when no digest is saved.
  - With three saved digests, the response equals `GET /api/digests/{id}` for the newest one: topics, items, Creator updates, language, `transcript_wait_days`, and tokens.
  - A Creator-updates-only newest digest is returned in full.
  - When two digests share `created_at`, the higher id is returned.
  - `GET /api/digests/{id}` still returns its digest, and `/api/digests/latest` is never parsed as an id (no 422).

  Verify: the new tests fail before 1.2.
- [x] 1.2 In `backend/src/catchup/api/digests.py`, add the `latest` route, declared before `/{digest_id}`.
  - It uses the list's order (`created_at desc, id desc`).
  - Move `get_digest`'s serialization into one helper shared by both routes.

  Verify: the 1.1 tests pass, `uv run pytest` passes, and the coverage reported for `api/digests.py` does not drop.

## 2. Shared reading component

- [x] 2.1 Create `frontend/src/components/DigestArticle.test.tsx` with failing tests for an exported `DigestArticle`:
  - `before` renders as the section's first child, before the `h1`.
  - `headEnd` renders inside the page head after the meta line.
  - `className` is appended to `page page-digest`.
  - The rendered digest passes `expectAccessible`.
- [x] 2.2 Move `DigestBody` and the digest types from `frontend/src/pages/DigestView.tsx` into `frontend/src/components/DigestArticle.tsx` as `DigestArticle`, with the optional `className`, `before`, and `headEnd` props. Its markup stays unchanged. `DigestView` renders it with "← All digests" as `headEnd` and keeps its own loading, error, and title logic.

  Verify: the 2.1 tests pass, and every existing test in `frontend/src/pages/DigestView.test.tsx` passes with no change other than imports.

## 3. Main screen

- [x] 3.1 Move the page to `Home` and the latest-digest request.
  - Run `git mv frontend/src/pages/Generate.tsx frontend/src/pages/Home.tsx` and `git mv frontend/src/pages/Generate.test.tsx frontend/src/pages/Home.test.tsx`.
  - Export `Home`, route `/` to it in `frontend/src/App.tsx`, and make it request `/digests/latest` instead of `/digests`.
  - With `/digests/latest` mocked as `null`, every behavior covered by the current tests must still pass:
    - the first-run, idle, no-sources, running, progress, success, no-new-content, failed, and interrupted states
    - polling, the persistent status region, and failures announced once
    - saved counts, load errors, `model_not_configured`, and the run-active recovery
  - Remove the "Last digest" hero line and rail box.
  - Add failing-first tests:
    - `/` never requests `/api/digests` (the list).
    - The page shows "Loading…" until its four requests settle.

  Verify: `npm test -- --run` passes; `Home.test.tsx` has at least 21 `it`/`it.each` tests (the count in `Generate.test.tsx` before this task); the commit message names every test that was replaced and why.
- [x] 3.2 Add the layout with a shown digest. When `/digests/latest` returns a digest, render `DigestArticle` with `className="page-home"`, the run bar (design D4) as `before`, and no `Rail`.

  Verify with failing-first tests in `frontend/src/pages/Home.test.tsx`:
  - The digest's headline, index, and topics render.
  - The bar shows "Generate digest" as the only primary action and "{N} sources · Manage sources".
  - With a digest shown, first run gives "Set up your model" as the only primary action, and no sources gives "Add sources" as the only primary action, each with Generate disabled and its visible reason.
  - The bar contains no heading elements, and the page's first heading is the digest's `h1`.
  - No `aside.rail` is rendered.
  - The document title is "Latest · No. {id} · CatchUp", or "Latest · CatchUp" with no digest.
  - `expectAccessible` passes in each case.
- [x] 3.3 Add the run states in the bar while a digest is shown (design D4).

  Verify with failing-first tests:
  - **Running:** the stepper, the progress bar with its accessible name, and the source checks show, and the previous digest is still rendered.
  - **Succeeded:** the result line uses `savedItems`, sources, and tokens; held notes and source checks show; there is no "View digest" and no primary action; Generate digest is secondary.
  - **No new content:** no primary action, and the digest is kept.
  - **Failed:** the alert has no `role="alert"`. "Try again" is primary, or for configuration errors "Check settings" is primary and "Try again" secondary. The digest is kept.
  - The status region texts are unchanged.
  - `expectAccessible` passes in each state.
- [x] 3.4 Replace the digest after a successful run (design D5). With fake timers, add failing-first tests:
  - Polling to `succeeded` fetches `/digests/{digest_id}` and shows that digest in place of the previous one.
  - `/api/digests` (the list) is not requested.
  - An element focused before the run ends, such as the bar's "Manage sources" link, is still `document.activeElement` afterwards, and `HTMLElement.prototype.focus` is not called by the page.
  - The status region is the same DOM node before and after, and it says "Digest ready: …" once. This also holds for the switch from the no-digest layout to the first saved digest.
  - A failed fetch of the new digest shows "Could not load the new digest" with a link to `/digests/{digest_id}`, and the previous digest stays shown.
  - A failed `/digests/latest` at startup shows "Could not load the latest digest" with a "View History" link, and Generate still starts a run.

  Verify: these tests pass, and `npm test -- --run` passes.
- [x] 3.5 Style the run bar in `frontend/src/styles/components.css` and `frontend/src/styles/layout.css` (design D7):
  - `.page-home > .run-bar` spans the full grid width, also at 900 px and below.
  - A rule separates the bar from the digest head.
  - In the ready state the controls sit on one row.
  - Existing tokens and styles are reused.

  Verify: `python3 frontend/scripts/check-style-coverage.py` reports no new class without a rule, and `npm run build` passes.

## 4. Navigation, masthead, and titles

- [ ] 4.1 In `frontend/src/components/AppShell.tsx`, label the `/` item "Latest", keeping the `generate` icon. Use the screen key `latest` (`data-screen="latest"`), and mark that item `aria-current="page"` on `/`. History stays current on `/digests/:id`.

  Verify with failing-first tests in `frontend/src/App.test.tsx`:
  - The nav reads Latest, Sources, History, Settings.
  - `aria-current` is set on `/` and on `/digests/1`.
  - `data-screen` is `latest` on `/` and `digest` on `/digests/1`, so only the digest page gets the compact masthead.
  - The titles test expects "Latest · CatchUp" for `/` (with `/digests/latest` mocked as `null`).
  - The shell axe test still passes.
- [ ] 4.2 Update `README.md` wherever it describes the Generate screen or a "Generate" navigation item, so that it describes the main screen ("Latest") with the latest digest and its Generate button. The usage sentence near the top (`README.md:5`) is one such place.

  Verify: `grep -n -i "generate" README.md` shows only accurate uses (the Generate action, or the Docker key-generation step).

## 5. Integration checks and report

- [ ] 5.1 Run the full checks:
  - `uv run pytest` in `backend/`, noting the test count and coverage
  - `npm test -- --run` in `frontend/`, noting the test count and axe scans
  - `npm run build`
  - `python3 frontend/scripts/check-style-coverage.py`
  - `openspec validate show-latest-digest-on-home --strict`
  - a local `docker build`, if available

  Write the commands and their real results to `docs/process/test-report-show-latest-digest-on-home.md`. List the manual checks that were not performed: the live checks at 1440, 900, and 420 px, and a real run with the digest swapped in place.

  Verify: every command passes, and the report file exists with the actual numbers.
