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

### Claude Code review of group 5 (2026-10-03)

- Re-ran in a fresh worktree: 130 backend tests (95% coverage; runner 98%), runner tests 3× in a row with no flakiness, no fixed sleeps in tests, 15 frontend tests, build, and strict validation. No `backend/data` is created.
- Code read in full (runner, summarize, group, prompts, runs API). Confirmed:
  - All DB writes happen on the runner thread; workers only call the model.
  - Every pending item yields exactly one result.
  - Snapshot and delivery share one transaction.
  - Auth and balance errors abort without waiting for other workers.
  - Grouping output is validated: unknown refs are dropped, duplicates removed, unplaced items go to "Other".
  - Prompts mark item content as data, not instructions.
- Verdict: **no required fixes.** Carried into the group 6 hand-off (low severity):
  1. The final `except Exception` in `run_digest` logs nothing; unexpected failures should be logged server-side without credentials.
  2. The "Other" topic title is always English; it should follow the digest language.
  3. A source deleted mid-run raises `KeyError` at save time and fails the whole run; its items should be skipped instead.
- To check in the manual DeepSeek test: whether `SUMMARY_MAX_TOKENS = 512` is enough if the model spends tokens on reasoning (empty content would show up as "summary unavailable").

## Task group 6, digest history and carried review items (2026-10-03)

Digest history reads only `digests`, `digest_topics`, and `digest_items`, in stored order. SQLite UTC dates are serialized with a timezone so the browser renders the correct time. Original links open in a new tab with `noopener noreferrer`; topic text and summaries are rendered as text, not HTML.

| Scenario or review item | Test |
| --- | --- |
| Several digests, newest first with time and counts | `test_history_lists_three_newest_first_with_counts`, `History.test.tsx` list |
| Open older digest, ordered topics/items, overview, summary, date, source and original link | `test_digest_detail_uses_snapshot_positions_and_survives_source_deletion`, `DigestView.test.tsx` rendering |
| Source deleted without changing old digest | `test_digest_detail_uses_snapshot_positions_and_survives_source_deletion` |
| App restart on the same data directory preserves list and full detail | `test_digest_history_survives_new_app_on_same_data_directory` |
| Unexpected runner exception logged without decrypted key, provider URL, or collected text | `test_unexpected_failure_is_logged_without_key_or_collected_content` |
| Fallback title in English, Simplified Chinese, original and free text, including batch merge | `test_unplaced_topic_title_follows_digest_language`, `test_unplaced_batch_topic_title_follows_digest_language` |
| Source deleted during generation: skip lost items and count only saved ones | `test_deleted_source_during_grouping_saves_only_surviving_items`, `test_all_items_deleted_during_grouping_does_not_save_empty_digest`, `test_source_deleted_during_summarization_is_skipped` |

Verification: focused backend digest tests (28 passed before the last regression was added); final `uv run pytest` (142 passed); `npm test -- --run` (19 passed); `npm run build` (passed); `openspec validate add-core-digest-flow --strict` (passed). Tests use temporary data directories, fake model calls, and blocked unmocked network access; no real key, network, or fixed sleeps. One frontend test initially matched a split text node and was corrected to query its item; one UTC assertion expected `+00:00` but FastAPI serializes UTC as `Z`, so it was corrected. Group 7 remains pending; no live feed/model check was performed.

### Claude Code review of group 6 (2026-10-03)

- Re-ran in a fresh worktree: 142 backend tests (95% coverage; `digests.py` 100%), 19 frontend tests, build, and strict validation. No `backend/data` is created.
- Confirmed:
  - The history API reads only snapshot tables, in stored order.
  - Original links use `target="_blank" rel="noopener noreferrer"`, and no `dangerouslySetInnerHTML` is used.
  - All three group 5 carry-overs are fixed and tested:
    1. Unexpected errors are logged with the traceback but the exception text is withheld.
    2. The "Other" topic title is localized (其他 for zh-Hans).
    3. Items deleted mid-run are skipped and the counts adjusted.
- Verdict: **no required fixes.** Carried into the group 7 hand-off:
  1. [bug, low] Inconsistent datetime serialization. `api/digests.py` adds UTC with a local `_utc` helper, but `api/sources.py` returns `last_check_at`/`checked_at` as naive timestamps read back from SQLite. Browsers parse those as local time, so "last check" would display shifted by the UTC offset. Fix it once at the model layer (a timezone-aware `DateTime` type that always returns UTC) and drop the per-endpoint helper.
  2. [defense in depth, low] Feed entry links are rendered as `href`. React 19 blocks `javascript:` URLs, but parsing should keep only `http`/`https` links and fall back to the feed URL otherwise.

