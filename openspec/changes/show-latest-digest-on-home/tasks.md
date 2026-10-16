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

- [x] 4.1 In `frontend/src/components/AppShell.tsx`, label the `/` item "Latest", keeping the `generate` icon. Use the screen key `latest` (`data-screen="latest"`), and mark that item `aria-current="page"` on `/`. History stays current on `/digests/:id`.

  Verify with failing-first tests in `frontend/src/App.test.tsx`:
  - The nav reads Latest, Sources, History, Settings.
  - `aria-current` is set on `/` and on `/digests/1`.
  - `data-screen` is `latest` on `/` and `digest` on `/digests/1`, so only the digest page gets the compact masthead.
  - The titles test expects "Latest · CatchUp" for `/` (with `/digests/latest` mocked as `null`).
  - The shell axe test still passes.
- [x] 4.2 Update `README.md` wherever it describes the Generate screen or a "Generate" navigation item, so that it describes the main screen ("Latest") with the latest digest and its Generate button. The usage sentence near the top (`README.md:5`) is one such place.

  Verify: `grep -n -i "generate" README.md` shows only accurate uses (the Generate action, or the Docker key-generation step).

## 5. Integration checks and report

- [x] 5.1 Run the full checks:
  - `uv run pytest` in `backend/`, noting the test count and coverage
  - `npm test -- --run` in `frontend/`, noting the test count and axe scans
  - `npm run build`
  - `python3 frontend/scripts/check-style-coverage.py`
  - `openspec validate show-latest-digest-on-home --strict`
  - a local `docker build`, if available

  Write the commands and their real results to `docs/process/test-report-show-latest-digest-on-home.md`. List the manual checks that were not performed: the live checks at 1440, 900, and 420 px, and a real run with the digest swapped in place.

  Verify: every command passes, and the report file exists with the actual numbers.

## 6. Review fixes, round 1

Notes for this round:
- These tasks come from the review of groups 1–5. Each finding was confirmed against the code, and the user decided how to resolve it on 2026-10-16. `design.md` (D3, D5, D7) and the spec scenario "Same digest in both places" were amended to match. Read those passages again first.
- **Use `diagnosing-bugs`** for 6.1–6.4: reproduce each bug with a failing test first, rank hypotheses, fix, and keep the test as the regression test. Put the confirmed cause in the commit message.
- **Use `tdd`** for 6.5, 6.6, and 6.8. Task 6.7 is the refactor step of `tdd`: it changes no behavior, so it has no failing test of its own. The tests from groups 3 and 6.1–6.6 are its safety net and must stay green.
- Do not edit `proposal.md`, `design.md`, or the spec deltas.

- [x] 6.1 Stale errors in the run bar (design D3, D5). Two bugs:
  - The startup alert "Could not load the latest digest" reappears in the run bar as a new `role="alert"` once a run's digest is shown (`Home.tsx:174`).
  - `generate()` does not clear "Could not load the new digest" (`newDigestError`).

  Verify with failing-first tests in `frontend/src/pages/Home.test.tsx`:
  - `/digests/latest` fails at startup, then a run succeeds and its digest is fetched. Afterwards no alert says "Could not load the latest digest", and no `role="alert"` is present.
  - A failed new-digest fetch shows "Could not load the new digest". Clicking Generate digest removes that alert.
  - A startup failure of another request (such as `/sources`) while a digest is shown still shows "Could not load some page details" in the run bar.
- [x] 6.2 No "View digest" after the first digest is saved (spec "Digest ready"; design D3). In the no-digest layout, the success card shows a primary "View digest" link today (`Home.tsx:264`). When the new-digest fetch fails, the link appears twice: once in the card and once in the alert.
  - While the new digest is being fetched, the card shows "Loading the new digest…".
  - The card has no primary action and no "View digest" link.
  - If the fetch fails, the alert's link to `/digests/{digest_id}` is the only link to the new digest.

  Verify with failing-first tests, using a deferred promise for `/api/digests/8`:
  - While the fetch is pending: "Loading the new digest…" is shown, there is no `.btn-primary`, and there is no "View digest" link.
  - After the fetch fails: exactly one link to `/digests/8`.
  - After the fetch succeeds: the digest article is shown.
  - `expectAccessible` passes in each case.
- [x] 6.3 Load-error title and message mismatch (design D3). When `/digests/latest` and another request both fail, the title says "Could not load the latest digest", but the message comes from whichever request failed first (`Home.tsx:81-86`).

  Verify with a failing-first test: `/settings/model` fails with message A and `/digests/latest` fails with message B. The alert shows the latest-digest title with message B.
