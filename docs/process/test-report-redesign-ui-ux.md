# Redesign UI/UX implementation checks

2026-10-06, branch `redesign-ui-ux`, baseline `e05dada`. All commands below ran from their documented directories unless noted.

| Check | Result |
| --- | --- |
| `uv run pytest --cov=catchup --cov-report=term-missing -q` | 352 passed; 96% statement coverage (1,861 statements, 77 missed). Digest API: 100%; runner: 99%. |
| `npm test -- --run` | 56 passed in 10 files. 31 explicit `expectAccessible` calls cover the shell, components, page states and errors; axe found no violations. The jsdom helper excludes axe's canvas-dependent color-contrast rule, while token tests check WCAG contrast in both themes and the hue separation. |
| `npm run build` | Passed TypeScript and Vite build; public install/offline assets copied into `dist/` byte-for-byte. |
| `openspec validate redesign-ui-ux --strict` | Valid. |
| `docker build -t catchup-redesign-smoke .` and `scripts/docker-smoke.sh catchup-redesign-smoke` | Passed on Docker 29.8.0. Verified manifest/worker MIME, offline page bytes, health, persistence after restart, non-root process, and image exclusions. Uses a throwaway named volume and a loopback port. |
| Icon reproducibility | Vitest regenerated all PNGs and SVG into a temporary directory and compared bytes with committed files; checked PNG headers and dimensions. |
| Worker isolation | Fake-service-worker tests covered only-offline install caching, old-cache cleanup, rejected-navigation fallback, pass-through 500, and API/asset non-interception. |

One Docker smoke attempt initially failed: the new public text files had mode 600, so the non-root container returned response headers but could not stream their bodies. Changed the three files to mode 644, rebuilt, and reran successfully. No real model, public feed, or key was used in unit tests. No unit test waits for a real sleep or writes outside temporary test directories.

## Rendered spot check

In a fresh isolated Chrome session against the local smoke image, the first-run Generate page passed the browser's WCAG 2 A/AA axe audit (0 violations). At 420 × 900, the masthead was 84.8 px tall (limit: 120 px), and the document was 420 px wide with no horizontal overflow. Settings and Sources also passed browser axe in the narrow viewport (0 violations); Sources was checked in dark mode. After the throwaway container stopped, navigating to `/history` rendered the service worker's "CatchUp isn't running" fallback and Reload button; that page also passed browser axe. The browser session and container were closed afterward.

The full D8 visual parity matrix (every prototype state in both themes at 1440 and 420), first-digest-topic placement in a populated live digest, keyboard-only pass, Chrome/Edge/Safari installation UI, and macOS Safari rendering are **not verified by this implementation run**. Those are manual review checks assigned to the subsequent Claude review in design.md D8; no blanket parity or installation claim is made here. In particular, jsdom cannot measure paint-based contrast or layout; token arithmetic and the limited real-browser spot check do not replace that review.

## Scope audit

Compared to the approved `e05dada` baseline, only `tasks.md` changed under the OpenSpec change folder. No prototype, proposal, design, spec delta, CI job name, or backend route was edited. Runtime dependencies are unchanged; frontend dev dependencies add only `axe-core` and `vitest-axe` (with their lockfile transitive packages). Color literals under `frontend/src` occur only in `tokens.css`, tests, and the two approved switch literals. Manifest, offline page, index theme metas, and generated icons mirror token colors under the scoped D2 exception.

Interpretive choices made under the user's ambiguity guidance: History obtains topic previews from existing digest-detail responses because list responses have no titles; No new content has no primary action per the corrected D4 table; Settings' saved-key suffix appears as separate descriptive text, never in the password input or placeholder. The service worker falls back only after a rejected navigation, not on HTTP error responses.

## Style coverage (review task 10.6)

`python3 frontend/scripts/check-style-coverage.py` compares static class names in the C7 renderer and app TSX against the ordered prototype cascade and owned stylesheets. After porting the missing rules, it reports:

```text
Static UI classes with C7 rules but no app rules (9):
  .code
  .edition
  .logo
  .logo-lg
  .offline-brand
  .offline-card
  .page-history
  .page-offline
  .page-sources
```

The first six and `.page-offline` belong to prototype-only chrome or the separate self-contained offline page, not React's runtime CSS. `.page-history` and `.page-sources` share the app's `.page` grid; their page-specific content placement is handled by `.page > *`. At 320 px in a fresh isolated Chromium session, all four navigation labels were fully visible and `document.documentElement.scrollWidth === 320`.

## Review fixes

2026-10-06, branch `redesign-ui-ux`, review baseline `88b5b7d`. This section supersedes the earlier History per-detail-request note: History now uses one enriched list response, with two digest-list SELECTs regardless of list length.

| Check | Result |
| --- | --- |
| `uv run pytest --cov=catchup --cov-report=term-missing -q` | 354 passed; 96% statement coverage (1,868 statements, 77 missed). Digest API: 100%. |
| `npm test -- --run` | 79 passed in 12 files. 36 explicit `expectAccessible` call sites ran 41 axe scans when parameterized variants are counted, covering the new digest index, language, loading/error, Generate and field-error states. No axe violations; jsdom color contrast remains excluded as described above. |
| `npm run build` | Passed TypeScript and production Vite build, including copying `offline.html` and the install assets. |
| `openspec validate redesign-ui-ux --strict` | Valid. |
| `docker build -t catchup-redesign-review-smoke .` and `scripts/docker-smoke.sh catchup-redesign-review-smoke` | Passed on Docker 29.8.0, including health, manifest/worker/offline files, non-root process, image exclusions and saved preference after restart. Smoke used a throwaway volume and loopback port. |
| `python3 frontend/scripts/check-style-coverage.py` | Nine remaining prototype-only or generic-grid classes, listed and classified above; no uncovered runtime component class. |
| Browser spot checks | At 320 px, all four nav labels fit without horizontal overflow. The standalone offline page at 320 px had the C7 serif body/brand, centered card, hidden decorative logo and small-caps Reload button; document width was 320 px. |

Tests used mocked API/feed/model responses and fake timers, not live feeds or a real provider. No runtime dependencies, CI job names, protected OpenSpec plans/specs or prototype files changed in this review-fix round. Under the OpenSpec change folder, the implementer changed only task checkboxes; the reviewer then corrected the 10.7 text there and, in `components.css`, hid the index counts (`d47fbf8`). No full multi-theme visual parity, keyboard-only end-to-end pass, native PWA installation or Safari rendering was performed; the earlier manual-review limitations remain. The offline-page spot check loaded the standalone file, not a simulated service-worker navigation; the prior worker-isolation tests and Docker asset smoke still passed.

Interpretive choices at that point: a digest with no topics and no Creator updates displays “No topics”; the Creator-only flag requires an actual Creator-updates topic. When the model-settings read fails, Generate keeps active-run visibility rather than assuming first-run setup. The later second-review fixes supersede two claims here: “Your sources” is no longer an empty-state heading, and index counts are hidden as in C7 (the conflicting 10.7 text was corrected). The independent style audit still reports generic page and standalone-offline selectors rather than silently filtering them out.

## Second review fixes

This section supersedes the earlier Review fixes snapshot where behavior changed. Index counts are hidden as in C7; 10.7 text was corrected in the plan. The empty Sources state now has one “No sources yet” heading, which receives focus after deleting the last source, instead of retaining “Your sources”. The earlier nine-class style output is historical; the current full selector audit below reports eight explained exceptions and `Uncovered prototype selectors (0):`.

### Second-review selector audit (task 11.10)

The audit now checks the complete prototype-to-app class-selector difference, not just classes found in static markup. `python3 -m unittest test_check_style_coverage -v` passed three tests, including a dynamic-only selector check. `python3 frontend/scripts/check-style-coverage.py` printed:

```text
Static UI classes with C7 rules but no app rules (8):
  .code
  .logo
  .logo-lg
  .offline-brand
  .offline-card
  .page-history
  .page-offline
  .page-sources
Allow-listed prototype-only selectors (8):
  .code: Offline command block uses self-contained inline CSS
  .logo: Prototype wordmark; standalone offline logo was removed
  .logo-lg: Prototype-only large wordmark
  .offline-brand: Prototype offline card; standalone page owns its own CSS
  .offline-card: Prototype offline card; standalone page owns its own CSS
  .page-history: Generic .page grid handles the History wrapper
  .page-offline: Standalone offline page does not load app CSS
  .page-sources: Generic .page grid handles the Sources wrapper
Uncovered prototype selectors (0):
```

### Second-review mutation checks (task 11.11)

After adding source kinds to the Creator-updates fixture, temporarily restoring `<KindIcon kind={item.source_kind}/>` inside each item's metadata made `renders creator updates after topics with saved wait labels` fail: five item-level hidden kind labels appeared instead of zero. The original group-only markup was restored.

The masthead test now expects the literal local date `2026-10-06` for an instant whose UTC date is `2026-10-07`. Before pinning the test timezone, running it with `TZ=UTC` failed (`dateTime="2026-10-07"`). The `test` script pinned `America/Los_Angeles` at this point; the pin later moved to `vite.config.ts` and is checked in `src/test/setup.ts` (see "Reviewer fixes after the second review"). Temporarily restoring `today.toISOString().slice(0, 10)` after that change made the same test fail again with `dateTime="2026-10-07"`; local-date markup was restored. Under an outer `TZ=UTC`, the targeted App/Digest suites then passed 16/16, and the frontend build passed. No temporary production mutation remains.

### Failing checks before fixes

| Task | Red check and subsequent green verification |
| --- | --- |
| 11.1 | With fake-timer polling, a failed `/digests` startup alert disappeared after two successful polls. Separating startup and polling errors preserved it; focused rendered-page tests and build passed. |
| 11.2 | A deferred list refresh kept a successfully deleted source row visible. Removing it on DELETE success and focusing the next list/empty target fixed the rendered test; refresh failures now have their own error; focused tests and build passed. |
| 11.3 | A failed `/sources` load made Generate report zero sources and suggest adding sources. Distinguishing unread (`null`) from empty removed the invented count; focused tests and build passed. |
| 11.4 | Tag tests rejected valid `ja`, `fr`, `zh-hant`, `PT-br` and `de-CH`; the explicit name table plus canonicalization and approved primary-subtag list accepted them while rejecting `abcdefgh` and `xx`. Focused tests (18) and build passed. |
| 11.5 | Rendered Generate hero used the long date; compact hero date test failed then passed (17 focused tests and build). The rail retains its long date. |
| 11.6 | Empty Sources showed an extra “Your sources” heading and focused it on last deletion. One empty-state heading and empty-state focus passed (13 focused tests and build). |
| 11.7 | History lacked the `.edition` accent element; a rendered assertion failed then passed with the wrapper and CSS (2 focused tests, style script and build). |
| 11.8 | Install assertions found an unused offline logo element and stylesheet; removing both passed install and worker tests, build and byte-for-byte asset checks, plus Docker smoke. |
| 11.9 | Digest-list topic SELECT received `(3, 2, 1)` IDs; after removing the redundant `IN` predicate it used one unparameterized topic query. All 8 digest-history tests passed. |
| 11.10 | CLI test for the complete prototype selector difference failed while the audit only scanned static markup. Full selector comparison and eight justified exceptions passed 3 unit tests; the exact output is recorded above. |
| 11.11 | With real kinds in Creator groups/items, restoring item-level icons yielded five unexpected hidden labels. With a pinned `America/Los_Angeles` test zone, restoring UTC-derived masthead dates yielded `2026-10-07` instead of `2026-10-06`. Both mutations were removed; 16 focused tests and build passed. |
| 11.12 | A new report-verification unittest failed on the missing `## Second review fixes` section before this section was written; it now checks the corrections, task evidence and final commands below. |

