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
| `uv run pytest --cov=catchup --cov-report=term -q --tb=short` at final checks | **384 passed**, **96%** statement coverage (**1,838/1,913** statements, **75 missed**); `api/sources.py` **91%**, `sources/discovery.py` **96%**. |
| `openspec validate improve-feed-discovery-errors --strict` | Valid. |
| `docker version`; `docker build -t catchup:improve-feed-discovery-errors .` | Docker daemon available; local image build passed, including the frontend TypeScript/Vite build. No image was pushed. |
| `test -f docs/process/test-report-improve-feed-discovery-errors.md` before creating this report | Expected red: exit status 1 (report absent). |

All automated tests use fixture responses, mock DNS/network access, and no real sleeps. **Manual check not performed:** pasting `https://spaces.ac.cn/` into a local CatchUp instance to verify the live feed preview. The local Docker image was built, not run.

## Fix round 1

2026-10-18. Backend and frontend commands ran from their respective subdirectories, Docker and OpenSpec commands from the repository root.

| Check | Actual result |
| --- | --- |
| `uv run pytest tests/test_discovery.py::test_declared_feed_timeout_is_unavailable_without_http_status -q --tb=short` before discovery changes | Expected red: **1 failed**, returned `not_a_feed` rather than `feed_unavailable`. Repeated in the full discovery run. |
| `uv run pytest tests/test_discovery.py -q --tb=line` before 5.2 | Expected red: **9 failed, 33 passed**. A first attempt had an unmatched probe route in the Apple 404 test; after adding a mocked fallback route and allowing the intentionally uncalled `/feed`, the nine failures were the intended wrong codes or wrong feed preview. Already passing: timeout plus unparsable candidate (`not_a_feed`), last HTTP status 410, page HTTP 400 probing, page 200 size-limit no probing, and page 302 without `Location` no probing. |
| `uv run pytest tests/test_discovery.py -q --tb=short` after 5.2 | **42 passed**, including all original discovery tests. |
| `uv run pytest tests/test_sources_api.py -q --tb=line` before 5.4 | Expected red: **2 failed, 47 passed**. Oversized page and confirm-time feed still included `http_status: 200`. Already passing after 5.2: declared-feed timeout returned `feed_unavailable` without `http_status`; confirm-time HTTP 400 returned `feed_unavailable` with `http_status: 400`. |
| `uv run pytest -q --tb=short` after 5.4 | **402 passed**. |
| `npm test -- --run src/pages/Sources.test.tsx` before 5.6 | Expected red: **3 failed, 27 passed**. `fetch_failed` with 200 or 302 and `feed_unavailable` with 200 incorrectly named HTTP 200/302. Already passing: 401, 410, 500, 599, 499, and 600 produced their exact requested text. |
| `npm test -- --run` after 5.6 and at final checks | **182 passed** in **13 files** each time. |
| `npm run build` after 5.6 and at final checks | TypeScript and Vite passed; **41 modules** transformed each time. |
| `uv run pytest --cov=catchup --cov-report=term -q --tb=short` at final checks | **402 passed**, **96%** statement coverage (**1,850/1,923**, **73 missed**); `api/sources.py` **91%**, `sources/discovery.py` **96%**. |
| `openspec validate improve-feed-discovery-errors --strict` | Valid. |
| `docker version --format '{{.Server.Version}}'`; `docker build -t catchup:improve-feed-discovery-errors-fix1 .` | Docker daemon **29.8.0** available; local image build passed, including the frontend build. No image pushed or run. |
| `rg -q '^## Fix round 1' ... && rg -q '1,838/1,913' ... && rg -q '1850/1923' ...` before the documentation update | Expected red: exit status 1, the section and corrected numbers were absent. |

**Known limits (design Risks):**
- A pasted URL that redirects to another origin and fails there is probed on the original origin because `safe_fetch` does not report the final failed URL. Paste the final URL or the feed URL instead.
- A pasted feed URL that answers an HTTP error is reported as a page error because its type cannot be known before a successful fetch. Feed URLs declared by a page do report `feed_unavailable`.

**Manual check still not performed:** pasting `https://spaces.ac.cn/` into a local CatchUp instance.
