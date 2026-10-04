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