### Final integration checks (9.1)

| Check | Result |
| --- | --- |
| `uv run pytest --cov=catchup --cov-report=term-missing -q` | 355 passed; 96% statement coverage (1,868 statements, 77 missed). Digest API: 100%. |
| `npm test -- --run` | 91 passed in 12 files; 37 `expectAccessible` call sites, 42 axe scans including parameterized states, no reported violations. jsdom excludes the paint-dependent color-contrast rule; token contrast tests cover both themes. |
| `npm run build` | TypeScript and Vite production build passed. |
| `python3 -m unittest discover -s scripts -p 'test_*.py' -v` | Selector and report checks: 4 passed after the report update. |
| `python3 scripts/check-style-coverage.py` | Eight explicitly explained prototype-only selectors; `Uncovered prototype selectors (0):` (full output above). |
| `openspec validate redesign-ui-ux --strict` | Valid. |
| `docker build -t catchup-redesign-group11-final .` and `scripts/docker-smoke.sh catchup-redesign-group11-final` | Passed: health, host check, manifest/worker/offline MIME, preference saved across restart on a throwaway volume, non-root process, and image exclusions. |

Scope audit: in this second-review round the implementer changed only task checkboxes under the OpenSpec change folder, and the reviewer corrected the 11.4 example (`4de850a`); protected plans/spec deltas/prototypes, CI jobs, runtime dependencies and lockfiles were untouched. Tests use mocked APIs and fake timers; no unit test contacts a live feed or provider or waits on a real sleep. The standalone style audit covers prototype class selectors even when absent from static markup. This run did not repeat the full two-theme visual parity matrix, keyboard-only end-to-end pass, native PWA installation or Safari rendering; the earlier manual-review limitations still apply.

## Reviewer fixes after the second review

2026-10-07, by Claude Code after the fixed review step (`/code-review` plus an independent spec review) on `1351e9f..3c76f9f`. Each fix was test-first: the new test was seen failing, or, for a guard that already existed, the guard was removed temporarily to show the test fails without it.

| Fix | Failing evidence |
| --- | --- |
| `GET /api/digests` skips topics of a digest saved between its two queries | New test `test_history_list_ignores_a_digest_saved_between_its_two_queries` failed with `KeyError` at `api/digests.py:29`, then passed. |
| `digestLang` names table is a `Map` | `constructor` and `__proto__` returned a function and an object; 2 new cases failed, then passed. |
| Free text that is neither a name nor a tag gets no `lang` | Removing the `RangeError` guard made 6 cases fail ("Brazilian Portuguese", "English (US)", "中文（简体）" and others). |
| Focus after deleting one of several sources lands on "Your sources" | New test; with focus forced to the empty-state heading it failed 3 of 3 runs. A first version was flaky (1 of 3 failures) because it asserted focus before the effect ran; it now waits for focus. |
| Test timezone pinned in `vite.config.ts` (`test.env.TZ`) instead of a POSIX-only `TZ=` prefix in `package.json` | From a `TZ=UTC` shell, re-introducing `toISOString()` in the masthead still failed the date test. |

Follow-up from the review of these fixes: the race test also checks the topics of listed digests; `src/test/setup.ts` throws unless the zone is `America/Los_Angeles`, so a pool that ignores `test.env` (for example `--pool=threads` from a UTC shell) fails loudly; `digestLang` lowercases with `toLowerCase()` (a test emulating Turkish case rules failed with `toLocaleLowerCase()`); the `toString`/`hasOwnProperty` cases, which could not fail, were dropped.

Checks after these fixes: `uv run pytest -q` 356 passed; `npm test -- --run` 98 passed, four consecutive full runs including one from a `TZ=UTC` shell; `npm run build` passed; `openspec validate redesign-ui-ux --strict` valid. `design.md` D5 gained an amendment note for language tags.

## Final review fixes

