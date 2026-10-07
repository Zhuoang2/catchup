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
