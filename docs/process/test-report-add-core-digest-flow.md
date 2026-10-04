# Test report: add-core-digest-flow

2026-10-03. All automated tests used pytest temporary data directories, blocked unmocked DNS/socket connections, respx feed/provider mocks, and fake model clients. No real network, real API key, or fixed test sleeps were used. Manual review is separate.

## Commands and results

Run from `backend/` unless otherwise noted:

| Command | Result |
| --- | --- |
| `uv run pytest -q tests/test_digest_history.py tests/test_discovery.py tests/test_digest_runner.py` | 36 passed, 0 failed |
| `uv run pytest -q tests/test_core_flow.py` | First attempt failed (incorrect fake provider dependency override); fixed the test, then 1 passed |
| `uv run pytest` | 147 passed, 0 failed |
| `uv run pytest --cov=catchup --cov-report=term` | 147 passed, 0 failed; 95% total statement coverage |
| `npm test -- --run` (from `frontend/`) | Initial attempt could not find `vitest`; installed locked dependencies with `npm ci`, then 19 passed across 6 files, 0 failed |
| `npm ci` (from `frontend/`) | Installed 120 packages; 0 audit vulnerabilities |
| `npm run build` (from `frontend/`) | TypeScript and Vite build passed |
| `openspec validate add-core-digest-flow --strict` (from repository root) | Valid |

The SQLite migration stays unchanged: `UTCDateTime` uses `DateTime(timezone=True)` as its underlying type and the same SQLite `DATETIME` columns as `0001_initial.py`. Existing naive SQLite UTC values are read back with a UTC offset.

## Backend coverage

From `uv run pytest --cov=catchup --cov-report=term`:

| Module (`src/catchup/`) | Statements | Missed | Coverage |
| --- | ---: | ---: | ---: |
| `__init__.py` | 0 | 0 | 100% |
| `api/__init__.py` | 0 | 0 | 100% |
| `api/digests.py` | 22 | 0 | 100% |
| `api/runs.py` | 22 | 0 | 100% |
| `api/settings.py` | 100 | 7 | 93% |
| `api/sources.py` | 97 | 12 | 88% |
| `collection.py` | 57 | 0 | 100% |
| `config.py` | 16 | 0 | 100% |
| `crypto.py` | 13 | 0 | 100% |
| `db.py` | 28 | 0 | 100% |
| `digest/__init__.py` | 0 | 0 | 100% |
| `digest/group.py` | 67 | 4 | 94% |
| `digest/runner.py` | 141 | 2 | 99% |
| `digest/summarize.py` | 46 | 4 | 91% |
| `errors.py` | 20 | 0 | 100% |
| `llm/__init__.py` | 0 | 0 | 100% |
| `llm/client.py` | 67 | 5 | 93% |
| `llm/prompts.py` | 14 | 0 | 100% |
| `main.py` | 69 | 2 | 97% |
| `models.py` | 111 | 2 | 98% |
| `net/__init__.py` | 0 | 0 | 100% |
| `net/safe_fetch.py` | 101 | 11 | 89% |
| `sources/__init__.py` | 0 | 0 | 100% |
| `sources/discovery.py` | 73 | 6 | 92% |
| `sources/feeds.py` | 55 | 2 | 96% |
| **TOTAL** | **1119** | **57** | **95%** |

## Spec scenario coverage

Test names without a path in this table are in `backend/tests/`; frontend tests are under `frontend/src/pages/`. The API integration test is `test_core_flow.py::test_incremental_api_flow_with_stored_citations`.

