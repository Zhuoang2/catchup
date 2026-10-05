# Tasks

Implementer notes:
- Read `proposal.md`, `design.md` (D2–D11), and every file under `specs/` first. Follow them; if something looks wrong or contradictory, stop and report rather than redesigning.
- Treat these rules as verification criteria, not notes:
  - Tests make no real network calls: respx for httpx; DNS is blocked by the autouse fixture in `backend/tests/conftest.py`; a fake `requests` transport adapter and a fake `YouTubeTranscriptApi` for captions.
  - Tests use no real API key and **no real sleeps**. Inject clocks and the `HostSpacer` sleep.
  - Tests write nothing outside pytest temp dirs.
  - Fixture feeds and transcripts are small hand-written files under `backend/tests/fixtures/`, modeled on the shapes in `research.md`. Do not download real feeds.
  - When a model interface changes (`list_models`, usage totals), update the existing fakes instead of weakening assertions:
    - `FakeModel` in `tests/test_digest_runner.py:23` and `tests/test_digest_stages.py:11`
    - `FixtureModel` in `tests/test_core_flow.py:20`
    - `FakeProvider` in `tests/test_settings_api.py:23`
  - Transcript and caption code never logs fetched content, only exception types and item ids.
- Backend commands run from `backend/` with uv; frontend commands run from `frontend/` with npm.
- Commit after each task group. Do not edit `proposal.md`, `design.md`, or `specs/`. Never push, tag, or open a PR.
- Each group must leave `uv run pytest`, `npm test -- --run`, and `npm run build` green.

## 1. Schema, dependencies, and configuration

- [x] 1.1 Add Alembic migration `0002` and the model fields per design.md D11 in `backend/src/catchup/models.py`:
  - `sources.kind`
  - `items.transcript_status`
  - `app_settings.youtube_captions`/`youtube_skip_shorts`
  - `model_config.context_window`
  - `digest_runs.prompt_tokens`/`completion_tokens`/`waiting_count`/`deferred_count`
  - `digests.transcript_wait_days`
  - `digest_topics.kind`
  - `digest_items.update_reason`

  Use server defaults and `batch_alter_table`. Verify with a test in `backend/tests/test_db.py`:
  - a database at `0001` with one source, item, topic, and digest item upgrades
  - existing rows read back as `kind='feed'`, `transcript_status` NULL, topic `kind='topic'`, `youtube_captions` false, `youtube_skip_shorts` true
  - downgrade to `0001` succeeds
- [x] 1.2 Add `youtube-transcript-api>=1.2.4,<1.3` and `lxml>=5,<7` to `backend/pyproject.toml` and update `backend/uv.lock`. Verify: `uv sync --locked` succeeds, and `uv run python -c "import youtube_transcript_api, lxml"` works.
- [x] 1.3 Update `backend/src/catchup/config.py` per design.md D9 and D3:
  - add `CATCHUP_MAX_FEED_BYTES` (default 33554432)
  - add `CATCHUP_TRANSCRIPT_WAIT_DAYS` (7), `CATCHUP_CAPTION_WAIT_HOURS` (24), `CATCHUP_CAPTIONS_PER_RUN` (20), `CATCHUP_LONG_ITEM_CHARS` (20000)
  - add the optional `CATCHUP_SINGLE_CALL_CHARS`
  - all must be positive integers, otherwise startup fails with a clear error
  - remove `max_item_chars`; a set `CATCHUP_MAX_ITEM_CHARS` logs one warning naming `CATCHUP_SINGLE_CALL_CHARS`

  Update `.env.example` (drop `CATCHUP_MAX_ITEM_CHARS`, add the new variables commented out). Verify: config tests for defaults, invalid values, and the warning (caplog).

## 2. Podcast and YouTube sources: kind, larger feeds, Apple Podcasts

- [x] 2.1 Add `max_bytes` to `safe_fetch` (`backend/src/catchup/net/safe_fetch.py`) per design.md D3. The default stays 5 MB, and the size error message names the limit. Pass `settings.max_feed_bytes` at all three feed call sites: `discover()` (`sources/discovery.py`), the cache-miss fetch in `confirm()` (`api/sources.py:90`), and `check_source()` (`collection.py`). Make `FeedCache` (`net/feed_cache.py`) skip storing responses over 5 MB. Verify with respx tests:
  - a 6 MB feed body passes preview with the feed limit, by both Content-Length and streaming
  - confirming a 6 MB feed with no cached preview succeeds (spec "Confirm a large feed after the preview expired")
  - a 6 MB response is not stored in the cache
  - a 6 MB article fetch through `article_text()` still fails