2026-10-07, task group 13, starting at `4b65d19`. Focused checks were run red before each fix, then green. The choices below follow the approved D4–D7 amendments.

| Task | Failing check before the fix |
| --- | --- |
| 13.1 | Run API test raised `KeyError: digest_item_count` for one summary plus two Creator updates and for a Creator-only digest. Fake-timer Generate tests announced 1 or 0 summarized items instead of 3 or 2 saved items. |
| 13.2 | Failed `/sources` load still rendered the “No sources yet” heading and examples. |
| 13.3 | Polling to a failed run left an error `role="alert"` alongside the status region. |
| 13.4 | Rendered routes left `document.title` blank on all four screens and digest loading/error/success. A first version of the success fixture used a different route id than the returned digest; the corrected fixture tests `/digests/3`. |
| 13.5 | Configured model with a successfully loaded empty source list had no primary “Add sources” link and an enabled Generate button. Failed source reads retain the neutral state. |
| 13.6 | Fake worker recorded no offline-page refresh and no `waitUntil` after a successful navigation. |
| 13.7 | Stylesheet assertion found `-webkit-line-clamp: 2` and `overflow: hidden` on `.source-feed`. |
| 13.8 | Digest-detail API test raised `KeyError: item_count`; rendered two distinct sources with the same title as “1 source”. |
| 13.9 | Hover stylesheet assertion found no `--muted` override for History counts. Both themes' `--muted`/`--fg` on `--hover` contrast pairs pass. |
| 13.10 | Interrupted zero-item run rendered “0 of 0”; navigation from a 404 to a valid digest kept the old error; stylesheet had no `.btn:disabled` rule. |
| 13.11 | Strengthened test assertions were green against the unmutated implementation; mutation probes below each turned the targeted test red and were restored. |
| 13.12 | The report-verification unittest failed because the final review section lacked task 13.12 and the full-check results; it passed after recording them below. |

For 13.11, temporary mutations were applied one at a time and restored in `finally` before the focused suite and build passed (69 tests in five files). The following mutations each made its targeted test fail: show “Your sources” in an empty Sources page; show populated rail data on first run; remove the digest edition; replace saved source count and saved item count with zero; remove summary `lang`; shift the wide-summary threshold from 140 to 141; make failed and warning chips the same tone (separate probes); zero the podcast rail breakdown; zero the “Checking sources” numerator; stop marking the base URL invalid on `connection_failed`; and remove the skip link's focus handler. No temporary production mutation remains.

### Final integration checks (task 13.12)

| Check | Result |
| --- | --- |
| `uv run pytest --cov=catchup --cov-report=term-missing -q` | 357 passed; 96% statement coverage (1,871 statements, 77 missed); digest API 100%, runner 99%. |
| `npm test -- --run` | 117 passed in 12 files; 37 explicit `expectAccessible` call sites, 42 axe scans including parameterized states; no reported violations. jsdom's paint-dependent color contrast is excluded; token tests check contrast in both themes. |
| `npm run build` | TypeScript and production Vite build passed. |
| `python3 -m unittest discover -s scripts -p 'test_*.py' -v` from `frontend/` | 5 passed after adding the final-report verification. The earlier root-level discover found 0 tests; this command uses the correct directory. |
| `openspec validate redesign-ui-ux --strict` | Valid. |
| `docker build -t catchup-redesign-group13-final .` and `scripts/docker-smoke.sh catchup-redesign-group13-final` | Passed with Docker 29.8.0: health, Host validation, manifest/worker/offline assets and MIME, non-root process, database volume, image exclusions, and preference persistence across restart. The script used a throwaway container and volume. |
| `python3 scripts/check-style-coverage.py` from `frontend/` | Full output below: eight explained exceptions and no uncovered prototype selectors. |

