# Design

Status: Proposal 1 chosen by the user on 2026-10-05, with five amendments:
1. a Creator updates section
2. one appearance per item, with a transcript wait for podcasts
3. a single-call budget derived from the model's context window
4. request control for the captions library
5. original-language captions

The user confirmed the amended design the same day and accepted these defaults:
- no description excerpt in Creator updates
- `CATCHUP_CAPTIONS_PER_RUN` = 20
- the wait is configurable as `CATCHUP_TRANSCRIPT_WAIT_DAYS` (default 7)
- the `captions_failed` reason
- stopping caption requests after the first block
- resolving transcripts in the run's check phase
- the `CATCHUP_SINGLE_CALL_CHARS` override
- after the plan review: a caption wait for YouTube videos without captions yet (`CATCHUP_CAPTION_WAIT_HOURS`, default 24)

The two-proposal comparison is in git history (`be46efb`). The rejected alternative is recorded under D1.

## Context

See `proposal.md` for motivation and `research.md` for the current code and external facts. The parts that shape this design:
- **Collection.** Every source is a generic feed. `parse_feed` (`sources/feeds.py:63-87`) reads only id, link, title, dates, and content. `article_text()` (`collection.py:14-29`) fetches the linked page when the feed text is under 500 characters, both at confirm (`api/sources.py:116-125`) and during checks (`collection.py:68`).
- **Fetch limit.** `safe_fetch` caps every response at 5 MB (`net/safe_fetch.py:18,163,175`). The Vergecast's 6.2 MB feed fails today.
- **Summarization.** It is one call per item on `content_text[:CATCHUP_MAX_ITEM_CHARS]` (20,000), with 4 workers (`digest/summarize.py:27-41,57`). The prompt always asks for 2–4 sentences (`llm/prompts.py:24-36`).
- **Delivery.** Pending items become `delivered` when the digest is saved (`digest/runner.py:185`). Every saved item belongs to a `DigestTopic` (`models.py:130-153`).
- **Run spacing.** A run's checks are sequential and share one `HostSpacer` (`digest/runner.py:92-97`; `net/host_spacing.py`).
- **Third-party behavior** (research):
  - feedparser keeps only the last `<podcast:transcript>` of an item.
  - `youtube-transcript-api` makes 3 requests per video with its own `requests` client.
  - DeepSeek documents `context_window` on `GET /models` (not yet verified live).

## Goals / Non-Goals

**Goals:**
- Podcast and YouTube items are summarized only from transcripts, and long transcripts are summarized in full.
- Every item appears in exactly one digest: summarized in a topic, or listed under Creator updates with a reason.
- YouTube is contacted for captions only after the user opts in, and then politely: sequentially, spaced, capped, and stopping when blocked.
- Configuration stays backward compatible except for the documented removal of `CATCHUP_MAX_ITEM_CHARS`.

**Non-Goals:**
- Speech-to-text, YouTube audio download, and yt-dlp (Proposal 2, rejected).
- Per-channel or per-source transcript settings.
- Prices or currency estimates.
- Detecting context-overflow errors and retrying with smaller parts.
- Summarizing or showing show notes or descriptions in any form, including excerpts.
- Changing topic grouping (`digest/group.py`), which already works on summaries.

## Decisions

### D1. Transcripts resolved in the run's check phase and stored in `content_text` (Proposal 1)
- A transcript is just better `content_text`, with `content_origin = "transcript"` (String(16), `models.py:84`). Summary caching, history, and grouping stay unchanged.
- **Alternative considered (Proposal 2):**
  - What it was:
    - a provider chain at digest time with a separate `transcripts` table
    - per-source options
    - always chunking
    - speech-to-text of podcast audio through a user-supplied transcription key, with ffmpeg in the image
  - Why it was rejected:
    - It is much larger: a second credential, a binary dependency, audio downloads of hundreds of MB, and more tables.
    - Speech-to-text is not committed (`docs/handoff.md:55`).
    - It still excludes YouTube audio for ToS reasons.
  - It stays a possible follow-up built on `kind` and `transcript_status`.

