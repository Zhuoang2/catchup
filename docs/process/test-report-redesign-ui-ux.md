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