```text
Static UI classes with C7 rules but no app rules (8):
  .code
  .logo
  .logo-lg
  .offline-brand
  .offline-card
  .page-history
  .page-offline
  .page-sources
Allow-listed prototype-only selectors (8):
  .code: Offline command block uses self-contained inline CSS
  .logo: Prototype wordmark; standalone offline logo was removed
  .logo-lg: Prototype-only large wordmark
  .offline-brand: Prototype offline card; standalone page owns its own CSS
  .offline-card: Prototype offline card; standalone page owns its own CSS
  .page-history: Generic .page grid handles the History wrapper
  .page-offline: Standalone offline page does not load app CSS
  .page-sources: Generic .page grid handles the Sources wrapper
Uncovered prototype selectors (0):
```

Tests used fake timers and mocked network/model/feed responses. The Docker smoke script used a loopback port and intentionally polled container health; it is not a unit test. No runtime dependencies, CI job names, protected planning artifacts or prototypes were changed. Full side-by-side visual parity, keyboard-only end-to-end pass, native installation, and Safari rendering remain manual review checks, not claims of this run.

## Reviewer fixes after the final review

2026-10-08, by Claude Code after the fixed review step on group 13 (`4b65d19..abf2b3c`). Each fix was test-first. For test gaps, the old or broken behavior was re-introduced temporarily, with the file restored from an in-memory copy afterwards.

| Fix | Failing evidence |
| --- | --- |
| Offline page refresh uses `new Request('/offline.html', { cache: 'no-cache' })` | New assertion on the refresh request's `cache` mode failed, then passed. The fake worker context resolves relative `Request` URLs against `http://localhost/`, as a real worker resolves them against its own location. |
| A throwing `waitUntil` cannot turn a 200 navigation into the offline page | New test "returns the real response even if scheduling the refresh throws" failed with the old `.then(...).catch(...)` chain, then passed. |
| Disabled buttons do not change on hover (hover rules use `:not(:disabled)`) | New stylesheet assertion failed, then passed. |
| No-sources state keeps the hero "Last digest" line | New test failed, then passed. |
| Digest title "No. 3 · 5 Oct 2026 · CatchUp" (short date only, D5) | Updated title test failed against `shortDateTime`, then passed. |
| Failed `/sources` load does not show the no-sources state | With `noSources` using `!sources?.length`: 1 failed. |
| Fresh install (no model, no sources) puts "Set up your model" first | With first run suppressed when sources are empty: 1 failed. |
| A running run with zero sources shows "Generating…", not "Add sources" | With `&& !run` removed: 1 failed. |
| DigestView clears the previous digest while the next loads | With `setDigest(null)` removed: 1 failed. |
| `digest_item_count` is `null` for no-new-content and failed runs | With `0` returned instead: 2 failed. |

Checks after these fixes: `uv run pytest -q` 357 passed; `npm test -- --run` 123 passed in four consecutive full runs, one from a `TZ=UTC` shell; `npm run build` passed; style coverage reports 0 uncovered prototype selectors; script unittests passed; `openspec validate redesign-ui-ux --strict` valid. Docker was not rebuilt for this round; `sw.js` changed, and `/sw.js` serving is covered by the earlier smoke run and must be re-checked in the manual test.

Follow-up from the review of these fixes (`/code-review` 2 low findings; spec review: no must-fix or should-fix, verified in a real Chromium service worker that the refresh revalidates with `If-Modified-Since`): the install request now also uses `cache: 'no-cache'` (the install test failed first, then passed), and the refresh test pins the cache name (opening another cache now fails it). 357 backend and 123 frontend tests pass, twice in a row; the build passes.

## Automated end-to-end check with a stand-in model (2026-10-13)

Run by Claude Code before the manual test, at the user's request, against the Docker image built from `015e86c` (`catchup:redesign-e2e`). The model provider was a local OpenAI-compatible stand-in, so no real key was used. It answered `/v1/models` and `/v1/chat/completions` with valid summary and grouping JSON and reported token usage. The sources were real public feeds, and the session drove the browser pane.