- [x] 6.4 A fetched digest is discarded if another run starts during the fetch (design D5). The fetch effect's cleanup drops the result when `run` changes (`Home.tsx:108-120`). If the next run then finds no new content, the page keeps showing the older digest.

  Verify with failing-first tests (fake timers, deferred fetch):
  - Run 1 succeeds with digest 8, and run 2 starts while `/api/digests/8` is pending. Once the fetch resolves, digest 8 is shown.
  - A fetch for a lower id that resolves after a higher-id digest is shown does not replace it.
- [x] 6.5 Make the success-path tests exercise the success path. The tests at `Home.test.tsx:309`, `:362`, and `:400` do not mock `/api/digests/8`, so they pass in the fetch-error state, and `:309` asserts the old "View digest".
  - Mock the digest in each of these tests.
  - Replace `:309`'s "View digest" assertion with the 6.2 behavior.
  - `:362` and `:400` also assert that the digest article is shown and that the status region is the same node.

  Verify: these tests fail if the `/api/digests/{id}` mock is removed. Name each changed test in the commit message.
- [x] 6.6 Comparison test for "Same digest in both places" (amended spec scenario). Render Home with digest No. 7 as the latest digest, and render `DigestView` for `/digests/7` with the same digest.

  Verify: the two `section.page-digest` elements match once the run bar, the "← All digests" link, and the `page-home` class are removed. They must have identical markup, or at least identical headings, index, topic rows, items, and Creator updates.
- [x] 6.7 Shared run-state component (design D3 "Shared run-state content"). Today the running, succeeded, no-new-content, and failed content is written twice in `Home.tsx`: once in the run bar (`:180-211`) and once in the no-digest cards (`:247-288`).
  - Extract one component that renders this content for both. Its options cover the differences: headings in the cards, paragraphs in the bar.
  - Do this after 6.1–6.6, so that every behavior is covered by tests first. Do not write a red-first test for it, and do not test the component's internals.

  Verify:
  - Every `Home.test.tsx` test passes, with no change other than those made in 6.1–6.6.
  - The run bar still contains no heading elements.
  - `npm test -- --run` passes.
- [x] 6.8 Styles and the backend ordering test (design D7, D1):
  - **Double rule.** Remove the second line under the run bar: the bar's last `.check-row` has no bottom border. Add a `tokens.test.ts` assertion for it.
  - **Redundant rule.** Remove the narrow-block `.page-home > .run-bar` rule (`layout.css:61`). The narrow block's `.page > *` rule already spans it. Replace the `tokens.test.ts:138` assertion with one that checks the narrow `.page > *` rule spans `1 / -1`.
  - **Dead rules.** Remove the `.hero-last` rules (`components.css:76`, `:172`).
  - **Backend.** In `backend/tests/test_digest_history.py`, add a test where the newest digest by `created_at` has a lower id than an older one. `/api/digests/latest` returns the newest by time, matching the list's first entry.

  Verify:
  - `python3 frontend/scripts/check-style-coverage.py` passes.
  - `npm run build` passes.
  - `uv run pytest` passes.
- [x] 6.9 Re-run the 5.1 checks and append a "Review fixes, round 1" section to `docs/process/test-report-show-latest-digest-on-home.md`, with the commands and their real results.
  - In `docs/process/ai-usage-log.md`, move your entry "Latest digest on Home" so that it follows the 2026-10-16 plan entry, which keeps the log in chronological order.
  - Change that entry's date to "2026-10-15 to 2026-10-16", and add a short fix-round paragraph to it.

  Verify: every command passes, and the report has the actual numbers.

## 7. Review fixes, round 2

Notes for this round:
- These tasks come from the review of group 6 (`/code-review` and the spec subagent). Each finding was confirmed by a probe test, a mutation, or the code. The user decided on 2026-10-16 how to resolve them. `design.md` D3 (failed load, shared run-state content), D5, and D7 were amended; read those passages first.
- **Use `diagnosing-bugs`** for 7.1 and 7.2: reproduce each bug with a failing test, then fix, and keep the test.
- **Use `tdd`** for 7.3–7.5 and 7.7. Task 7.6 is a refactor step: like 6.7, it has no red test, and the existing tests must stay green.
- Do not edit `proposal.md`, `design.md`, or the spec deltas.