### D2. Source kind
- `sources.kind` is `feed`, `podcast`, or `youtube` (default `feed`).
- `parse_feed` reports two facts, plus a per-entry `has_audio` flag:
  - whether the feed URL's host is `youtube.com`, `www.youtube.com`, or `m.youtube.com` and its path is `/feeds/videos.xml`
  - the share of entries with an audio enclosure (`enclosures[*].type` starting with `audio/`)
- Kind:
  - `youtube` if the first fact holds
  - else `podcast` if more than half of the entries have audio enclosures
  - else `feed`

  One audio post in a blog does not make it a podcast.
- **iTunes metadata is deliberately not used.**
  - Verified 2026-10-05: feedparser maps `itunes:author` to the generic `author`, so the presence of iTunes elements cannot be detected from its output.
  - Substack newsletters declare the iTunes namespace and emit `itunes:author`, `itunes:owner`, and `itunes:block` with zero audio enclosures (live: astralcodexten.com/feed, noahpinion.blog/feed).
- **Per-entry handling inside a podcast source.**
  - Entries with `has_audio` are episodes and follow the transcript rules.
  - Entries without audio get `transcript_status = 'text'` and are handled like website entries: `article_text()` at confirm and in checks, and summarized.
  - So even a wrongly classified source loses nothing; at worst its audio entries wait for transcripts.
- Confirm saves the kind. Every successful check recomputes it, but only upgrades: `feed` → `podcast`/`youtube`. A podcast or YouTube source is never downgraded, so a source cannot flip-flop as entries scroll out of the feed.
- For podcast and YouTube sources, a pending item with a NULL `transcript_status`, saved before this change, is handled as `to_fetch`. A pending NULL-status Short on a YouTube source is set to `baseline` when skipping is on (D8).
- The preview API returns `kind` and `captions_enabled` (read from `app_settings.youtube_captions`, which exists from task 1.1). `Sources.tsx` shows the kind and how transcripts are obtained:
  - podcast: "Transcripts published by the show"
  - YouTube with captions on: "Captions fetched from YouTube on this computer"
  - YouTube with captions off: "Caption fetching is off; videos will be listed without summaries"

### D3. Feed size limit
- `safe_fetch(..., max_bytes=None)` keeps 5 MB when unset.
- Feed fetches pass `settings.max_feed_bytes` (`CATCHUP_MAX_FEED_BYTES`, default 32 MiB). These are the three call sites:
  - the initial URL and declared or probed candidates in `discover()`
  - the cache-miss fetch in `confirm()` (`api/sources.py:90`)
  - `check_source()`
- The size error message names the actual limit.
- A first fetch of a pasted URL may be an HTML page, so it uses the feed limit too. HTML pages are rarely that large, and the 30 s deadline still applies.
- The preview cache (`net/feed_cache.py`, 50 entries) stores only responses up to 5 MB. Larger feeds are fetched again at confirm. This keeps the cache's worst case at about 250 MB instead of about 1.6 GB.

### D4. Apple Podcasts resolution
- `discover()` first matches `^https://podcasts\.apple\.com/[a-z]{2}/podcast/[^/]+/id(\d+)` (query ignored).
- It fetches `https://itunes.apple.com/lookup?id=<id>&entity=podcast` through `safe_fetch`. Apple serves `text/javascript`, so the body is parsed as JSON whatever the content type.
- It reads `results[0].feedUrl` and discovers that feed.
- With `?i=` present, `follows_site_feed_notice` is set (`discovery.py:31-34`). The frontend words the notice "the whole show" for podcasts.
- When `resultCount` is 0, `feedUrl` is missing, or the JSON is invalid, the result is `FetchError("no_feed", …)`, which keeps the existing "No supported feed was found" message.
- There is no client-side rate limiter: previews are user-paced, and Apple allows about 20 calls per minute.

