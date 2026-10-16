# Show latest digest on Home: implementation checks

2026-10-15, branch `show-latest-digest-on-home`. Commands ran from the repository root unless a directory is named.

| Check | Actual result |
| --- | --- |
| `cd backend && uv run pytest --cov=catchup --cov-report=term -q` | **361 passed**; 96% statement coverage (1,879 statements, 77 missed). `api/digests.py`: **100%** (48 statements, 0 missed), unchanged from its prior 100% coverage. |
| `cd frontend && npm test -- --run` | **143 passed** in 13 files. **54 axe scans** across 46 explicit `expectAccessible` call sites, counting parameterized variants; zero violations. The jsdom color-contrast rule is disabled because jsdom does not paint; the existing token tests check both themes numerically. |
| `cd frontend && npm run build` | Passed TypeScript and Vite production build (41 modules). |
| `python3 frontend/scripts/check-style-coverage.py` | Passed: eight pre-existing allow-listed prototype-only/generic-grid classes; zero uncovered prototype selectors and no new class without a rule. |
| `openspec validate show-latest-digest-on-home --strict` | Valid. |
| `docker build -t catchup-show-latest-digest-on-home .` | Passed locally with Docker 29.8.0, including TypeScript and Vite compilation in the frontend stage. No image was pushed. |

The backend endpoint tests first failed with HTTP 422 (the missing route), then passed. The new component test initially failed to import `DigestArticle`. The Home tests failed on the list request, loading state, reading layout, run-state contents, and digest replacement before those behaviors were implemented. The app-shell tests first failed on the old Generate label. The responsive run-bar style test failed before its selectors were added. Tests use mocked fetches, fake polling timers, and backend temporary directories, not a real feed, model provider, or API key.

**Manual checks not performed:** live layout checks at 1440, 900, and 420 px; a real run whose digest swaps in place. DOM/axe tests and a Docker build do not verify painted layout, keyboard behavior in a browser, or a live end-to-end run. Those remain for the separate review.