## Task group 7, integration and test report (2026-10-03)

- Both group 6 carry-overs addressed: all model timestamps use `UTCDateTime` (same SQLite schema, UTC on storage and retrieval), the digest endpoint's `_utc` helper is gone, and run detail now includes `started_at`/`finished_at`. The cross-endpoint regression test covers source list, run detail, digest list and detail, and normalization of a non-UTC input offset. Feed parsing falls back to the feed URL for non-HTTP(S) entry links; a parameterized regression test covers `javascript:`, `data:`, and `file:`.
- API integration test configures a fake provider, previews and confirms the RSS fixture, synchronously executes three runs (success, `no_new_content`, success after one feed entry is added), checks the third digest contains only that entry, and checks links/source names against fixture data rather than model output. It uses respx, patched DNS, temporary SQLite, and a fake model client; no fixed sleeps.
- Verification: focused carry-over tests 36 passed; integration test 1 passed after fixing a test dependency override (first attempt failed); full `uv run pytest` 147 passed; `uv run pytest --cov=catchup --cov-report=term` 147 passed, 95% overall (module details in `docs/process/test-report-add-core-digest-flow.md`). Initial frontend invocation lacked Vitest in this worktree; `npm ci` installed locked dependencies, then `npm test -- --run` passed 19 tests, `npm run build` passed, and `openspec validate add-core-digest-flow --strict` passed. All 48 scenarios in the five spec deltas have rows in the report; none are unmapped. No real feed or key was used; manual verification remains for reviewer and user.

### Claude Code review of group 7 (2026-10-03)

- Re-ran in a fresh worktree: 147 backend tests (95% coverage), 19 frontend tests, build, `npm audit` (0), strict validation; OpenSpec apply state `all_done` (24/24).
- Test report cross-checked with a script:
  - All 48 spec scenarios are named in the mapping table.
  - All 57 cited `file::test` references exist in `backend/tests/`.
  - All cited frontend test files exist.
- End-to-end test reviewed. Besides the flow in tasks.md, it asserts:
  - the key never appears in responses
  - stored citations (title, link, source) match the fixture
  - an earlier digest is unchanged after a later run
  - exactly 5 model calls (3 summaries + 2 groupings), so nothing is re-summarized
  - exactly 5 feed fetches
- Both group 6 carry-overs are fixed: a model-layer `UTCDateTime` replaces the per-endpoint helper, and non-http(s) entry links fall back to the feed URL.
- Verdict: **no required fixes.** Remaining before merge: manual verification with a real feed and a real DeepSeek key.

## Task group 8, manual-verification fixes (2026-10-03)

- 8.1: Output budgets are 4096 for summaries and `min(32768, 8192 + 24 × count)` for grouping and merge. Fake-client tests assert the requested budgets at all three stages and the cap. This leaves room for DeepSeek's default thinking mode before the JSON answer.
- 8.2: Untitled feed entries derive a plain-text title at a word boundary up to 80 text characters (or exactly 80 CJK characters with no spaces), adding an ellipsis if shortened. A Bluesky-style HTML-description fixture, long CJK post, empty post, and titled hash fallback are covered. Entries with ids or links retain their key selection.
- 8.3: A declared feed on `/@user` no longer triggers the whole-site notice. Existing article (`og:type=article`) and deeper-page origin-probe notice tests still pass.
- 8.4: The summary system prompt now asks for 2–4 sentences on substance, excludes platform identifiers/handles/submission metadata/timestamps unless essential, and gives one short sentence for content-free items. A prompt test asserts those rules and the existing language, JSON keyword, and example.
- Verification: `uv run pytest -q tests/test_digest_stages.py` (12 passed); `uv run pytest -q tests/test_discovery.py tests/test_sources_api.py` (33 passed); `uv run pytest` (153 passed); `npm test -- --run` (19 passed); `npm run build` (passed); `openspec validate add-core-digest-flow --strict` (valid). The scenario audit matched 52/52 headings to report rows and resolved all 85 backend test references. All tests used fake/mocked model and network interactions, with pytest temp data directories and no fixed sleeps.
- During test authoring, the first Bluesky truncation assertion expected a shorter title than the specified 80-character limit; corrected the expected title, then the focused suite passed. The first mapping audit counted header/separator rows; restricted it to spec names and it passed. No live feed or DeepSeek re-test was done; reviewer and user own that verification. The 2026-10-03 manual-verification record in the test report was not edited.
