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

## Review fixes, round 1

2026-10-16, branch `show-latest-digest-on-home`. Commands ran from the repository root unless noted.

| Check | Actual result |
| --- | --- |
| `cd backend && uv run pytest --cov=catchup --cov-report=term` | **362 passed**; **96%** statement coverage (1,879 statements, 77 missed); `api/digests.py` **100%** (48 statements, 0 missed). |
| `cd frontend && npm test -- --run` | **152 passed** in **13 files**. Existing accessibility/axe assertions passed; zero reported violations. |
| `cd frontend && npm run build` | Passed TypeScript and Vite production build (**41 modules**). |
| `python3 frontend/scripts/check-style-coverage.py` | Passed: **9** documented prototype-only/generic-grid classes (including the removed Home `.hero-last`), **0** uncovered prototype selectors. |
| `python3 -m unittest discover -s frontend/scripts -p test_check_style_coverage.py` | **3 passed**. |
| `openspec validate show-latest-digest-on-home --strict` | Valid. |
| `docker build -t catchup-show-latest-digest-on-home .` | Passed locally with Docker **29.8.0**, including frontend TypeScript and Vite compilation. No image was pushed. |

The review tests reproduced stale Home alerts, the extra first-digest action, mismatched load-error text, and a digest fetch discarded across overlapping runs before their fixes. Three previously weak success-path tests failed without a mocked detail response, then passed when they loaded the article. The Home/History article comparison passed with only the agreed run-bar, back-link, and class differences. Task 6.7 was a behavior-preserving refactor under the existing **49** passing Home tests, without a new failing test. The CSS test failed on the redundant narrow rule before the style fix. The new backend `created_at`-before-id ordering test passed immediately because the endpoint already uses that order. The first style-coverage run failed because the archived prototype still references `.hero-last`; documenting it as prototype-only made the audit pass without restoring dead app CSS.

**Manual checks not performed in this round:** painted layouts at 1440, 900, and 420 px, and a real run that swaps its digest in place. Browser keyboard behavior and live model/feed integration remain for review.