- [x] 2.2 Classify sources per design.md D2. The changes:
  - `parse_feed` exposes the YouTube-host fact, the audio-enclosure share, and a per-entry `has_audio`
  - the majority rule alone decides `podcast` (no iTunes check), and accepted hosts are `youtube.com`, `www.youtube.com`, and `m.youtube.com`
  - non-audio entries of podcast sources get `transcript_status='text'` and keep `article_text()`
  - confirm (`api/sources.py`) saves `kind`, and `check_source` upgrades it but never downgrades
  - the preview API returns `kind` and `captions_enabled` (read from the `app_settings` column)
  - `frontend/src/pages/Sources.tsx` shows the kind and the transcript text from design.md D2, including the "whole show" wording for podcast whole-site notices

  Verify:
  - tests for a podcast fixture (majority audio), a YouTube fixture, a plain RSS fixture, a blog fixture with 1 audio post among 15 (stays `feed`), and a Substack-style fixture with `itunes:author`/`itunes:owner`/`itunes:block` and no enclosures (stays `feed`)
  - a test that a non-audio entry in a podcast source is `text` and summarized
  - a test that a `feed` source whose feed now looks like YouTube is upgraded on check, and that a podcast source whose feed no longer has enclosures stays `podcast`
  - a vitest test for the preview text with captions on and off
- [x] 2.3 Resolve Apple Podcasts URLs in `discover()` per design.md D4. Verify with respx tests:
  - a show URL → lookup → feed preview
  - an episode URL with `?i=` → whole-show notice
  - `resultCount` 0, missing `feedUrl`, and invalid JSON → `no_feed`
  - the lookup request goes through `safe_fetch` (the User-Agent is asserted)

## 3. Podcast transcripts

- [x] 3.1 Extract transcript candidates in `sources/feeds.py` per design.md D5:
  - a hardened lxml parser with `recover=True`
  - BOM and whitespace stripped first
  - matching by guid, else link
  - feedparser's `podcast_transcript` as the fallback whenever lxml produced nothing for an entry, including after a parse error

  Add fixtures:
  - `podcast-multi.xml`: one item with html, json, x-subrip, and vtt tags
  - `podcast-oddns.xml`: the non-canonical namespace URI, `application/srt`
  - `podcast-none.xml`: no tags
  - `podcast-entity.xml`: `&nbsp;` in an item title, plus a vtt tag

  Verify:
  - all 4 candidates are kept, with the preference order applied
  - the odd namespace is recognized
  - `podcast-entity.xml` still yields its vtt candidate (spec "Feed with an undefined HTML entity")
  - an internal entity declaration is not expanded
  - garbage bytes yield no candidates without failing `parse_feed`
  - when lxml fails entirely but feedparser exposes `podcast_transcript`, that candidate is used
- [x] 3.2 Add `backend/src/catchup/transcripts/convert.py` per design.md D5: VTT, SRT, JSON (including string `startTime` and word-level segments), HTML, and plain text. A listed declared type decides the format; otherwise the body is sniffed after BOM stripping. Verify with unit tests per format:
  - speaker labels kept
  - timing lines removed
  - same-speaker cues merged
  - an SRT body with a BOM and no declared type is sniffed correctly
  - empty input → None
- [x] 3.3 Resolve podcast transcripts in `check_source` per design.md D6. The changes:
  - a `TranscriptContext` is created in `digest/runner.py` beside the `HostSpacer`
  - confirm stores `to_fetch` for podcast and YouTube items and skips `article_text()`
  - `check_source` handles new, `to_fetch`, `waiting`, and NULL-status podcast items matched in this fetch
  - transcripts are fetched with the spacer and the 5 MB limit, with fallback to the next candidate (at most 2 fetches)
  - a found transcript sets `content_origin='transcript'` and clears `summary`/`summary_language`
  - per-item work runs inside a catch-all (design.md D5, "Error containment")

  Verify with respx tests:
  - a new episode with a VTT transcript → `found` with converted text
  - a 404 on the best candidate falls back to the second
  - an episode without tags → `waiting`
  - a later check whose feed now lists a transcript → `found`, with an old summary cleared
  - a converter raising an unexpected exception → `waiting`, and the check still succeeds
  - confirm makes no episode-page or transcript request
  - spacer calls are recorded