- [x] 7.1 Restore first-run gating of finished runs (design D3, shared run-state content). Before 6.7, the succeeded, no-new-content, and failed content was gated on `state`, which is `'first-run'` when no model is set. `RunStateContent` now keys on `run.status` alone (`Home.tsx:253`, `:289`).
  - Reproduction: a run fails, the user clicks "Try again", and the POST returns `model_not_configured`. "Digest generation failed" now stays next to "Set up your model first".

  Verify with failing-first tests, in both layouts:
  - No-digest layout: a failed run, then that POST. No "Digest generation failed" text or result card remains, and "Set up your model" is the only primary action.
  - Digest layout: a succeeded run, then that POST. The run bar shows no result line.
  - A running run's progress still shows in first run, as before 6.7.
- [ ] 7.2 Hide a new-digest error for an older digest (design D5). The catch handler sets "Could not load the new digest" for digest 8 even when a newer digest is, or is about to be, shown. Two ways this happens:
  - **Overlapping runs.** Fetch 8 is pending, run 2 starts, fetch 8 fails, and run 2 then saves digest 9. The alert linking to `/digests/8` stays above No. 9.
  - **Same tick.** Fetch 9 resolves and fetch 8 rejects before the next render, so `shownDigest.current` is stale.

  Fix at render time:
  - Show the alert only while no digest is shown, or while its id is higher than the shown digest's.
  - Remove the `shownDigest` ref and its write during render (`Home.tsx:127`). The functional `setDigest` updater keeps the success path ordered.

  Verify with failing-first tests for both cases: after No. 9 is shown, no `role="alert"` and no link to `/digests/8` remain.
- [ ] 7.3 Make the 6.4 "succeeded" case detect the regression it names. Today it still passes with the lower-id guards removed: digest 8 briefly overwrites 9, and the effect then fetches 9 again.

  Verify:
  - The test asserts that `/api/digests/9` is requested exactly once.
  - The test asserts that "Fetched edition" is never rendered after "Newer edition" has been shown.
  - The test fails when the success-path guard is changed to an unconditional `setDigest(result)`. Name this mutation in the commit message.
- [ ] 7.4 Cover the no-digest success card. In the pending-fetch test from 6.2, assert the card's content: the "Your digest is ready" heading, the saved items and source count, the token totals, the held notes, and the source checks.

  Verify: the test fails if `HeldNotes` or the token line is removed from the card branch of `RunStateContent`.
- [ ] 7.5 Record the two kinds of startup load error separately (design D3).
  - Replace the title-keyed `loadError` with an explicit kind, or with two state values: the latest-digest error and the page-details error.
  - Remove the three title-string comparisons (`Home.tsx:184`, `:246`, `:281`).

  Verify with failing-first tests:
  - `/digests/latest` and `/sources` both fail. The no-digest layout shows both alerts: "Could not load the latest digest" with its own message and "View History", and "Could not load some page details" with the sources message.
  - A run then saves a digest. The run bar shows "Could not load some page details" with the sources message, and no latest-digest alert.
  - The existing 6.1 and 6.3 tests still pass.
- [ ] 7.6 Refactor step, with no red test:
  - Rename the component-level `mounted` ref so that it no longer shares its name with the effects' local `mounted` flags (`Home.tsx:124`, `:136`, `:161`).
  - Remove any guard in the digest-fetch effect that 7.2 and 7.5 made redundant.

  Verify: `npm test -- --run` passes with no test changes in this task, and `Home.tsx` assigns no `ref.current` during render.
- [ ] 7.7 No second line during queued or early collecting (design D7). An empty `.check-list` in the run bar keeps its `border-top` (`components.css:88`), 1rem above the bar's `border-bottom`.
  - Either remove that border for an empty list in the bar, or do not render an empty list there.

  Verify with a failing-first test, either in `tokens.test.ts` or as a DOM check in `Home.test.tsx` for a queued run with no source checks.
- [ ] 7.8 Re-run the 5.1 checks and append a "Review fixes, round 2" section to `docs/process/test-report-show-latest-digest-on-home.md`, with real results.
  - Include the axe scan count, and add the missing count for round 1 if you can reconstruct it. Otherwise, say that it was not recorded.
  - Correct the round 1 statement that 6.7 preserved behavior: it did not in first run, and 7.1 fixed that.
  - In `docs/process/ai-usage-log.md`, add one short sentence on round 2 to your "Latest digest on Home" entry. Do not change the other entries.

  Verify: every command passes, and the report has the actual numbers.
