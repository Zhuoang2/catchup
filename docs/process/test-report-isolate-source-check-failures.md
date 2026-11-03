# Isolate source check failures: implementation checks

2026-11-03, branch `isolate-source-check-failures` (#66), from plan commit `1f9b993`. Implemented by Claude Code (a Claude Opus 5.5 sub-agent) in place of Factory Droid, whose login had expired. Backend commands ran from `backend/` with Python 3.12, frontend and extension commands from their folders, and OpenSpec and Docker commands from the repository root. Before any change, `uv run -p 3.12 pytest -q` passed **776 tests**.

## Red first

Each test was written before its implementation and run on the unchanged code. Every red result failed for the reason the task names.

| Task | Tests | Observed red result on the unchanged code |
| --- | --- | --- |
| 1.1 | `tests/test_urls.py` (10 cases) | Collection error: `ModuleNotFoundError: No module named 'catchup.net.urls'`. |
| 1.2 | `test_feeds.py::test_filter_image_urls_skips_addresses_that_cannot_be_joined` | `ValueError: 'object Object' does not appear to be an IPv4 or IPv6 address` from `urljoin` at `feeds.py:122`. |
| 1.2 | `test_feeds.py::test_parse_feed_keeps_entry_with_malformed_image_media_and_link` | `ValueError: Invalid IPv6 URL` from `_Links.handle_endtag` (`feeds.py:224`), for `<a href="http://&#91;x">`. |
| 1.2 | `test_extension_api.py::test_capture_skips_image_whose_address_cannot_be_parsed` | The same `ValueError` escaped `POST /api/captures` through the test client (a 500 in production). |
| 1.2 | `test_digest_runner.py::test_malformed_address_in_one_entry_does_not_fail_the_run` | Run status `failed` instead of `succeeded`; log: "Unexpected digest generation failure for run 1 (ValueError)"; source 2 was never fetched. |
| 1.3 | `test_context_links.py::test_unparsable_item_link_or_site_url_matches_nothing` (2 cases) | `ValueError: Invalid IPv6 URL` at `links.py:19` (item link `http://[x`), and `ValueError: 'object Object' ...` at `links.py:21` (site URL `https://[object Object]/`). |
| 1.3 | `test_context_links.py::test_unparsable_link_is_skipped` | Guard: passed on the unchanged code, as planned (`links.py` already catches it). |
| 1.3 | `test_discovery.py::test_declared_feed_that_cannot_be_joined_is_skipped` | `ValueError: Invalid IPv6 URL` at `discovery.py:118`; the bad `href` comes first. |
| 1.4 | `test_safe_fetch.py::test_url_httpx_rejects_is_invalid_url_without_a_request` | `httpx.InvalidURL: Invalid non-printable ASCII character in URL, '\x7f' at position 24.` |
| 1.4 | `test_safe_fetch.py::test_preview_of_url_httpx_rejects_is_invalid_url` | The same `httpx.InvalidURL` escaped `POST /api/sources/preview`. |
| 1.4 | `test_sources_api.py::test_entry_link_httpx_rejects_keeps_feed_text` | `httpx.InvalidURL ... at position 22` escaped `article_text` (DNS mocked, so it was raised after the address check). |
| 2.1 | `test_digest_runner.py::test_unexpected_error_in_one_source_is_recorded_and_the_run_goes_on` | Run status `failed`; log: "... (RuntimeError)". |
| 2.1 | `test_digest_runner.py::test_unexpected_error_in_one_x_account_keeps_its_charged_reads` | Run status `failed`; log: "... (RuntimeError)". |
| 2.1 | `test_digest_runner.py::test_source_deleted_during_its_check_is_skipped` | Run status `failed`; log: "... (IntegrityError)". |
| 2.2 | `test_caption_pass.py::test_channel_deleted_during_caption_pass_is_skipped` | Run status `failed`; log: "... (StaleDataError)". |
| 2.2 | `test_caption_pass.py::test_caption_failure_for_one_item_keeps_its_status_and_goes_on` | Run status `failed`; log: "... (RuntimeError)". |

All of these passed after their implementation. After group 1 the full backend suite passed **797 tests**; after group 2, **802 tests**.

## Named mutations

Each mutation was applied to the implemented code, the named test was run, and the file was restored from a copy. No mutation remains.

| Task | Temporary mutation | Result |
| --- | --- | --- |
| 1.2 | Call `urljoin` directly in `filter_image_urls` again. | `test_filter_image_urls_skips_addresses_that_cannot_be_joined` **failed** with `ValueError: 'object Object' ...` at `feeds.py:123`. |
| 1.3 (guard) | Remove the `try` around each link in `related_links`. | `test_unparsable_link_is_skipped` **failed** with `ValueError: Invalid IPv6 URL` at `links.py:27`. |
| 1.4 | Remove the `httpx.InvalidURL` mapping. | `test_url_httpx_rejects_is_invalid_url_without_a_request` **failed** with `httpx.InvalidURL`. |
| 2.1 | Re-raise in the guard instead of recording `failed`. | `test_unexpected_error_in_one_source_is_recorded_and_the_run_goes_on` **failed**: status `failed`, log "... (RuntimeError)". |
| 2.2 (extra, not named in the plan) | Drop the `if item is None: continue` skip in `caption_pass`. | `test_channel_deleted_during_caption_pass_is_skipped` **failed**: warning "Caption pass failed for item 2 (AttributeError)", so item 2 was not skipped without an error. |

## Final checks (task 3.2, in order)

| Check | Actual result |
| --- | --- |
| `npm run build` in `frontend/` | Passed TypeScript and Vite; **41 modules** transformed. |
| `uv run --python 3.12 pytest --cov=catchup --cov-report=term` in `backend/` | **802 passed**, **97% overall** (3,074/3,183 statements, 109 missed). New `net/urls.py` **100%**, `context/links.py` **100%**, `digest/runner.py` **98%**, `sources/feeds.py` **98%**, `sources/discovery.py` **97%**, `net/safe_fetch.py` **94%**. |
| `npm test -- --run` in `frontend/` | **259 passed** in 14 files. |
| `npm test -- --run` in `extension/` | **112 passed** in 8 files (unchanged, as a guard). |
| `docker build -t catchup:isolate-local .` | Passed. |
| `scripts/docker-smoke.sh catchup:isolate-local` | Passed: all 11 checks (health, HTML, manifest, service worker, offline page, saved preference, non-root, database on volume, no `.env` or source tree, preference after restart). The image was then removed. |
| `DO_NOT_TRACK=1 openspec validate isolate-source-check-failures --strict` | Valid. |

## Notes

- **Where some checks live.** The preview 422 check for `https://public.example/a\x7fb` is in `test_safe_fetch.py`, whose `resolve` fixture answers `public.example` with a public address; `test_sources_api.py`'s fixture answers it with `127.0.0.1`, which would give `blocked_address`. The `article_text` check is in `test_sources_api.py`, next to the existing ones, with a `site.example` link. The discovery check calls both `discover` and `POST /api/sources/preview`.
- **`related_links`.** `split_url` is used for the item link and the site URL; the existing `try` around each link stays, so the guard and its mutation still apply.
- **The run test in 1.2** sets `context_fetches_per_run=0`, so the entry's good link is not fetched as context, and asserts the run status before the route counts, so its red result shows the failed run.
- **Caption pass.** An item whose channel is deleted while its captions are fetched fails at its commit (`StaleDataError`) and is logged as a warning with its id; the later items of that channel are skipped without a log.
- **Not covered:** `check_one_source`'s early return when a source is already gone before its check starts (`runner.py:131`), the same skip the loop's `if source is not None` made before.
- **Manual check not performed:** a run on a local instance with a real feed that has a malformed image address.