## 4. Creator updates and once-only delivery

- [x] 4.1 Implement selection in `digest/runner.py` per design.md D7. Selection is decided by `transcript_status`. Expiry is computed in memory from `discovered_at` with an injected clock: the transcript wait for podcast `to_fetch`/`waiting`/NULL items, and the caption wait for YouTube `caption_wait`/`unplayable_wait` items. The changes:
  - expiry statuses (`no_transcript`, `no_captions`, `captions_failed`) are written only in the save transaction
  - `waiting_count`/`deferred_count` are written
  - no model call is made for Creator updates items
  - a digest with only Creator updates is saved when nothing else is includable, replacing the early return at `runner.py:161-165` for that case
  - `no_new_content` when nothing is includable at all

  Verify with tests covering these spec scenarios:
  - "Episode waiting for a transcript", "Item never repeated", "Only waiting episodes", "Only Creator updates", and "Run fails after a wait ends" (`specs/digest-generation/spec.md`)
  - "Wait ends", "Feed keeps failing", and "Caption wait ends" (`specs/transcripts/spec.md`)
  - a fake client asserting zero calls for Creator updates items
- [x] 4.2 Store and serve Creator updates per design.md D7. The changes:
  - the `creator_updates` topic with `update_reason` items, and `digests.transcript_wait_days`
  - `GET /api/digests/{id}` returns `topics` (kind `topic` only), `creator_updates` grouped by source, and `transcript_wait_days`
  - `GET /api/digest-runs/{id}` (`api/runs.py`) returns `waiting_count`/`deferred_count`

  Verify:
  - API tests for grouping and order
  - an old-style digest without the topic still returns `creator_updates: []`
  - a failed save leaves the items pending
  - a digest reopened after the configured wait changes still reports its saved `transcript_wait_days` (spec `digest-history` "Open a digest with Creator updates")
- [x] 4.3 Render Creator updates in `frontend/src/pages/DigestView.tsx` with the labels from design.md D7 (N from the digest), and show the waiting and deferred counts in `frontend/src/pages/Generate.tsx` with the exact texts from design.md D7 "Run counters", including the no-new-content message. Verify with vitest tests: the section appears after the topics, has a heading per source, and shows each label; the counts appear in both a succeeded run and a no-new-content run.

## 5. YouTube captions

- [x] 5.1 Add the YouTube preferences to `api/settings.py` (`GET/PUT /api/settings/preferences`, all PUT fields optional, missing = unchanged) and two toggles with the design.md D8 description on `frontend/src/pages/Settings.tsx`. Verify:
  - API tests for defaults (captions off, skip Shorts on), for partial updates, and that a PUT with only `digest_language` keeps both toggles
  - vitest tests for the toggles and the Terms of Service text
- [x] 5.2 Skip Shorts per design.md D8: new Shorts as `baseline` at confirm and in checks, and pending NULL/`to_fetch` Shorts set to `baseline` at the start of the caption pass. Verify: tests show a `/shorts/<id>` entry is `baseline`, no caption call is made, it is never in a digest, and a pre-existing pending Short is skipped; with skipping off, it is handled like a normal video.
- [x] 5.3 Add `backend/src/catchup/transcripts/youtube.py` per design.md D8:
  - the spaced `requests.Session` subclass (`trust_env=False`, spacer, User-Agent, timeout)
  - the API factory
  - track choice (original language, manual > auto, best effort without an auto track, no `translate()`)
  - exception mapping to `caption_wait`/`unplayable_wait`/`blocked`/`captions_failed`, with a catch-all

  Verify:
  - a fake transport adapter test proving `spacer.wait` runs before each request, the User-Agent and timeout are set, and `trust_env` is False
  - fake-transcript-list tests for both "Use captions in the video's original language" scenarios, the no-auto-track fallback, and `translate()` never called
  - a test per exception class, including `TranscriptsDisabled` → `caption_wait`, `VideoUnplayable` → `unplayable_wait`, `IpBlocked` → `blocked`, and a plain `KeyError` → `captions_failed`
