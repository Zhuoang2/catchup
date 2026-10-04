# Review notes

## Task 4.1, content collection (2026-10-03)

Verification: `uv run pytest --cov=catchup --cov-report=term` (113 passed, 95% overall coverage, 100% collection.py); `npm test -- --run` (9 passed); `npm run build` (passed); `openspec validate add-core-digest-flow --strict` (passed). All HTTP requests were mocked with respx and DNS was patched; the test fixture isolated SQLite in pytest temporary directories. No real model key was used.

Content-collection spec scenarios:

| Scenario | Test |
| --- | --- |
| Source unreachable; other sources checked | `test_failed_source_does_not_prevent_checking_another_source`, `test_fetch_or_parse_failure_never_reports_no_new_items` |
| Nothing new | `test_repeated_entries_are_not_reinserted_or_changed` |
| Repeated entries | `test_repeated_entries_are_not_reinserted_or_changed` |
| Late entry with old publish date | `test_late_entry_is_new_despite_older_publish_date` |
| Site changes an entry identifier | `test_changed_identifier_same_link_is_not_new` |
| Failure then success | `test_failed_check_then_success_recovers_both_items` |
| All entries unseen (possible gap) | `test_possible_gap_only_with_prior_items_and_no_match`, `test_linkless_new_entry_can_signal_gap` |
| Feed provides only a short excerpt | `test_short_feed_excerpt_is_replaced_with_extracted_article`, `test_confirm_enriches_short_pending_entry_but_not_baseline` |

Additional fallback, status, empty-feed, and linkless-entry cases are covered in `backend/tests/test_collection.py`. The per-run source iteration and UI display remain in task group 5.

### Claude Code review of task 4.1 (2026-10-03)

- Re-ran in a fresh worktree: 113 backend tests, 9 frontend tests, build, and strict validation pass, and no `backend/data` is created. Coverage reproduced as **94%** overall (735/778; Droid reported 95%, a rounding-level difference) and 100% for `collection.py`.
- Code read in full. Confirmed:
  - one transaction per source
  - feed-URL links excluded from the secondary link match
  - the gap flag requires prior items and no match
  - HTTP status recorded on both failure and success
  - article extraction only through `safe_fetch`, with fallback to the feed text
- Verdict: **no required fixes.**
- Known trade-off, not a defect: article extraction runs synchronously inside `check_source` and at confirm time. The worst case is ~30 s per short entry (the `safe_fetch` deadline); typical pages take 1–2 s. Group 5 should show progress during the collecting stage so long collections stay understandable.

## Task group 5, digest generation (2026-10-03)

Verification: focused `uv run pytest -q tests/test_digest_stages.py tests/test_digest_runner.py` (17 passed); full `uv run pytest` (130 passed); `npm test -- --run` (15 passed); `npm run build` (passed); `openspec validate add-core-digest-flow --strict` (passed). The test sandbox blocks DNS/connect, all model calls use fakes except the existing respx-mocked adapter tests, and the instance database is under pytest's temp directory. No real key or live network was used. Frontend polling uses fake timers; backend synchronization uses events, not fixed sleeps.

Digest-generation spec scenarios:

| Scenario | Test |
| --- | --- |
| Start a run | `test_api_rejects_unconfigured_and_reports_active_progress`, `Generate.test.tsx` starts generation |
| Run already active | `test_api_rejects_unconfigured_and_reports_active_progress`, `Generate.test.tsx` resolves an active-run conflict |
| Following progress | `test_api_rejects_unconfigured_and_reports_active_progress`, `Generate.test.tsx` shows 5 of 12 and collecting sources checked |
| Long gap (140 pending) | `test_long_gap_snapshots_every_item_once_and_delivers_atomically` |
| Run fails before saving | `test_group_failure_preserves_pending_and_retry_uses_cached_summary`, `test_save_failure_rolls_back_snapshot_and_delivery` |
| Nothing new and one failure | `test_no_content_reports_failed_source_without_digest`, `Generate.test.tsx` no-new-content state |
| Retry after failure | `test_group_failure_preserves_pending_and_retry_uses_cached_summary` |
| Item missing from grouping | `test_missing_group_ref_goes_to_other_and_unknown_ref_is_ignored`, `test_group_discards_unknown_refs_and_duplicates_and_places_omissions` |
| Unknown item reference | `test_missing_group_ref_goes_to_other_and_unknown_ref_is_ignored` |
| Choose Chinese at setup | `test_language_change_resummarizes_and_keeps_old_snapshot`, `test_group_discards_unknown_refs_and_duplicates_and_places_omissions` (topic prompt language) |
| Change language after earlier runs | `test_language_change_resummarizes_and_keeps_old_snapshot`, `test_summary_cache_language_prompt_truncation_and_unavailable` |
| Generate before setup | `test_api_rejects_unconfigured_and_reports_active_progress`, `Generate.test.tsx` Settings link |
| Restart during a run | `test_recovery_marks_unfinished_failed_and_allows_retry` |
| Empty model response | `test_empty_response_retries` in `test_llm_client.py` (adapter used by runner) |
| Rejected key during a run | `test_auth_or_balance_fails_immediately_with_pending_items`, `test_auth_failure_does_not_wait_for_another_model_worker` |

Additional tests cover summary-unavailable snapshots, original-language prompt rules, batching and merge, read-once language, source-check visibility as collection commits, and failure UI. Remaining end-to-end collection-to-digest API testing and history endpoints are task groups 7 and 6 respectively.