| Spec | Scenario | Test(s) |
| --- | --- | --- |
| model-settings | Save a configuration | `test_settings_api.py::test_save_and_read_encrypted_configuration`, `test_core_flow.py::test_incremental_api_flow_with_stored_citations` |
| model-settings | Update without re-entering the key | `test_settings_api.py::test_update_without_reentering_key` |
| model-settings | Valid credentials | `test_settings_api.py::test_can_test_unsaved_key_and_list_provider_models`, `test_core_flow.py::test_incremental_api_flow_with_stored_citations` |
| model-settings | Invalid key | `test_settings_api.py::test_provider_errors_are_safe` (parameterized authentication case), `Settings.test.tsx` (authentication message) |
| model-settings | Unreachable provider | `test_settings_api.py::test_provider_errors_are_safe` (connection case), `test_llm_client.py::test_connection_timeout`, `test_llm_client.py::test_lists_provider_models` (15-second timeout configuration) |
| model-settings | Reading settings | `test_settings_api.py::test_save_and_read_encrypted_configuration`, `test_settings_api.py::test_invalid_request_never_echoes_submitted_key` |
| model-settings | Missing instance secret | `test_settings_api.py::test_missing_instance_secret_refuses_save` |
| model-settings | Base URL changed without a key | `test_settings_api.py::test_changed_provider_requires_new_key_for_save_and_test` |
| model-settings | Request for an unknown host | `test_allowed_hosts.py::test_disallowed_host_rejected_before_action` |
| model-settings | Insufficient balance | `test_settings_api.py::test_provider_errors_are_safe` (balance case), `test_digest_runner.py::test_auth_or_balance_fails_immediately_with_pending_items` |
| source-management | Pasting a feed URL | `test_sources_api.py::test_preview_does_not_write_and_limits_entries`, `test_discovery.py::test_direct_feed_and_declared_html` |
| source-management | Pasting a website URL that declares a feed | `test_discovery.py::test_direct_feed_and_declared_html`, `test_sources_api.py::test_declared_html_article_notice` |
| source-management | Website exposes a feed without declaring it | `test_discovery.py::test_reddit_path_dot_rss_probe`, `test_discovery.py::test_origin_feed_probe_notices_site_scope` |
| source-management | Pasting a single article URL | `test_sources_api.py::test_declared_html_article_notice`, `test_discovery.py::test_article_page_follows_whole_site` |
| source-management | No feed found | `test_sources_api.py::test_no_feed_and_not_a_feed`, `test_discovery.py::test_no_candidate_succeeds_and_probing_is_bounded` |
| source-management | Duplicate source | `test_sources_api.py::test_duplicate_preview_and_confirm_name_existing_source` |
| source-management | Confirm a feed with old and recent entries | `test_sources_api.py::test_confirm_marks_first_add_baseline[2-10-1-2-11]` |
| source-management | Confirm a feed with many recent entries | `test_sources_api.py::test_confirm_marks_first_add_baseline[8-0-0-5-3]` |
| source-management | Delete a source | `test_sources_api.py::test_list_status_and_delete_keeps_digest_snapshot`, `test_digest_history.py::test_digest_detail_uses_snapshot_positions_and_survives_source_deletion` |
| source-management | Internal address | `test_sources_api.py::test_invalid_and_blocked_urls`, `test_safe_fetch.py::test_rejects_non_public_addresses` |
| source-management | Redirect to an internal address | `test_safe_fetch.py::test_redirect_to_metadata_is_blocked_before_request` |
| source-management | Slow or oversized response | `test_safe_fetch.py::test_timeout`, `test_safe_fetch.py::test_oversized_stream`, `test_safe_fetch.py::test_slow_drip_aborts_after_wall_clock_deadline` |
| content-collection | Source unreachable | `test_collection.py::test_failed_source_does_not_prevent_checking_another_source`, `test_collection.py::test_fetch_or_parse_failure_never_reports_no_new_items` |
| content-collection | Nothing new | `test_collection.py::test_repeated_entries_are_not_reinserted_or_changed`, `test_core_flow.py::test_incremental_api_flow_with_stored_citations` |
| content-collection | Repeated entries | `test_collection.py::test_repeated_entries_are_not_reinserted_or_changed`, `test_core_flow.py::test_incremental_api_flow_with_stored_citations` |
| content-collection | Late entry with an old publish date | `test_collection.py::test_late_entry_is_new_despite_older_publish_date` |
| content-collection | Site changes an entry identifier | `test_collection.py::test_changed_identifier_same_link_is_not_new` |
| content-collection | Failure then success | `test_collection.py::test_failed_check_then_success_recovers_both_items` |
| content-collection | All entries unseen | `test_collection.py::test_possible_gap_only_with_prior_items_and_no_match`, `test_collection.py::test_linkless_new_entry_can_signal_gap` |
| content-collection | Feed provides only a short excerpt | `test_collection.py::test_short_feed_excerpt_is_replaced_with_extracted_article`, `test_sources_api.py::test_confirm_enriches_short_pending_entry_but_not_baseline` |
| digest-generation | Start a run | `test_digest_runner.py::test_api_rejects_unconfigured_and_reports_active_progress`, `test_core_flow.py::test_incremental_api_flow_with_stored_citations`, `Generate.test.tsx` |
| digest-generation | Run already active | `test_digest_runner.py::test_api_rejects_unconfigured_and_reports_active_progress`, `Generate.test.tsx` |
| digest-generation | Following progress | `test_digest_runner.py::test_api_rejects_unconfigured_and_reports_active_progress`, `Generate.test.tsx` |
| digest-generation | Long gap | `test_digest_runner.py::test_long_gap_snapshots_every_item_once_and_delivers_atomically` |
| digest-generation | Run fails before saving | `test_digest_runner.py::test_group_failure_preserves_pending_and_retry_uses_cached_summary`, `test_digest_runner.py::test_save_failure_rolls_back_snapshot_and_delivery` |
| digest-generation | Nothing new and one failure | `test_digest_runner.py::test_no_content_reports_failed_source_without_digest`, `Generate.test.tsx` |
| digest-generation | Retry after failure | `test_digest_runner.py::test_group_failure_preserves_pending_and_retry_uses_cached_summary` |
| digest-generation | Item missing from grouping | `test_digest_runner.py::test_missing_group_ref_goes_to_other_and_unknown_ref_is_ignored`, `test_digest_stages.py::test_group_discards_unknown_refs_and_duplicates_and_places_omissions` |
| digest-generation | Model returns an unknown item reference | `test_digest_runner.py::test_missing_group_ref_goes_to_other_and_unknown_ref_is_ignored`, `test_core_flow.py::test_incremental_api_flow_with_stored_citations` (fixture links, not model links) |
| digest-generation | Choose Chinese at setup | `test_digest_runner.py::test_language_change_resummarizes_and_keeps_old_snapshot`, `test_digest_stages.py::test_group_discards_unknown_refs_and_duplicates_and_places_omissions` (language prompt), `Settings.test.tsx` |
| digest-generation | Change language after earlier runs | `test_digest_runner.py::test_language_change_resummarizes_and_keeps_old_snapshot`, `test_digest_stages.py::test_summary_cache_language_prompt_truncation_and_unavailable` |
| digest-generation | Generate before setup | `test_digest_runner.py::test_api_rejects_unconfigured_and_reports_active_progress`, `Generate.test.tsx` |
| digest-generation | Restart during a run | `test_digest_runner.py::test_recovery_marks_unfinished_failed_and_allows_retry` |
| digest-generation | Empty model response | `test_llm_client.py::test_empty_response_retries`, `test_llm_client.py::test_empty_choices_retries` |
| digest-generation | Rejected key during a run | `test_digest_runner.py::test_auth_or_balance_fails_immediately_with_pending_items`, `test_digest_stages.py::test_auth_failure_does_not_wait_for_another_model_worker` |
| digest-history | Several digests | `test_digest_history.py::test_history_lists_three_newest_first_with_counts`, `History.test.tsx` |
| digest-history | Open an older digest | `test_digest_history.py::test_digest_detail_uses_snapshot_positions_and_survives_source_deletion`, `DigestView.test.tsx` |
| digest-history | Restart | `test_digest_history.py::test_digest_history_survives_new_app_on_same_data_directory` |