- [x] 5.4 Add the caption pass to `digest/runner.py` per design.md D8. It runs after all source checks, over pending YouTube `to_fetch`/NULL items and unexpired `caption_wait`/`unplayable_wait` items, ordered by `discovered_at`, `id`, with the video id taken from `identity_key`:
  - setting off → `captions_off` with no library call
  - the per-run cap with deferral
  - stopping after the first `blocked`
  - per-item commits
  - a found caption sets `content_origin='transcript'` and clears the old summary

  Verify with tests covering the "Limit and space caption requests" scenarios: 25 videos with the same `discovered_at` → the 20 lowest ids fetched and 5 deferred; a block on the 3rd of 10 → 7 untouched; a deferred video missing from the next feed is still fetched. Also cover:
  - "Default settings", "Unexpected response format", and "Captions generated after upload" (a retry within the wait succeeds)
  - turning the setting off ends a running wait with `captions_off`
  - a pending `captions_off` item is fetched once the setting is on
  - with a cap of 1, one `caption_wait` item and one NULL item: the wait item is retried; the NULL item becomes `to_fetch` and is counted as deferred
  - a wait item skipped after a block keeps its wait status and counts as waiting
  - a pre-existing `feed` YouTube source upgraded with its pending videos following the caption rules
- [x] 5.5 Rewrite README "Supported sources" per design.md Rollout:
  - podcasts with published transcripts and the wait variable
  - the caption wait variable
  - Apple Podcasts URLs
  - YouTube with opt-in captions and the ToS statement
  - Shorts skipped by default
  - Creator updates
  - the feed size variable
  - setting `CATCHUP_SINGLE_CALL_CHARS` for small local models

  Verify: every variable named in the README exists in `config.py`, and the README no longer says podcasts/YouTube are unsupported.

## 6. Long texts and token usage

- [x] 6.1 Learn the context window per design.md D9:
  - `ModelClient.list_models()` returns `ModelInfo` with strict int parsing from `model_extra`, and callers (`api/settings.py:123`) are updated with an unchanged response shape
  - `PUT /model` clears `context_window` when the base URL or model changes
  - the runner fills it once at run start when NULL, matching the configured model id and catching any exception

  Verify:
  - tests with a respx-mocked `/models` that has `context_window`, has none, has `"12"`, or has `true`
  - the matching entry is chosen among several models
  - the cached value is reused (request count)
  - a model change clears it
  - a `/models` failure or a fake without `list_models` at run start does not fail the run
- [x] 6.2 Implement the single-call budget, parts, and combine in `digest/summarize.py` and prompts in `llm/prompts.py` per design.md D9 (budget formula, split order, part and combine prompts, the long-transcript prompt with key points). Render "- " lines as a list in `DigestView.tsx`. Verify with fake-client tests covering the three "Summarize long texts in full" scenarios, with fixtures made of 1,000-character paragraphs: 1 call at 169,961 characters with a 1M window; 3 parts + 1 combine with an unknown window; 3 + 1 with `CATCHUP_SINGLE_CALL_CHARS=20000` on 50,000 characters. Also check:
  - no text is dropped (the concatenated part inputs equal the original after whitespace normalization)
  - the long-transcript prompt is used only for transcripts over `CATCHUP_LONG_ITEM_CHARS`
  - a part failure → `summary_unavailable`
  - a vitest test for list rendering
- [x] 6.3 Record token usage per design.md D10:
  - thread-safe accumulation in `llm/client.py`
  - totals written at every run end in `digest/runner.py`, tolerating clients without usage
  - exposed in `GET /api/digest-runs/{id}` and `GET /api/digests/{id}`
  - shown in `Generate.tsx` and `DigestView.tsx` ("Tokens: N in / M out" or "Tokens: not reported")

  Verify:
  - client tests with usage present and absent, and concurrent calls summing correctly
  - a runner test for succeeded, no-new-content, and failed runs
  - vitest tests for both display variants

## 7. Integration checks

- [ ] 7.1 Run the full checks and record the results in the final report:
  - `uv run pytest` (with the coverage summary used in earlier changes)
  - `npm test -- --run`
  - `npm run build`
  - `openspec validate add-podcast-and-video-sources --strict`
  - `docker build` plus `scripts/docker-smoke.sh` if Docker is running; otherwise say so explicitly

  Verify: all pass. Report any skipped check with its reason.