### D5. Podcast transcript candidates and conversion
- **Candidate extraction.**
  - `parse_feed` additionally parses the raw bytes with `lxml.etree.XMLParser(recover=True, resolve_entities=False, no_network=True, load_dtd=False)`. A leading UTF-8 BOM and whitespace are stripped first.
  - Experiment (2026-10-05): without `recover`, an item title containing `&nbsp;` makes lxml reject the whole document, while feedparser tolerates it. With `recover=True`, the transcript tag is still found.
  - For each `<item>`, it collects children whose tag local name is `transcript` and whose namespace URI is either the canonical `https://podcastindex.org/namespace/1.0` or the URI the document binds to the `podcast` prefix.
  - Candidates (url, type, language, rel) attach to `FeedEntry` by matching the item's `guid`, else its `link`, to the feedparser entry.
  - Whenever lxml produced no candidates for an entry, including after a parse error that `recover` could not handle, feedparser's single `entry.podcast_transcript` is used as the candidate if present.
  - Parse errors never fail the check.
- **Choice.**
  - Preference: `text/plain` > `text/vtt` > `application/x-subrip` | `application/srt` > `application/json` > `text/html`.
  - At equal type rank, a candidate whose `language` matches the feed `<language>` wins.
  - A candidate with a missing or unlisted `type` ranks last; its format is decided by sniffing.
- **Fetching.** Through `safe_fetch` (5 MB) with the run spacer. Only the best candidate is fetched; if it fails, the next one is tried. At most 2 fetches are made per item per run.
- **Format detection.**
  - A listed declared `type` decides the format, not the server's content type, because servers send `application/octet-stream` or `text/plain` for SRT.
  - Otherwise the body (after stripping a BOM) is sniffed: `WEBVTT` header → VTT; `^\d+\r?\n\d\d:\d\d:\d\d,\d{3} -->` → SRT; a JSON object → JSON; else plain text.
- **Conversion** (new module `catchup/transcripts/convert.py`):
  - VTT: drop the header, cue ids, timings, and NOTE/STYLE blocks; `<v Name>` becomes "Name: ".
  - SRT: drop indices and timings; keep "Name:" prefixes.
  - JSON: concatenate `segments[*].body`, starting a new "Speaker: " paragraph when `speaker` changes. Word-level segments are joined with spaces.
  - HTML: run trafilatura; if that fails, fall back to `plain_text()`.
  - Plain text is stripped.
  - Consecutive cues from the same speaker merge into one paragraph.
  - An empty result counts as no transcript.
- **Error containment.** Fetching, decoding, and converting one item's transcript run inside a catch-all. Any exception means "no transcript on this run" for that item, with the same effect as no candidates. Only the exception type and item id are logged, never content. This matches how `article_text` already swallows extraction errors (`collection.py:26-28`).

### D6. Transcript status and transcript resolution
- **`items.transcript_status`** (String(16), NULL for `feed` sources) takes these values:
  - `found`
  - `text` (non-audio entry of a podcast source; handled like a website entry)
  - `to_fetch`
  - `waiting` (podcast, no transcript yet)
  - `caption_wait` (YouTube, no caption tracks yet)
  - `unplayable_wait` (YouTube, cannot be played yet)
  - `no_transcript`
  - `captions_off`
  - `no_captions`
  - `blocked`
  - `captions_failed`
- **Confirm** (`api/sources.py:116-125`): for podcast episodes and YouTube videos, pending first-add items are stored with `to_fetch` and the feed text, without `article_text()`. This keeps confirm fast. Non-audio entries of podcast sources get `text` and `article_text()` as today.
- **Run context.** A per-run `TranscriptContext` is created next to the `HostSpacer` (`runner.py:92`). It holds:
  - the spacer
  - the settings and preferences
  - `captions_remaining = CATCHUP_CAPTIONS_PER_RUN`
  - `captions_blocked = False`
- **Podcasts, in `check_source`.** After a successful fetch, a podcast source handles:
  - new entries (instead of `article_text()`)
  - its pending items with `to_fetch`, `waiting`, or NULL status that this fetch's entries match by identity key

  Outcome:
  - An entry without an audio enclosure (including a matched legacy NULL item) → `text`, with `article_text()` as for website entries.
  - Best candidate fetched and converted → `found`.
  - No candidates, or all fetches failed → `waiting`.
  - Items not matched in this fetch, and items of a source whose check failed, keep their status.

  Whether they expire is decided at selection (D7) from `discovered_at` alone, so a failing feed or a dropped entry cannot keep an episode pending forever.
