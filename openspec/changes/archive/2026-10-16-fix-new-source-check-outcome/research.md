# Research: a new source's first run reports "No new items" while its seeded items are in the digest (#31)

- Date: 2026-10-16
- Query: Why does a source's check in a run say "No new items" while the digest saved by that run contains items from it? The research covers:
  - how adding a source seeds items
  - how a run checks sources and picks the items it digests
  - how outcomes are stored, returned, and shown
  - what the specs and tests say
- Git ref: `main` @ 40d913b

## Summary

**Adding a source.** Confirming a source fetches its feed and records every current entry:
- Entries from the last 7 days, up to the 5 newest, are stored as `pending`; the rest are `baseline`.
- A confirm-time check is written with `run_id = NULL`, status `new_items` when anything was seeded, and `new_count` equal to the number seeded.

**A digest run.**
- Each source is checked again. Its outcome is `new_items` only when the check itself records a feed entry that was not stored before. Entries seeded at confirm time are already stored, so the source's first run reports `no_new_items` for them.
- The run then digests every `pending` item from every source, including the seeded ones.
- A run's outcome therefore describes what that check discovered, not what the run delivers. The run JSON and the UI expose only the status, not `new_count`.

**Tests encode the current behavior.** An existing end-to-end test asserts this exact combination: a first run with `items_total == 2` and `source_checks[0].status == "no_new_items"`.

## Detailed Findings

### Adding a source (confirm)
- **Preview.** It returns up to 5 recent entries and changes nothing — `backend/src/catchup/api/sources.py:60-86`.
- **Confirm** (`POST /api/sources`) re-reads the feed from the preview cache or fetches it — `sources.py:89-100`.
- **Seeding** — `sources.py:105-114`, `:124-128`:
  - `lookback = now - first_add_days`.
  - Entries dated within `[lookback, now]` are taken newest first, up to `first_add_max`, and stored with state `pending`.
  - Every other entry is stored as `baseline`, including undated ones.
  - A YouTube Short becomes `baseline` when Shorts are skipped.
- **Defaults:** `CATCHUP_FIRST_ADD_DAYS` "7" and `CATCHUP_FIRST_ADD_MAX` "5" — `backend/src/catchup/config.py:34-35`, `:55-56`.
- **Text of seeded items.** Seeded items get article text when they are short feed items. Podcast and YouTube items get `transcript_status` `to_fetch`, or `text` for a podcast without audio — `sources.py:129-142`.
- **The confirm-time check:**
  - `source.last_check_status` becomes `new_items` if anything was seeded, else `no_new_items` — `sources.py:143`.
  - A `SourceCheck` is written with `run_id=None`, `status` as above, `new_count=pending_count`, and `entries_seen=len(feed.entries)` — `sources.py:144-148`.
  - The confirm response returns `last_check_status` — `sources.py:157-161`.

### Checking a source in a run
- `check_source` — `backend/src/catchup/collection.py:57-142`.
  - A fetch or parse failure records `failed` with the error and HTTP status — `collection.py:61-75`.
  - The stored items' identity keys and links are loaded — `collection.py:80-84`.
  - An entry is skipped when its key, or its non-fallback link, is already stored. This includes items seeded at confirm and items still `pending` — `collection.py:105-106`.
  - Each entry not seen before is stored and adds 1 to `new_count` — `collection.py:107-130`.
    - The entry is stored as `pending`, or as `baseline` for a skipped YouTube Short (`:114-116`).
    - A Short stored as `baseline` still adds 1 to `new_count`.
  - Status: `new_items` if `new_count` else `no_new_items`. `possible_gap = bool(existing_items) and not matched_previous` — `collection.py:132-137`.
- **Podcasts.** For an episode already stored and still pending, the check retries its transcript or article text in place, without counting it as new — `collection.py:94-104`.
- **The run's collect stage** checks every saved source once, with `run_id` set — `backend/src/catchup/digest/runner.py:197-209`.

### What a run digests
- After collecting, the run loads every item with `state == "pending"` from all sources, in id order — `runner.py:211-215`.
- `select_pending` (`runner.py:35-58`) sorts them:
  - **Summarized:** `found`/`text` transcripts, and feed items with no transcript status.
  - **Creator updates:** items with a terminal caption or transcript reason (`CREATOR_REASONS`, `:32`), and expired waits.
  - **Counted as waiting:** podcasts still waiting for a transcript, and caption waits.
  - **Counted as deferred:** YouTube items not yet fetched.