**Scenarios without a test:** None. An automated audit compared all 48 `#### Scenario:` headings to the 48 table rows and verified 79 backend test references against definitions; none were missing or unknown. Additional regression tests: `test_digest_history.py::test_stored_timestamps_are_utc_across_endpoints` checks timestamps in source, run and digest responses (including conversion from a non-UTC offset); `test_discovery.py::test_unsafe_entry_links_fall_back_to_feed_url` rejects non-HTTP(S) entry links.

## Manual verification

Performed 2026-10-03 by Claude Code with the user.

**Setup:** branch at `e710af7`, run locally with a throwaway data directory. The user entered their own DeepSeek key in Settings; Claude never handled it. Model `deepseek-flash`, digest language 简体中文.

**Sources** (added through the UI, preview then confirm):

| Source | Result |
| --- | --- |
| `https://simonwillison.net/` | declared Atom feed found |
| `https://bsky.app/profile/bsky.app` | declared RSS feed found |
| `https://mastodon.social/@Mastodon` | declared RSS feed found |
| `https://www.reddit.com/r/programming/` | no declared feed; probing found `/r/programming.rss` |

**Run 1: failed.**
- Stage 1: 7 of 11 summaries succeeded; 4 came back as empty content after retries.
- Stage 2: the grouping call returned empty content, so the run failed with `provider_error`.
- As designed, all 11 items stayed pending and the 7 summaries stayed cached.
- In the same run Reddit answered HTTP 429. It was recorded as `failed` with `http_status=429`, separately from "no new items", and the run continued.

**Diagnosis:** DeepSeek's docs say thinking mode is on by default at "high" effort. The original budgets (512 per summary, 776 for grouping) left no room for the answer after reasoning.

**Experiment:** budgets raised locally, uncommitted (4096 per summary; 8192 + 24 per item for grouping).

**Run 2: succeeded** in 22 s.
- 11/11 summaries, 0 unavailable, 6 topics.
- Chinese output is fluent; topic grouping is sensible.
- Links, source names, and local times are correct.
- Reddit answered 200 this time, so the earlier 429 was transient rate limiting.

**Issues found that the mocked tests could not catch:**

| Issue | Severity | Status |
| --- | --- | --- |
| Output budgets too small for DeepSeek's default reasoning | must | task 8.1 |
| Bluesky/Mastodon entries titled "Untitled" (no `<title>` in their RSS) | should | task 8.2 |
| Whole-site notice wrongly shown on profile pages | should | task 8.3 |
| Summaries describe metadata (DIDs, user handles, "submitted by …") | should | task 8.4 |
| Reddit link posts carry no content in RSS (only "[link] [comments]") | later | next change: extract the linked article |
| Reddit 429 under repeated requests | later | next change: e.g. a descriptive User-Agent, backoff |

A re-test after tasks 8.1–8.4 is recorded below.