- **YouTube, in a caption pass after all sources are checked** (D8). `check_source` stores new YouTube entries as `to_fetch`, or as `baseline` for Shorts, and makes no caption request. Captions are not tied to a feed match, because the video id comes from `identity_key` (`yt:video:<id>`).
- **Replacing content.** Whenever a transcript replaces `content_text`, `summary` and `summary_language` are cleared, so a summary made from the description in an earlier failed run is not reused (`summarize.py:53`).

### D7. Selection, Creator updates, and once-only delivery
- **Selection is decided by `transcript_status`.** The source kind is only used to start the status (D2, D6). At the start of summarizing, pending items split as follows:
  - **summarize:** items with NULL status on `feed` sources, and items with `found` or `text`
  - **creator updates:**
    - items with `captions_off`, `no_captions`, `blocked`, `captions_failed`, or `no_transcript`
    - expired podcast items: `to_fetch`, `waiting`, or NULL status, with `discovered_at` + `CATCHUP_TRANSCRIPT_WAIT_DAYS` ≤ now; the reason is `no_transcript`
    - expired YouTube wait items: `caption_wait` or `unplayable_wait`, with `discovered_at` + `CATCHUP_CAPTION_WAIT_HOURS` ≤ now; the reason is `no_captions` or `captions_failed`, respectively
  - **held:** they stay pending.
    - the remaining podcast `to_fetch`/`waiting`/NULL items, and YouTube `caption_wait`/`unplayable_wait` items within their wait (counted in `waiting_count`)
    - YouTube `to_fetch` items (counted in `deferred_count`)
- **Expiry is computed in memory.** The resulting status (`no_transcript`, or `no_captions`/`captions_failed` for expired YouTube waits) is written only in the save transaction, together with `delivered`. If the run fails first, the item keeps its earlier status and is selected again next time. Including `no_transcript` in the creator-update set also covers any row that already has it.
- **Run counters.** `digest_runs.waiting_count` (podcast episodes and YouTube videos in a wait) and `deferred_count` (YouTube `to_fetch` items held by the cap or a block) record the held items. The run view shows "N items waiting for transcripts or captions" and "M videos deferred to the next run". Each line is shown only when its count is non-zero.
- **Nothing to summarize and no creator-update items** → `no_new_content`, as today. The run view and API show the waiting and deferred counts (spec "No digest when nothing is new").
- **A run with only creator-update items** saves a digest that has only the Creator updates section. Grouping is skipped. This replaces today's early return when `saved_ids` is empty (`runner.py:161-165`) for that case.
- **Storage.**
  - `digest_topics.kind` is `topic` (default) or `creator_updates`.
  - One `creator_updates` topic per digest is saved after the normal topics: title "Creator updates", empty overview.
  - Its `DigestItem`s carry `update_reason` (the status value) and `summary = NULL`. Positions are ordered by source title, then publish time descending.
  - `digests.transcript_wait_days` stores the wait in effect at save time, so reopened digests show the same label (spec `digest-history`).