- The run therefore includes items that no check of this run discovered:
  - items seeded at confirm
  - items left `pending` by a failed or interrupted earlier run
  - podcast episodes whose transcript arrived in this run
  - caption results from `caption_pass` (`runner.py:209`)
- When nothing is ready and there are no Creator updates, the run ends `no_new_content` — `runner.py:233-240`.

### Stored outcome and API shapes
- **The `SourceCheck` model:** `run_id` (nullable), `source_id`, `status`, `possible_gap`, `error`, `http_status`, `entries_seen`, `new_count`, `checked_at` — `backend/src/catchup/models.py:95-107`.
- **`run_detail`** (`runner.py:372-398`; `api/runs.py` only calls it):
  - Its `source_checks[]` holds `source_id, source_title, status, possible_gap, error, http_status, rate_limited`, filtered by `run_id`.
  - `new_count` and `entries_seen` are not returned.
  - `sources_total` counts all saved sources — `runner.py:391`.
- **`GET /api/sources`** (`sources.py:164-181`):
  - Each source's status comes from its latest `SourceCheck` by `checked_at`, which right after confirming is the confirm-time check.
  - It returns `last_check_at, last_check_status, possible_gap, http_status, rate_limited`, with no pending count.

### How the UI shows outcomes
- **Home** (`frontend/src/pages/Home.tsx`):
  - The `Check` type has no `new_count` — `:11-14`.
  - `SourceChecks` (`:33-49`):
    - The label is "Sources", a `<p>` in the run bar or an `<h2>` in cards.
    - Chips: "Rate limited · try later" (warn), "Failed" (error), "New items" (ok), "No new items" (neutral), plus a "Possible gap" warn chip.
  - It is shown during a run, after success, after no new content, and after failure: `:71`, `:92`, `:105`, the run bar at `:250`, and the cards at `:287-288`.
  - The succeeded result line reads "Your digest is ready · {saved items} · {N} sources · {tokens}", with `sources_total` counting all saved sources — `:80-84`.
- **Sources page** (`frontend/src/pages/Sources.tsx`):
  - `SourceStatus` uses the same labels, plus "Never checked" and the check time — `:72-84`.
  - Confirming shows "Source saved." and refreshes the list. The new row then shows the confirm-time "New items" when entries were seeded — `:140-152`, `:179`.
  - The rail says "Sources are checked when you generate a digest." — `:222-223`.
- **No screen shows how many items a source contributed** to a run, or how many are pending.