| Step | Result |
| --- | --- |
| `docker build` and `scripts/docker-smoke.sh` | 11 of 11 checks passed, including `/manifest.webmanifest`, `/sw.js` and `/offline.html` |
| First run | Title "Generate · CatchUp". The only primary action is "Set up your model"; Generate is disabled with its visible reason; the rail shows "Getting started". |
| Settings | Test connection listed the stand-in's two models. After saving, the page shows "Saved key ending in 0001", and the key input is empty with the "replace" placeholder. |
| Sources | A website feed, a podcast with published transcripts (Buzzsprout), and a YouTube channel (`@GoogleDevelopers`) were previewed and confirmed. Each shows its kind and method. YouTube shows "Caption fetching is off" with a link to Settings. |
| Generate | The status region announced "Checking sources, 0 of 3" and then "Digest ready: 7 items": 5 summarized posts plus 2 Creator updates, so the count includes Creator updates. "View digest" is the only primary action, and the rail updated to "No. 1". The stand-in received 5 summary requests and 1 grouping request, all with an `Authorization` header. |
| Digest No. 1 | Title "No. 1 · 13 Oct 2026 · CatchUp". Saved counts "7 items · 2 sources". The index lists the topic and Creator updates. Kind labels are present, and the reason reads "Caption fetching is off". The first topic starts at 354 px of a 900 px viewport. |
| No new content | Generating again gave no primary action, Generate as secondary, "Tokens: 0 in / 0 out", and the hero kept "Last digest: No. 1". |
| History and delete | History has one row with its topic preview and the rail archive count. Deleting the podcast moved focus to Cancel when the confirmation opened, and to the "Your sources" heading after the delete. |
| 420 px, dark theme | Header 94 px, no horizontal overflow, all four nav links visible, dark tokens applied. |
| Simplified Chinese | After switching the digest language and adding a feed with recent items (The Verge), digest No. 2 has 7 `lang="zh-Hans"` elements (topic title, overview, 5 summaries), while item titles stay `en`. Digest No. 1 still has no `zh-Hans` marks, so the saved snapshot is kept. |
| Offline | The worker registered and cached only `/offline.html`. With the container stopped, `/digests` showed "CatchUp isn't running" in the C7 style. After restarting and clicking Reload, History came back with its data. |

**Pane artifact, not an app defect.** When the browser pane opened `http://localhost:8800` as a plain URL, service-worker registration failed with "An unknown error occurred when fetching the script", while `fetch('/sw.js')` from the page returned 200 with `text/javascript`. Opened through an attach-only launch configuration, the app registered its worker itself. Installation in a real Chrome is part of the manual test.

**Not covered by this run:** summaries from the real model, a failed run (it needs new items and a failing provider), and Chrome's install UI.

## Real model run and visual check (2026-10-13)

The user entered their DeepSeek key in Settings themselves; Claude never saw it. Claude then generated a digest through the UI against the real provider (`deepseek-flash`, digest language Simplified Chinese):

- The status region went "Checking sources, 0 of 3" → "Summarizing, 0 of 7" … "7 of 7" → "Digest ready: 7 items" in about 20 seconds.
- Tokens: 3,652 in / 4,855 out.
- The YouTube source failed with "The source could not be fetched." This is YouTube's intermittent RSS failure seen before, not part of this change.
- Digest No. 3 has 6 Chinese topics and 25 `lang="zh-Hans"` elements, and item titles stay `en`. One short summary sits in a narrow column beside a long one. The first topic starts at 381 px of a 900 px window.

Visual check by screenshots of every screen at 1440 px light and 420 px dark. No layout defects. Two observations:

1. **Single-item topics leave the right third of the row empty.** Real digests often have one item per topic, and a long item spans 6 of the 9 content columns. This is filed as a follow-up issue, together with the grouping granularity.
2. **Settings Save sat below the fold.** In the manual test, the user tested the connection and did not save. The fix (task 14.7) makes the save bar sticky with a full-width background, and the message now names Save. New tests failed first: a stylesheet assertion and the message text. 124 frontend tests pass. Screenshots at 1440 px and 420 px show Save at 843–884 px of a 900 px window from the first paint, with no overflow.
