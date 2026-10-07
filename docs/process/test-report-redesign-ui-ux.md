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

Tests used mocked API/feed/model responses and fake timers, not live feeds or a real provider. No runtime dependencies, CI job names, protected OpenSpec plans/specs or prototype files changed in this review-fix round; only task checkboxes changed under the OpenSpec change folder. No full multi-theme visual parity, keyboard-only end-to-end pass, native PWA installation or Safari rendering was performed; the earlier manual-review limitations remain. The offline-page spot check loaded the standalone file, not a simulated service-worker navigation; the prior worker-isolation tests and Docker asset smoke still passed.

Interpretive choices: a digest with no topics and no Creator updates displays “No topics”; the Creator-only flag requires an actual Creator-updates topic. When the model-settings read fails, Generate keeps active-run visibility rather than assuming first-run setup. Sources retains the “Your sources” heading in its empty state as the post-deletion focus target. The index displays section counts as explicitly required by task 10.7, despite the older prototype cascade hiding `.toc-count`. The independent style audit still reports generic page and standalone-offline selectors rather than silently filtering them out.

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
