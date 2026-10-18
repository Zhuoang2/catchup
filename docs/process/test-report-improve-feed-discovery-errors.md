# Feed discovery errors: implementation checks

2026-10-18, branch `improve-feed-discovery-errors`. Backend commands ran from `backend/`, frontend commands from `frontend/`, and OpenSpec/Docker commands from the repository root.

| Check | Actual result |
| --- | --- |
| `uv run pytest tests/test_discovery.py -q` after new tests, before D1/D2 | Expected red: **5 failed, 23 passed**. The refused-page and declared-feed-404 scenarios failed; the no-probing cases and mixed-failure case already passed. |
| `uv run pytest tests/test_discovery.py -q --tb=short` after D1/D2 | **28 passed**. First run found an incorrect test expectation of eight probes for the root URL; root-path deduplication gives seven. Corrected the test, then reran green. |
| `uv run pytest --cov=catchup.api.sources --cov=catchup.sources.discovery --cov-report=term -q --tb=short` before API changes | **380 passed**, `api/sources.py` **91%** (109 statements, 10 missed), `sources/discovery.py` **96%** (123 statements, 5 missed). |
| `uv run pytest tests/test_sources_api.py -q --tb=short` after new tests, before D3 | Expected red: **3 failed, 42 passed**. Both missing `http_status` fields and the confirm-time `fetch_failed` code failed; the unchanged rate-limit case passed. |
| `uv run pytest --cov=catchup.api.sources --cov=catchup.sources.discovery --cov-report=term -q --tb=short` after D3 | **384 passed**, `api/sources.py` **91%** (116 statements, 10 missed), `sources/discovery.py` **96%** (123 statements, 5 missed). Neither changed module's coverage dropped. |
| `npm ci` | Installed **124 packages** from the lockfile, **0 vulnerabilities** reported; needed because Vitest was missing from this worktree. |
| `npm test -- --run src/pages/Sources.test.tsx` after new tests, before D4 | Expected red: **6 failed, 15 passed**. The unchanged no-status fetch message already passed. |
| `npm test -- --run` after D4 and again at final checks | **173 passed** across **13 files** each time. |
| `npm run build` after D4 and again at final checks | Passed TypeScript and Vite build; **41 modules** transformed each time. |
| `uv run pytest --cov=catchup --cov-report=term -q --tb=short` at final checks | **384 passed**, **96%** statement coverage (**1,839/1,913** statements); `api/sources.py` **91%**, `sources/discovery.py` **96%**. |
| `openspec validate improve-feed-discovery-errors --strict` | Valid. |
| `docker version`; `docker build -t catchup:improve-feed-discovery-errors .` | Docker daemon available; local image build passed, including the frontend TypeScript/Vite build. No image was pushed. |
| `test -f docs/process/test-report-improve-feed-discovery-errors.md` before creating this report | Expected red: exit status 1 (report absent). |

All automated tests use fixture responses, mock DNS/network access, and no real sleeps. **Manual check not performed:** pasting `https://spaces.ac.cn/` into a local CatchUp instance to verify the live feed preview. The local Docker image was built, not run.