- **Delivery.** These items are set to `delivered` in the same transaction as everything else (`runner.py:145-188`). A failed save keeps them pending. `Digest.item_count` counts them.
- **API.** `GET /api/digests/{id}` returns `topics` (kind `topic` only), `creator_updates: [{source_name, items: [{title, link, published_at, reason}]}]` grouped by `source_name`, and `transcript_wait_days`.
- **Frontend.** `DigestView` renders Creator updates after the topics, with a heading per source. Each item shows its title (linked), publish time, and label:

  | `update_reason` | Label |
  |---|---|
  | `captions_off` | Caption fetching is off |
  | `no_captions` | This video has no captions |
  | `blocked` | Blocked by YouTube |
  | `captions_failed` | Captions could not be fetched |
  | `no_transcript` | No transcript within N days (N = the digest's `transcript_wait_days`) |

- **Old digests** have no `creator_updates` topic and render as before.

### D8. YouTube captions
- **Settings.**
  - `app_settings.youtube_captions` (default false) and `youtube_skip_shorts` (default true) are exposed through `GET/PUT /api/settings/preferences` (`api/settings.py:135-150`).
  - All `PUT` fields are optional, and a missing field means unchanged. This matters because the Settings page's existing save sends only `digest_language` (`frontend/src/pages/Settings.tsx:83`), which must not reset the toggles.
  - The captions toggle's description: "Fetches captions from YouTube from this computer. YouTube's Terms of Service do not allow automated access, so turn this on only if you accept that risk. When off, new videos are listed under Creator updates without a summary." The README repeats this.
- **Shorts.** When skipping is on, an entry whose link path starts with `/shorts/` is stored as `baseline` at confirm and in checks. Pending NULL- or `to_fetch`-status Shorts are also set to `baseline`, at the start of the caption pass. A Short is never fetched and never delivered.
- **Caption pass.** It runs in `digest/runner.py` after the per-source check loop (`runner.py:93-97`) and before selection, over every pending YouTube item with `to_fetch` or NULL status, or with `caption_wait`/`unplayable_wait` still within `CATCHUP_CAPTION_WAIT_HOURS` of `discovered_at`. It orders them by `discovered_at`, then `id`. Expired wait items are left for selection (D7).
  The pass also includes pending `captions_off` items when the setting is now on. Such items exist only after a failed run; they get fetched.
  1. Setting off → `captions_off` (this also ends a running wait).
  2. `captions_blocked`, or `captions_remaining == 0`:
     - a `caption_wait`/`unplayable_wait` item keeps its status unchanged and counts in `waiting_count`
     - a NULL, `to_fetch`, or `captions_off` item becomes `to_fetch` and counts in `deferred_count`
  3. Otherwise `captions_remaining -= 1`, take the video id from `identity_key` (`yt:video:<id>`; an unparsable key → `captions_failed`), and fetch.

  Each item's result is committed on its own, so a later failure does not undo it. Every status written here is in the summarize, creator-update, or held set of D7, so nothing gets stuck.
- **Intended edge cases.**
  - A `caption_wait`/`unplayable_wait` item whose wait expires is listed with its wait reason ("This video has no captions" or "Captions could not be fetched"), even if the user has since turned caption fetching off. It did wait without captions.
  - Waiting items are older, so they are retried first and use the per-run cap. Many uploader-disabled videos can therefore defer new videos for up to `CATCHUP_CAPTION_WAIT_HOURS`. This is bounded, and deferred videos are never lost (see Risks).
- **Fetching** (new module `catchup/transcripts/youtube.py`):
  - `YouTubeTranscriptApi(http_client=session)`. `session` is a `requests.Session` subclass with `trust_env = False`, which ignores proxy and `.netrc` settings from the environment, like `safe_fetch` (`net/safe_fetch.py:111`). Its `request()`:
    - calls `spacer.wait(url)` first
    - sets the CatchUp User-Agent
    - applies a default timeout of (10 s connect, 30 s read)
  - The API object is created through a module-level factory, so tests inject a fake.
- **Track choice** (library 1.2.4: `Transcript` has `language_code` and `is_generated`).
  - Call `.list(video_id)`.
  - The original language is the `language_code` of the first auto-generated track. Take the manually created track in that language if any, else the auto-generated track.
  - With no auto-generated track (best effort, spec): the only manual track, else the first listed manual track.
  - `.translate()` is never called. `.fetch()` the chosen track and join snippet texts into paragraphs.
- **Exception mapping:**

  | Exception | Status |
  |---|---|
  | `TranscriptsDisabled`, `NoTranscriptFound`, or no usable track | `caption_wait` (`no_captions` once the wait ends) |
  | `VideoUnplayable` | `unplayable_wait` (`captions_failed` once the wait ends) |
  | `RequestBlocked` (including its subclass `IpBlocked`), `PoTokenRequired` | `blocked`, and set `captions_blocked = True` |
  | Any other exception, including `CouldNotRetrieveTranscript` subclasses, `requests` errors, and plain `KeyError`/`TypeError` | `captions_failed` |

  Why the first two rows wait (library 1.2.4 source):
  - The library raises `TranscriptsDisabled` whenever the player response has no `captionTracks`. That covers both captions disabled by the uploader and a fresh upload whose auto-captions are not generated yet, and the two cannot be told apart.
  - `VideoUnplayable` is raised for non-OK playability statuses other than login, age, and unavailable, which covers upcoming premieres and live streams.
  - `VideoUnavailable` and `AgeRestricted` do not wait.

  The last row matters because the library's `TranscriptList.build` indexes YouTube's JSON directly (`captions_json["captionTracks"]`, `caption["name"]["runs"][0]["text"]`). A page-format change therefore raises a plain `KeyError`. Only the exception type and video id are logged.
- **Not routed through `safe_fetch`.** The host is fixed, so there is no SSRF exposure. Spacing, the per-run cap, and stopping on a block replace `safe_fetch`'s politeness (spec "Limit and space caption requests").

### D9. Long texts: budget, parts, prompts
- **Context window.**
  - `ModelClient.list_models()` returns `ModelInfo(id, context_window)`.
  - `context_window` is read from the SDK object's extra fields (`model_extra`: `context_window`, else `context_length`). It counts only if `type(value) is int and value > 0`, which rules out strings and booleans. Otherwise it is `None`.
  - Experiment (2026-10-05): openai 3.24.0 keeps unknown fields in `model_extra`.
  - `POST /model/test` still returns the ID list.
  - `model_config.context_window` is nullable. `PUT /model` clears it when the base URL or model ID changes.
  - At run start, if it is NULL, the runner calls `list_models()` once and takes the entry whose `id` equals the configured model ID. It stores the value when found. Any exception here (`ModelError`, `AttributeError`, …) is caught and logged by type, and the window stays unknown.
- **Budget.**
  - If `CATCHUP_SINGLE_CALL_CHARS` is set, use it.
  - Else, when the context window is known: `max(2_000, context_window − SUMMARY_MAX_TOKENS − 2_000)`.
  - Else 60,000.

  The README notes that small local models without a reported context window should set `CATCHUP_SINGLE_CALL_CHARS`.
- **Parts.**
  - Split at blank lines, then at single newlines, then at whitespace, never mid-word. Each part is ≤ budget.
  - Each part is summarized with a part prompt ("part i of n of a transcript/article; write notes covering its points").
  - One combine call turns the part notes into the final summary.
  - Part calls of one item run sequentially inside that item's worker, so the 4-worker pool still bounds concurrency.
  - A part failure makes the item `summary_unavailable`, as today.
- **Prompts.** For `content_origin == "transcript"` and length > `CATCHUP_LONG_ITEM_CHARS` (default 20,000), the final call (single or combine) uses a long-transcript prompt:
  - an overview of 2–3 sentences, then 3–6 key points
  - returned as JSON `{"summary": "..."}`, with the points as "- " lines
  - a statement that the input is spoken text and no visuals were seen

  Other items keep `summary_messages`. `DigestView` renders "- " lines in a summary as a list.
- **Config.**
  - `CATCHUP_MAX_ITEM_CHARS` is removed. If it is set, startup logs a warning naming `CATCHUP_SINGLE_CALL_CHARS`.
  - `.env.example` drops it and documents the new variables, commented out.

### D10. Token usage
- `ModelClient` sums `response.usage.prompt_tokens` and `completion_tokens` under a lock across all chat calls (summaries, parts, combine, grouping, merge). It exposes `usage_totals()`, which returns `None` if no response reported usage.
- The runner writes the totals to `digest_runs.prompt_tokens`/`completion_tokens` when the run ends: succeeded, no new content, or failed.
- `GET /api/digest-runs/{id}` (`api/runs.py:11`) and `GET /api/digests/{id}` (through `digest.run_id`) return them. The run view and the digest show "Tokens: N in / M out", or "Tokens: not reported".

### D11. Dependencies and migration
- Add `youtube-transcript-api>=1.2.4,<1.3` and `lxml>=5,<7` (already installed through trafilatura) to `backend/pyproject.toml`, and update `uv.lock`.
- Alembic `0002` adds the following, with server defaults so existing rows are valid:
  - `sources.kind`
  - `items.transcript_status`
  - `app_settings.youtube_captions`, `youtube_skip_shorts`
  - `model_config.context_window`
  - `digest_runs.prompt_tokens`, `completion_tokens`, `waiting_count`, `deferred_count`
  - `digests.transcript_wait_days`
  - `digest_topics.kind`
  - `digest_items.update_reason`

  It uses `batch_alter_table` for SQLite. Downgrade drops them.

### D12. Review fixes (added after the implementation review, 2026-10-05)
These were found when Claude reviewed the implementation, together with an independent subagent. Every item was reproduced with a script or a live feed before being added.

- **Shared links.**
  - Live (2026-10-05): The Daily (`feeds.simplecast.com/Sl5CSM3S`) has 64 entries with 1 distinct `<link>`. A Captivate show has 121 entries with 1 distinct link.
  - Effect today: link-based dedup (`collection.py` new-entry loop, `api/sources.py` `_unique_entries`) records only the first episode, ever. This is pre-existing, but severe for podcasts.
  - Effect in this branch: the link fallback in transcript matching (`feeds.py` candidate lookup) gives an episode without a transcript a sibling's transcript.
  - Rule: compute `shared_links` = links carried by more than one entry in the fetched feed document. Treat them exactly like `fallback_links`: no link dedup, no matching of existing items by link, no article fetch, no transcript matching by link. An entry with no feed id whose link is shared gets the title+date hash as its identity (spec "Record entries the first time they are seen"). This applies at confirm, at preview (`_unique_entries`), and in `check_source`.
  - Transcript candidates are matched by guid. A link is used only when the item has no guid and the link is not shared.
- **DTD handling.**
  - The `<!DOCTYPE` byte check is replaced. Parse with the D5 parser, then read `root.getroottree().docinfo.internalDTD`. If it declares any entity (`iterentities()` is non-empty), discard all lxml candidates and rely on feedparser's single tag.
  - This works for any encoding, which closes the verified UTF-16 bypass in which attribute entities were expanded. A public DOCTYPE without entities (RSS 0.91) keeps full candidate extraction.
  - Verified: libxml2 expands internal entities in attribute values even with `resolve_entities=False`, and aborts a billion-laughs payload on its own.
- **Candidate details.**
  - A transcript element matches when its namespace is the canonical URI or its prefix is `podcast` (the element's own prefix, not only the root `nsmap`). Elements without a namespace never match.
  - A missing `language` counts as the feed language. Languages compare on the primary subtag, case-insensitively.
- **Joining text.**
  - JSON segments are joined with a space into one paragraph while the speaker is unchanged, including when there is no speaker. A new paragraph starts only when the speaker changes.
  - YouTube caption snippets are joined with spaces. A new paragraph starts before a snippet that begins with `- ` or `>>`, the speaker-change markers.
  - Verified: today's output puts one word, or one caption line, per paragraph.
- **Splitting.**
  - `split_parts` never raises. As a last level, it hard-splits at the budget on a code-point boundary, preferring the last `。！？.!?` within the final 10% of the part. Verified: a 90,000-character Chinese transcript without whitespace is currently `summary_unavailable`.
  - Separator-only overflow is trimmed so every part is ≤ budget.
- **Timings.** VTT and SRT timing patterns accept 2 or more hour digits.
- **Spacing on redirects.** `SpacedSession` waits on the spacer in `send()`, which `requests` also calls for redirect hops, and sets headers and timeout in `request()`.
- **Summary rendering.** `DigestView` `SummaryText` keeps every line in order: "- " lines become list items, and other lines become paragraphs. Verified: today, text after the first bullet that is not itself a bullet is dropped.
- **Creator updates grouping.** Sort by `(source_name.casefold(), source_name, …)` so each exact source name forms one contiguous group with a unique key.

## Risks / Trade-offs

- [The provider overstates `context_window`, or the 1 char/token assumption fails for some script] → the call returns 400, which becomes "summary unavailable" (`client.py:73-76`). The README documents `CATCHUP_SINGLE_CALL_CHARS`. Automatic shrink-and-retry is a non-goal.
- [YouTube changes its internals, or blocks the home IP] → `blocked` is recorded and shown separately, and requests stop for the run. Upgrading the pinned library is the fix. Captions are opt-in and off by default.
- [ToS exposure for users who opt in] → stated in the setting and the README. CatchUp never downloads media.
- [Podcasts without the transcript tag (Lex Fridman, The Daily, The Vergecast)] → their episodes reach Creator updates after the wait. This is honest, but thin coverage. Speech-to-text remains a possible follow-up (D1).
- [A 32 MB feed parsed on every run takes memory and time] → bounded by the limit and the 30 s deadline; the limit is configurable.
- [Matching lxml items to feedparser entries by guid or link can miss] → feedparser's single `podcast_transcript` is the fallback. If both miss, the item is `waiting`, then Creator updates. Fixture tests cover guid and link matching.
- [Caption waits use the per-run cap first] → with more than `CATCHUP_CAPTIONS_PER_RUN` waiting videos, new videos are deferred for up to `CATCHUP_CAPTION_WAIT_HOURS`. This is bounded, and the deferred count is shown.
- [Captions disabled by the uploader look the same as captions not generated yet] → both wait `CATCHUP_CAPTION_WAIT_HOURS` (default 24), so such a video is retried for up to a day before it is listed. Each retry costs up to 3 spaced requests within the per-run cap. How long YouTube takes to generate auto-captions is unverified; the default can be tuned after the alpha.
- [Existing test fakes (`FakeModel` in `tests/test_digest_runner.py:23` and `tests/test_digest_stages.py:11`, `FixtureModel` in `tests/test_core_flow.py:20`, `FakeProvider` in `tests/test_settings_api.py:23`) lack `usage_totals` and return plain ID lists] → tasks update them. The runner also tolerates missing usage.
- [Removing `CATCHUP_MAX_ITEM_CHARS` breaks configs that set it] → a startup warning, the README, and release notes. The value was only a cap, so ignoring it cannot lose data.
- [A long-transcript summary returned as JSON with list lines may be malformed] → covered by tests with a fake client; the real run with DeepSeek checks the format.

## Migration Plan

- Deploy: `0002` runs at startup like `0001` (`db.py`). Existing sources start as `feed` and are classified on their next successful check (D2).
- Rollback: downgrade `0002`, or restore the SQLite backup the README describes. On downgrade, Creator updates topics remain as ordinary topics without summaries; summarized items are untouched.

## Testing

- **Rules for all tests:**
  - no real network (respx for httpx; a fake transport adapter for `requests`; a fake `YouTubeTranscriptApi`)
  - no real sleeps (inject the spacer's sleep and clocks)
  - no real keys
  - nothing written outside pytest temp dirs
- Backend tests are listed per task in `tasks.md`, and cover every spec scenario.
- Frontend: vitest for the Sources preview kind text, the Settings YouTube toggles, Creator updates rendering, the waiting/deferred counts, and the token line.
- **Review (Claude), live from this machine:**
  - The Vergecast preview.
  - The Apple Lex Fridman URL resolving to its feed.
  - A Buzzsprout episode transcript collected end to end.
  - DeepSeek `/models` returning `context_window`, with the user's key entered by the user.
  - With captions on, `s7d2d8FhevU` summarized from its full transcript.
- **Manual test with the user:**
  - A real digest with one podcast and one YouTube channel, captions off and then on.
  - Checks: Creator updates; the long summary covers the last hour of the 3.6-hour sample; token totals match the DeepSeek usage page.

## Rollout

- One PR closes #5 and #6.
- The README "Supported sources" section is rewritten: podcasts with published transcripts, YouTube with opt-in captions and the ToS note, Apple Podcasts URLs, and the removed variable.
- The release notes for the next tag mention the `CATCHUP_MAX_ITEM_CHARS` removal.

## Open Questions

- Whether DeepSeek's live `/models` response really carries `context_window` is checked in review. If it does not, the 60,000-character fallback applies, and nothing in the specs or tasks changes.
