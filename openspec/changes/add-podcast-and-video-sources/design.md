# Design: add-podcast-and-video-sources

Status: Proposal 1 chosen by the user on 2026-10-05, with amendments:
1. a "Creator updates" section
2. one appearance per item, with a 7-day transcript wait for podcasts
3. a single-call budget derived from the model's context window
4. request control for the captions library
5. original-language captions

The user confirmed the amended design the same day and also accepted:
- the `captions_failed` reason
- stopping caption requests after the first block
- resolving transcripts in the run's check phase instead of at confirm
- renaming the override to `CATCHUP_SINGLE_CALL_CHARS`

Open questions resolved:
- no description excerpt in Creator updates
- `CATCHUP_CAPTIONS_PER_RUN` defaults to 20
- the wait is configurable as `CATCHUP_TRANSCRIPT_WAIT_DAYS`, default 7

Proposal 2 is kept below for the record.

## Solution Proposals

Context:
- Request: Support podcast sources (#5) and YouTube channel sources (#6) in one change.
  - Podcasts: podcast RSS feeds and Apple Podcasts URLs. Transcripts come from `<podcast:transcript>`.
  - YouTube: channels are listed through the official channel RSS. Captions are fetched only if the user turns on "fetch captions locally". It is off by default, and the setting states the conflict with YouTube's Terms of Service.
  - Items that cannot be summarized appear once in a "Creator updates" section.
  - Long transcripts are summarized in full. Today every item is cut to 20,000 characters.
- Research Source: `research.md`. Sections used:
  - "Current behavior with a YouTube channel URL"
  - "Current behavior with podcast URLs"
  - "Text length limits on the summarization path"
  - "Item states and 'unavailable' display"
  - "Requirements on record"
  - External facts: `<podcast:transcript>`, real feeds, feedparser, iTunes Lookup, `youtube-transcript-api`, DeepSeek limits, long-transcript estimates, speech-to-text, Terms

### Shared by both proposals

- **Source kind.** `Source` gets a `kind`: `feed`, `podcast`, or `youtube`. One Alembic migration (`0002`) adds it, and existing rows default to `feed`.
  - Detection at discovery:
    - `youtube` for a feed URL on `www.youtube.com/feeds/videos.xml`, which the channel page already declares (`sources/discovery.py:50-99`).
    - `podcast` for a feed whose items carry audio enclosures.
  - The preview shows the kind and how transcripts will be obtained.
  - Spec: `source-management` (modified).
- **Apple Podcasts URLs.**
  - A URL matching `podcasts.apple.com/{cc}/podcast/{slug}/id{digits}` is resolved before generic discovery. The resolver calls `https://itunes.apple.com/lookup?id=<id>&entity=podcast` through `safe_fetch` and takes `feedUrl` (research, "iTunes Lookup API").
  - An episode URL (`?i=`) follows the whole show. The preview says so, reusing the existing whole-site notice flag `follows_site_feed_notice` (`discovery.py:31-34`).
  - Lookup failures and a missing `feedUrl` are reported as unsupported sources.
- **Larger feeds.**
  - `safe_fetch` gets an optional per-call `max_bytes`. Feed fetches (preview, confirm, run checks) use a feed limit, `CATCHUP_MAX_FEED_BYTES`, default 32 MB. Article and transcript fetches keep 5 MB.
  - This is needed because The Vergecast (6.2 MB) fails today (`net/safe_fetch.py:18,163,175`), and The Daily's full archive is 20.3 MB.
  - Spec: `source-management` "Fetch user-supplied URLs safely" (modified: two limits).
- **Podcast transcripts.**
  - Parsing:
    - `parse_feed` (`sources/feeds.py:63-87`) gets per-entry transcript candidates by parsing item XML with lxml, which is already installed through trafilatura. Entity resolution and network access are disabled.
    - It matches the tag by its `podcast:` prefix and the local name `transcript`, not by namespace URI, because one major feed uses a non-canonical URI.
    - feedparser cannot be used, because it keeps only the last tag (research, "feedparser and transcripts").
  - Preference order: `text/plain` > `text/vtt` > `application/x-subrip`/`application/srt` > `application/json` > `text/html`. A tag whose `language` matches the feed language wins.
  - Fetching: transcripts are fetched through `safe_fetch` with the run's host spacer. The format is sniffed when the server sends `application/octet-stream`.
  - Each format is converted to plain text:
    - Cues are merged into paragraphs.
    - Speaker names from VTT `<v>`, JSON `speaker`, and SRT "Name:" are kept as "Name: …" lines.
    - Timing lines are dropped.
    - HTML goes through trafilatura, because Buzzsprout's HTML transcript is a whole web page.
  - Spec: `content-collection` (modified "Keep article text for summarization"; new "Use published transcripts for audio and video").
- **Transcript status and one appearance per item.** Podcast and YouTube items get a `transcript_status`. The value decides what a run does with a pending item:

  | `transcript_status` | Meaning | What a run does |
  |---|---|---|
  | `found` | Transcript stored in `content_text`, `content_origin = "transcript"` (`models.py:83-84`) | Summarize, deliver |
  | `to_fetch` | Not resolved yet: new at confirm, or deferred by the per-run captions limit | Resolve this run (see below) |
  | `waiting` | Podcast, no transcript yet, discovered less than 7 days ago | Re-check against this run's feed fetch; stay pending; not in the digest |
  | `no_transcript` | Podcast still without a transcript 7 days after `discovered_at` | Creator updates, deliver |
  | `captions_off` | YouTube, captions setting off | Creator updates, deliver |
  | `no_captions` | YouTube, the video has no captions (`TranscriptsDisabled`, `NoTranscriptFound`) | Creator updates, deliver |
  | `blocked` | YouTube refused the request (`RequestBlocked`, `IpBlocked`, `PoTokenRequired`) | Creator updates, deliver |
  | `captions_failed` | Any other library error (`VideoUnavailable`, `AgeRestricted`, `YouTubeRequestFailed`, …) | Creator updates, deliver |

  - Every delivered item becomes `delivered`, as today (`digest/runner.py:185`), so it appears in exactly one digest. That covers both the summarized topics and Creator updates.
  - A `waiting` podcast item is never delivered early.
  - The 7-day clock runs from `discovered_at`, because `published_at` can be missing or old.
  - The re-check uses the feed that the run already fetches (`collection.py:36`). If the item's entry now carries a transcript tag, the transcript is fetched and the item becomes `found`.
  - A run whose only pending items are `waiting` ends as `no_new_content`, and says "N episodes are waiting for transcripts".
  - Spec: `digest-generation` "Include every pending item" (modified: waiting podcast items are held for up to 7 days); `content-collection` (new).
- **When transcripts are resolved.**
  - Confirm-time first-add marks podcast and YouTube items `to_fetch` instead of fetching. Today the article fetch runs at confirm (`api/sources.py:116-125`); for these kinds it is skipped, so confirm stays fast.
  - Resolution happens in the run's check phase, sequentially, with the run's `HostSpacer` (`net/host_spacing.py`; created at `digest/runner.py:92`).
- **YouTube captions (opt-in).**
  - Request control:
    - Videos are fetched one at a time.
    - The library gets a `requests` session whose transport calls `HostSpacer.wait(url)` before every request. Its 3 requests per video (watch page, player, timedtext; research) are therefore spaced like `safe_fetch` requests. The session also sets CatchUp's User-Agent and a timeout.
    - At most `CATCHUP_CAPTIONS_PER_RUN` videos (default 20) are fetched per run. The rest stay `to_fetch` for the next run, and the run reports "N videos deferred to the next run".
    - After the first `blocked` result, the run makes no further caption requests. That video becomes `blocked`, and untried videos stay `to_fetch`.
  - Language: use captions in the video's original language. Prefer a manually created track over the auto-generated one, and never use YouTube's machine-translated tracks (`Transcript.translate()` is not called). The model writes the summary in the digest language, as today.
    - The original language is the language of the auto-generated track, which is speech recognition of the audio.
    - With no auto-generated track: the only manual track if there is one; otherwise the first listed manual track. This is a heuristic, because the library does not expose the audio language (unverified).
  - Recording: `blocked`, `no_captions`, and `captions_failed` are stored and shown separately.
  - The fetch path is outside `safe_fetch`. That is acceptable for SSRF, because the host is fixed (`youtube.com`); spacing and limits are handled above.
  - The setting text states the ToS conflict, and the README repeats it.
  - Spec: new `video-transcripts` capability, or folded into `content-collection` (decided at plan time).
- **Creator updates section** (new requirement, user decision 2026-10-05).
  - It is a section after the topic summaries, grouped by creator or show (the source title).
  - Each entry shows the title, publication time, link, and a reason label:

    | Status | Label |
    |---|---|
    | `captions_off` | "Caption fetching is off" |
    | `no_captions` | "This video has no captions" |
    | `blocked` | "Blocked by YouTube" |
    | `captions_failed` | "Captions could not be fetched" |
    | `no_transcript` | "No transcript within 7 days" |

  - No model call is made for these items.
  - Shorts never appear here. With "skip Shorts" on (the default), they are stored as `baseline`.
  - Show notes and video descriptions are not summarized, because summarizing them would claim to cover content that was not processed (`docs/handoff.md:47,113`).
  - Storage: digest items carry an `update_reason` and are rendered by `DigestView` (`frontend/src/pages/DigestView.tsx:38-56`) in their own section. The exact schema (nullable `topic_id` vs a section marker) is decided at plan time.
  - Spec: `digest-generation` (new "Creator updates"; modified "Summarize items once and group them by topic").
- **Long-transcript summary shape.**
  - Transcripts longer than `CATCHUP_LONG_ITEM_CHARS` (default 20,000 characters) use a long-transcript prompt. It asks for a 2–3 sentence overview plus 3–6 key points, and tells the model the input is a spoken transcript, so it must not describe visuals.
  - Shorter items keep the 2–4 sentence prompt (`llm/prompts.py:24-36`).
  - Spec: `digest-generation` "Summaries focus on substance" (modified).

---

### Proposal 1 — Transcripts resolved in the check phase, single call within a context-derived budget (chosen)

- Overview: Transcripts are resolved during the run's check phase and stored in the existing `content_text`.
  - Summaries make one model call when the text fits a budget derived from the model's context window. Only longer texts are split into chunks.
  - YouTube settings are global.
  - Speech-to-text is out of scope.
- Key Changes:
  - `collection.py`:
    - A transcript step handles podcast and YouTube items: `to_fetch` resolution, `waiting` re-checks, and the 7-day expiry.
    - `article_text()` (`collection.py:14-29`) stays for `feed` sources.
  - Single-call budget (replaces the fixed `content_text[:max_chars]` at `summarize.py:30`):
    - `list_models` (`llm/client.py:85-87`, used at `api/settings.py:123`) also returns each model's `context_window` when the provider reports it.
    - DeepSeek documents `context_window` and `max_output_tokens` on `GET /models` (https://api-docs.deepseek.com/api/list-models, fetched 2026-10-05). This is not yet verified live.
    - `ModelConfig` (`models.py:37-45`) stores `context_window` (nullable) when settings are saved. If it is missing at run start, for example in configs saved before this change, the runner asks `/models` once.
    - Budget in characters = (`context_window` − `SUMMARY_MAX_TOKENS` − 2,000 for prompt overhead) × 1 character per token.
      - One character per token is a conservative assumption for Chinese across tokenizers. DeepSeek documents about 0.6 tokens per Chinese character and 0.3 per English character (research).
      - For `deepseek-flash` (1M) this gives about 994,000 characters, so the 3.6-hour sample is one call.
    - When the provider reports no `context_window`, the budget is 60,000 characters.
    - Above the budget, the text is split at paragraph boundaries into chunks no larger than the budget. Each chunk is summarized, then one combining call produces the final summary. At 60,000 characters, the 3.6-hour sample takes 3 calls + 1.
    - `CATCHUP_MAX_ITEM_CHARS` is removed. A new optional override `CATCHUP_SINGLE_CALL_CHARS` exists for users who know their limit. It is renamed so that the `20000` value copied from today's `.env.example:11` does not silently override the derived budget.
  - `AppSettings` (`models.py:48-53`) gets `youtube_captions` (default off) and `youtube_skip_shorts` (default on). Both are shown on the Settings page. Shorts are recognized by their `/shorts/<id>` link (research, "Channel RSS").
  - Cost visibility:
    - `chat_json` (`llm/client.py:89-107`) returns the response `usage`.
    - `DigestRun` gets `prompt_tokens` and `completion_tokens`. The run page and the saved digest show "N tokens used".
    - There are no prices, because the provider and model are arbitrary.
  - Migration `0002`:
    - `sources.kind`
    - `items.transcript_status`
    - the digest-item `update_reason` (plus the section schema)
    - the two `app_settings` columns
    - `model_configs.context_window`
    - the two `digest_runs` token columns
  - Capabilities modified: `source-management`, `content-collection`, `digest-generation`, `model-settings` (context window; YouTube options on the Settings page). New: `video-transcripts`, or folded into `content-collection`.
- Trade-offs:
  - Benefits:
    - Fits the current pipeline. Transcripts are just better `content_text`, so caching, history, and grouping stay as they are.
    - For DeepSeek, nearly every episode is one call. The 3.6-hour sample is about 51k tokens, about $0.02 (research, "Long-transcript estimates").
    - Providers without `context_window` still work through chunking.
    - No new credentials, binaries, or Docker changes.
  - Costs:
    - The budget trusts the provider's `context_window`. A provider that overstates it still yields a 400, which becomes "summary unavailable" (`client.py:73-76`). There is no automatic retry with smaller chunks.
    - The 1-character-per-token assumption under-uses large contexts for English. That does not matter at 1M, but costs extra chunk calls on small-context models.
    - Global YouTube settings cannot treat channels differently.
    - Coverage for podcasts without the tag stays at zero. Lex Fridman, The Daily, and The Vergecast publish no `<podcast:transcript>`. Their episodes reach Creator updates after 7 days.
    - Runs get slower for caption sources: about 3 spaced requests per video, at most 20 videos per run by default.
- Validation:
  - Unit tests with fixture feeds:
    - Buzzsprout: 4 tags, pick plain or VTT.
    - Podcasting 2.0: non-canonical namespace, `application/srt` served as octet-stream.
    - Transistor: JSON with string `startTime`.
    - Captivate: HTML only.
    - A feed with no tags gives `waiting`.
  - Converter tests for VTT, SRT, JSON, and HTML, including speakers.
  - Discovery tests:
    - iTunes Lookup (mocked) for show and episode URLs, and lookup failure.
    - A 6 MB feed passes with the feed limit, and a 6 MB article still fails.
  - State tests with a fake clock:
    - A `waiting` item is not in day-1 digests.
    - It becomes `found` when a later feed fetch shows a tag.
    - It reaches Creator updates once after 7 days, and is never listed again.
    - A run with only waiting items ends `no_new_content` with the waiting count.
  - YouTube tests:
    - Setting off gives `captions_off`, listed once.
    - Mocked exceptions map to `no_captions`, `blocked`, and `captions_failed`.
    - The first `blocked` stops further requests, and untried videos stay `to_fetch`.
    - The per-run limit defers the rest.
    - The spacer is called before each of the library's requests.
    - Shorts are skipped.
  - Language tests with a mocked transcript list:
    - A manual original-language track beats the auto-generated one.
    - The auto-generated original track beats a manual track in another language.
    - `translate()` is never called.
  - Budget tests:
    - `context_window` 1,000,000 gives one call at 169,961 characters.
    - No `context_window` gives 3 + 1 calls.
    - `CATCHUP_SINGLE_CALL_CHARS` overrides both.
    - Token totals add up.
  - Live checks, done by Claude in review:
    - Vergecast preview.
    - Apple Lex Fridman URL → feed.
    - Buzzsprout episode transcript collected.
    - DeepSeek `/models` returns `context_window` (with the user's key, entered by the user).
    - With captions on, `s7d2d8FhevU` summarized from its full transcript.
  - Real run with the user and DeepSeek:
    - The long summary mentions topics from the last hour of the episode.
    - The token count matches the provider's usage page.
    - Creator updates looks right for a channel with captions off.
- Resolved questions (user, 2026-10-05):
  - Creator updates shows no description excerpt: only title, time, link, and reason.
  - `CATCHUP_CAPTIONS_PER_RUN` defaults to 20.
  - The transcript wait is configurable as `CATCHUP_TRANSCRIPT_WAIT_DAYS`, default 7. "7 days" elsewhere in this document means this default.

---

### Proposal 2 — Transcript providers resolved at digest time, always chunked, with speech-to-text for podcasts (not chosen)

- Overview: A transcript-provider chain runs at digest time, only for pending podcast and YouTube items:
  1. the `<podcast:transcript>` tag
  2. YouTube captions (opt-in per channel)
  3. speech-to-text of the podcast audio enclosure, through a user-supplied OpenAI-compatible transcription endpoint (Groq, OpenAI)

  Transcripts are cached in their own table. Summaries always use chunking. Usage is reported per item, including transcription minutes.
- Key Changes:
  - A `transcripts/` package with `PublishedTranscript`, `YouTubeCaptions`, and `SpeechToText` providers, and a "fetching transcripts" run stage.
  - A `transcripts` table.
  - A second encrypted provider key for speech-to-text.
  - ffmpeg in the image to split audio under 25 MB.
  - Per-source options: captions, skip Shorts, transcribe audio.
  - Per-item usage columns.
  - YouTube audio excluded: the Terms forbid downloading, and yt-dlp needs PO tokens.
- Trade-offs:
  - Benefits:
    - Podcasts without the tag can still be summarized when the user pays for transcription (about $0.14 on Groq turbo for the 3.6-hour sample).
    - Per-channel opt-in.
    - Works the same with any model size.
  - Costs:
    - Much larger change: second credential, binary dependency, audio downloads of hundreds of MB, more tables.
    - Speech-to-text is not committed (`docs/handoff.md:55`).
    - Always chunking costs up to 10× the output budget on large-context models.
    - Slower runs.
- Why not chosen: the user picked Proposal 1. Speech-to-text can be a later change built on `transcript_status` and source kinds, if the alpha shows missing podcast transcripts are the main gap.

---

Recommendation: Proposal 1, chosen by the user on 2026-10-05.
