# Test report: improve-source-reliability

2026-10-04. Backend tests run under the autouse temporary-data and blocked-DNS/socket fixture. Source HTTP is intercepted by respx; model responses use fake clients and test-only credentials. The retry and spacing hooks use fake clocks/sleeps, with default sleeps intercepted by the test fixture. No live network, real key, writes outside pytest temp data dirs, or real sleeps were used in tests.

## Commands and results

| Command | Result |
| --- | --- |
| `cd backend && uv run pytest tests/test_safe_fetch.py -q` | Initially 1 failure (asctime date lacked a timezone in `parsedate_to_datetime`); UTC handling added, then 42 passed |
| `cd backend && uv run pytest tests/test_feed_cache.py tests/test_discovery.py tests/test_sources_api.py -q` | 40 passed |
| `cd backend && uv run pytest tests/test_host_spacing.py tests/test_safe_fetch.py tests/test_sources_api.py tests/test_collection.py tests/test_digest_runner.py -q` | Initially 1 failure (the retry sleep hook was called with zero); avoided zero-length sleeps, then 108 passed |
| `cd backend && uv run pytest --cov=catchup --cov-report=term` | Initially 195 passed, 1 failure (old end-to-end test counted the removed confirm fetch); updated assertion, then 197 passed, 96% overall statement coverage |
| `cd backend && uv run pytest` | 197 passed |
| `cd frontend && npm ci` | 120 packages installed, 0 audit vulnerabilities |
| `cd frontend && npm test -- --run` | 22 passed across 6 files |
| `cd frontend && npm run build` | TypeScript/Vite build passed |
| `openspec validate improve-source-reliability --strict` | Valid |

## Backend coverage

From `uv run pytest --cov=catchup --cov-report=term`:

| Module (`src/catchup/`) | Statements | Missed | Coverage |
| --- | ---: | ---: | ---: |
| `config.py` | 21 | 0 | 100% |
| `main.py` | 72 | 1 | 99% |
| `net/safe_fetch.py` | 145 | 10 | 93% |
| `net/feed_cache.py` | 24 | 0 | 100% |
| `net/host_spacing.py` | 21 | 0 | 100% |
| `net/rate_limit.py` | 4 | 0 | 100% |
| `sources/discovery.py` | 88 | 7 | 92% |
| `api/sources.py` | 102 | 10 | 90% |
| `collection.py` | 58 | 0 | 100% |
| `digest/runner.py` | 144 | 2 | 99% |
| **Entire backend** | **1256** | **55** | **96%** |

## Spec scenario coverage

Every scenario in both change spec deltas is mapped below. Backend test names are under `backend/tests/`; frontend page tests are under `frontend/src/pages/`.

| Spec | Scenario | Test(s) |
| --- | --- | --- |
| source-management | Default User-Agent | `test_safe_fetch.py::test_user_agent_on_page_redirect_and_contact`, `test_safe_fetch.py::test_user_agent_fallback_and_invalid_contact`, `test_discovery.py::test_direct_feed_and_declared_html`, `test_discovery.py::test_reddit_path_dot_rss_probe`, `test_sources_api.py::test_confirm_without_preview_fetches_feed`, `test_sources_api.py::test_confirm_enriches_short_pending_entry_but_not_baseline`, `test_collection.py::test_short_feed_excerpt_is_replaced_with_extracted_article` |
| source-management | Configured contact | `test_safe_fetch.py::test_user_agent_on_page_redirect_and_contact` (redirect hop also covered) |
| source-management | Short wait requested | `test_safe_fetch.py::test_rate_limit_policy` (429 and 503, fake clock/sleep); `test_safe_fetch.py::test_retry_only_once_without_using_redirect_hop` |
| source-management | Long wait requested | `test_safe_fetch.py::test_rate_limit_policy`, `test_sources_api.py::test_rate_limited_preview_or_confirm_has_retry_after` |
| source-management | No wait given | `test_safe_fetch.py::test_rate_limit_policy`, `test_sources_api.py::test_preview_surfaces_rate_limit_on_discovered_feed` |
| source-management | Rate limited while adding a source | `test_sources_api.py::test_rate_limited_preview_or_confirm_has_retry_after`, `Sources.test.tsx` (preview and confirm errors) |
| source-management | Confirm right after preview | `test_sources_api.py::test_preview_confirm_uses_final_feed_url_once` (direct, declared and probed, including redirects), `test_feed_cache.py::test_cache_ttl_and_single_use` |
| source-management | Confirm after the window | `test_sources_api.py::test_expired_preview_refetches_feed`, `test_sources_api.py::test_confirm_without_preview_fetches_feed` |
| content-collection | Rate limited during a run | `test_digest_runner.py::test_rate_limited_run_check_is_visible_in_progress_and_source_list`, `test_collection.py::test_rate_limited_check_preserves_suggested_wait`, `test_digest_runner.py::test_run_detail_identifies_only_rate_limited_checks` (503 prefix), `test_sources_api.py::test_source_list_exposes_check_rate_limit`, `Sources.test.tsx`, `Generate.test.tsx` |
| content-collection | Two sources on one host | `test_digest_runner.py::test_runner_spaces_same_host_checks_without_delaying_other_hosts`, `test_host_spacing.py::test_host_spacing_case_insensitive_and_independent`, `test_host_spacing.py::test_fetch_uses_spacer_for_redirect_and_retry` |
| content-collection | Different hosts | `test_digest_runner.py::test_runner_spaces_same_host_checks_without_delaying_other_hosts`, `test_host_spacing.py::test_host_spacing_case_insensitive_and_independent` |

**Scenarios without a test:** None (11 scenarios in the two delta specs).

## Manual verification

Reviewer and user: pending. Preview → confirm a Reddit source without the previous ~15 s manual wait; inspect the User-Agent with a local request log or an HTTP echo service. Live Reddit and real model access were intentionally not used by the implementer.