### Reproduced
- **On 2026-10-16, on a local review instance** (the #27 review, stub model):
  - The public feed Python Insider was added as source 3. The next run saved digest No. 3 with one item, "Python 3.16.0 alpha 1 is now available", from Python Insider.
  - That run's checks read "Ruby News · No new items", "Rust Blog · No new items", and "Python Insider · No new items".
  - This matches `collection.py:105-106` and `:133`: the seeded entry was already stored, so the check counted 0.
- **The same combination in an existing test:** `backend/tests/test_core_flow.py:77-84` asserts:
  - the confirm response says `last_check_status == "new_items"`
  - the first run has `items_total == 2` and `items_done == 2`
  - `source_checks[0]["status"] == "no_new_items"`

## Code References
- `backend/src/catchup/api/sources.py:89-161` — confirm, seeding, the confirm-time check.
- `backend/src/catchup/api/sources.py:164-181` — source list status from the latest check.
- `backend/src/catchup/collection.py:57-142` — run-time check, `new_count`, status, possible gap.
- `backend/src/catchup/digest/runner.py:35-58` — `select_pending` classification.
- `backend/src/catchup/digest/runner.py:197-240` — collect stage, pending selection, no-new-content.
- `backend/src/catchup/digest/runner.py:372-398` — run JSON, including `source_checks`.
- `backend/src/catchup/models.py:95-107` — the `SourceCheck` columns.
- `backend/src/catchup/config.py:34-35`, `:55-56` — the first-add limits.
- `frontend/src/pages/Home.tsx:11-14`, `:33-49` — the check type and chips.
- `frontend/src/pages/Sources.tsx:72-84`, `:140-152`, `:222-223` — source status, confirm message, rail text.

## Current Specs
- **`content-collection`, "Check every source on each run"** (`openspec/specs/content-collection/spec.md:8-17`):
  - Each run records one outcome per source: `new_items` "(at least one new entry recorded)", `no_new_items` "(fetched and parsed successfully, nothing new)", or `failed`.
  - Scenario "Nothing new": a feed with only recorded entries is `no_new_items`.
- **`content-collection`, other requirements:**
  - Possible gap — `spec.md:46-50`.
  - Rate limiting is shown "in the source list and in run progress" — `spec.md:71-75`.
- **`source-management`, "Confirm and save a source"** (`openspec/specs/source-management/spec.md:67-77`):
  - On saving, the system records current entries. Those from the last 7 days, up to the 5 newest, "MUST be marked as new for the next digest"; all others are existing.
  - Both limits are configurable.
  - Scenario: the 2 recent entries "will appear in the next digest".
- **`source-management`, the source list:** it shows "the outcome and time of their most recent check" — `spec.md:80`.
- **`digest-generation`, "Show run progress and per-source outcomes"** (`openspec/specs/digest-generation/spec.md:19-24`):
  - The run reports "each source's check outcome as it becomes known".
  - With no new content, it shows each source's check outcome — `spec.md:46-50`.
- **`user-interface`:**
  - The run bar shows "each source's check outcome" during and after a run — `openspec/specs/user-interface/spec.md:169-170`.
  - A source shows "its last check outcome and time" — `spec.md:115`.
- **`transcripts`:** a skipped Short is "recorded as already seen" — `openspec/specs/transcripts/spec.md:181`.

## Tests
- **`backend/tests/test_core_flow.py::test_incremental_api_flow_with_stored_citations`:**
  - The confirm response is `new_items` (`:79`).
  - The first run has 2 items and a check of `no_new_items` (`:83-84`).
  - The second run is `no_new_items` (`:95`), and the third is `new_items` (`:108`).
- **`backend/tests/test_sources_api.py`:**
  - `test_confirm_marks_first_add_baseline` (`:315-332`) checks `new_items`, the pending and baseline counts, `run_id is None`, and `new_count == pending`.
  - `test_configurable_first_add_limits` (`:335-343`).
  - The list status and rate-limit tests (`:477-505`, `:517-534`).
- **`backend/tests/test_collection.py`:**
  - Status and `new_count` assertions — `:95-101`, `:118-120`, `:132-134`, `:144-150`, `:207`, `:227-230`, `:245-249`.
  - The possible-gap test — `:185-196`.
- **`backend/tests/test_digest_runner.py`:**
  - `stub_collection` always writes `no_new_items` — `:78-87`.
  - `source_checks` lengths — `:107`, `:316-317`, `:441`, `:450`.
  - The rate-limit tests — `:494-533`.
- **`backend/tests/test_youtube_shorts.py::test_confirm_short_default_and_opted_in`** checks a baseline vs pending Short at confirm — `:37-49`.
- **Frontend:**
  - `Home.test.tsx` checks the "Failed" and "Possible gap" chip tones (`:635-651`) and the rate-limit label (`:671-683`). No test asserts "New items" or "No new items".
  - `Sources.test.tsx` checks the "Possible gap" and rate-limit labels (`:126-136`). No test asserts "Source saved." or the new/no-new labels.

## Related History
- **`openspec/changes/archive/2026-10-03-add-core-digest-flow/design.md`:**
  - "first add keeps entries from the last 7 days, at most 5 per source" — `:3`.
  - Item states `pending`/`delivered`/`baseline` — `:40`.
  - `source_checks.run_id` is "nullable; null for the confirm-time check" — `:157`.
- **`openspec/changes/archive/2026-10-04-improve-source-reliability/design.md:24`, `:34-37`:** a fourth `rate_limited` outcome was rejected; rate limiting is a flag on `failed`.
- **`docs/handoff.md:68`** lists as open: "How far back the first generation looks; how history is backfilled when a new source is first added."
- **The decision log and the requirements-change log** have no entry on first-add seeding or on the meaning of check outcomes.
- **Issue #31,** filed 2026-10-16 during the #27 review.
