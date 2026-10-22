# Test report: add-browser-extension (#58)

2026-10-21. Implemented in task order, with tests written and observed failing before the corresponding implementation. The backend uses offline HTTP and model fakes. Extension tests use invented DOM fixtures, a fake Chrome API, and mocked `fetch`; no real X page or authenticated content was copied into the tests.

## Red-first results by group

| Group | Observed before implementation | After implementation |
| --- | --- | --- |
| 1. Tokens and middleware | Migration, token CRUD, restricted Bearer access, and status checks failed before their implementation. | **601 backend tests passed**. |
| 2. Saved-page API | Capture validation/replacement/removal, built-in source, waiting count, and image-filter checks failed first. | **615 backend tests passed**. |
| 3. Digest and context | Saved-page-only run and captured context scenarios failed first. | **623 backend tests passed**. |
| 4. Frontend | Built-in source and waiting-page UI, model-form isolation, connection, copy and disconnect tests failed first. | **229 frontend tests passed**; build passed. |
| 5. Extension foundation and Follow | Missing manifest/options/popup imports failed the package tests; connected popup checks then failed (11 of 12) until Follow was implemented. A first manifest read used Vite's non-file `import.meta.url` and was corrected to a filesystem path. | **19 extension tests passed**; build passed. |
| 6. Generic extractor and Add | The generic extractor import was missing, then seven add-page popup cases failed before the button and save path existed. | **32 extension tests passed**; build passed. |
| 7. X posts | The X extractor import and three popup routing checks failed first. A quoted-status regression then failed in both direct and serialized modes before matching all status anchors. | **41 extension tests passed**; build passed. |
| 8. CI and guide | Both CI-job and README contract tests failed before the extension job and loading instructions were added. | **43 extension tests passed**, `actionlint` and build passed. |

The three named temporary backend mutations in task 1.3 were each observed failing and reverted: accepting a valid token on every route, skipping token lookup, and not updating `last_used_at`. The task 6.1 named mutation moved `httpUrl` out of `extractGeneric`: all three serialized fixture checks failed with `ReferenceError` while direct checks passed. Restoring the helper inside the function made all six generic checks green. No mutation remains in the branch.

An initial `uv run pytest` selected Python 3.11 and failed to collect an unchanged test using Python 3.12 f-string syntax. `uv sync --python 3.12` fixed the environment without editing the test. For the new extension package, npm 10.8.2's peer resolver threw `Cannot read properties of null (reading 'edgesOut')` when first creating the lockfile. Generating it with `npm install --legacy-peer-deps` resolved that install-time issue; a subsequent plain `npm ci` succeeded. The package test fixture was corrected to wait for the asynchronous connection response and use the project's axe-violation assertion style. The first type check needed `@types/node`, and an anchor selector needed an `HTMLAnchorElement` type; both were corrected before checking off the task.

## Final automated checks

Commands were run in the order specified by task 8.2:

| Command | Result |
| --- | --- |
| `cd frontend && npm run build` | Passed; 41 modules transformed. |
| `cd backend && uv run pytest --cov=catchup --cov-report=term` | **623 passed**, **96%** statement coverage, 2,494/2,586 statements covered (92 missed). `api/extension.py` **95%** (137/144), `main.py` **99%** (121/122), `digest/runner.py` **99%** (271/274), `sources/feeds.py` **97%** (248/256). |
| `cd frontend && npm test -- --run` | **229 passed** in 14 files. |
| `cd extension && npm test -- --run` | **43 passed** in 7 files, including the three missing-build-file checks and direct/serialized extractor fixtures. |
| `cd extension && npm run build` | Passed; type check and Vite build, with `dist/manifest.json`, popup, options and PNG icon present. |
| `docker build -t catchup:extension-local .` | Passed locally; no push. |
| `scripts/docker-smoke.sh catchup:extension-local` | Passed: health, API, HTML/PWA files, saved preference, non-root process, volume database, image exclusions and persistence after restart. The script cleans its throwaway container and volume. |
| `openspec validate add-browser-extension --strict` | Passed. |
| `actionlint .github/workflows/ci.yml` | Passed. |

## Manual checks not performed

- Loading the unpacked extension in a real Chrome or Edge browser.
- Observing which `Origin` the CatchUp server sees from the real extension.
- Checking whether pressing the popup button grants `activeTab` for a live tab.
- Saving a real X post in the user's own logged-in browser; this requires the user's own risk decision under X's terms.

These browser checks remain for review. Automated tests do not prove browser permissions or live DOM compatibility.
