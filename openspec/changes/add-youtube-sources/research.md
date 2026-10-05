# Research: YouTube channel sources with transcripts (#6)

- Date: 2026-10-05
- Query: How does CatchUp handle a pasted YouTube URL today, where would transcripts fit into collection, storage, summarization, and display, and what are the current external facts (feeds, transcripts, official API, terms)?
- Git ref: main @ a0ba6e2
- Change: `add-youtube-sources`
- Issue: [#6](https://github.com/Zhuoang2/catchup/issues/6), including the third-party suggestion and maintainer note

## Summary

A YouTube channel URL already works as a generic RSS source today. The channel page declares its RSS feed, and `discover()` finds it. Each video becomes an item identified by `yt:video:<id>`, with the video description (a few hundred characters) as its text. Because that text is shorter than `CATCHUP_SHORT_TEXT_CHARS` (500), `article_text()` fetches the watch page and runs trafilatura on it. Summaries are therefore based on descriptions and page text, not on what is said in the video.

Nothing in the code knows about transcripts. There is no item state or display for "no transcript available", and the summary prompt is generic. The confirmed requirement is that audio and video are summarized only when a transcript or captions exist, and that a missing transcript is reported as unsupported (`docs/handoff.md:47,113`).

Live checks from this machine (residential IP, 2026-10-04/05) found:
- channel pages, the channel RSS feed, and `youtube-transcript-api` 1.2.4 all worked
- the feed lists only the latest 15 uploads, Shorts included
- YouTube's Terms of Service forbid automated access by scrapers
- the official Data API can download captions only for videos the caller can edit

## Detailed Findings

### Current behavior with a YouTube channel URL (live, 2026-10-05)
- `discover("https://www.youtube.com/@GoogleDevelopers")` returned:
  - feed `https://www.youtube.com/feeds/videos.xml?channel_id=UC_x5XG1OV2P6uZZ5FSM9Ttw`
  - title "Google for Developers"
  - site URL `https://www.youtube.com/channel/UC_…`
  - 15 entries, no whole-site notice
- Each entry has:
  - `identity_key` `yt:video:<videoId>`
  - link `https://www.youtube.com/watch?v=<id>`, or `https://www.youtube.com/shorts/<id>` for Shorts
  - `content_text` = the media description (362–449 characters in the sample)
- Code path:
  1. `discover` fetches the page and finds the declared `rel=alternate` RSS link — `backend/src/catchup/sources/discovery.py:50-99`
  2. `parse_feed` uses `entry.id` as the identity and `entry.summary`/content as the text — `backend/src/catchup/sources/feeds.py:63-87`

### Text used for summarization
- `article_text(entry, fallback_links, threshold, *, spacer=None)` — `backend/src/catchup/collection.py:14-29`:
  - It returns the feed text with origin `"feed"` when the text is at least the threshold or the link is a fallback link.
  - Otherwise it calls `safe_fetch(entry.link)` and `trafilatura.extract`, returning origin `"article"`, and falls back to the feed text.
  - For YouTube items (descriptions under 500 characters), this fetches the watch page.
- It is called for new items during runs (`collection.py`, `check_source`) and for pending items at confirm time (`backend/src/catchup/api/sources.py:118-121`).
- `Item.content_origin` is `String(16)`. The values in use are `"feed"` and `"article"` — `backend/src/catchup/models.py:84`, `migrations/versions/0001_initial.py:62`.
- `Item.content_text` is `Text` (unbounded) — `models.py:83`. Stage 1 truncates the input to `CATCHUP_MAX_ITEM_CHARS` (default 20000) — `digest/summarize.py`; config default `backend/src/catchup/config.py:34`.

### Item states and "unavailable" display
- `Item.state` is `pending`, `delivered`, or `baseline` — `models.py:87`; set at `api/sources.py:116`, `collection.py:72`, `digest/runner.py:102,185`.
- `DigestItem.summary_unavailable` (bool) marks a summary the model failed to produce — `models.py:153`; set at `digest/runner.py:183`.
- There is no field for "content unavailable" or "no transcript".
- The Digest view shows "Summary unavailable" when that flag is set — `frontend/src/pages/DigestView.tsx:51`. The source preview shows entries and an optional whole-site notice — `frontend/src/pages/Sources.tsx:107-112`.

### Summary prompt
- `summary_messages(title, text, language)` is generic. It covers substance, 2–4 sentences, no metadata, and "If there is no substantive content (e.g. only a link), say so in one short sentence." It has no notion of video, transcript, or visual content — `backend/src/catchup/llm/prompts.py:24-36`.

### Fetching
- All requests go through `safe_fetch`, which applies:
  - the SSRF guard
  - a CatchUp User-Agent
  - 429/`Retry-After` handling
  - a 30 s deadline
  - a 5 MB cap
  - optional per-host spacing
- Source: `backend/src/catchup/net/safe_fetch.py`; `improve-source-reliability` (archived).
- No third-party HTTP client used for sources bypasses it today.

### Requirements on record
- "Sources: selected public websites/blogs, and podcasts and long videos where captions or transcripts are obtainable" — `docs/handoff.md:44`.
- "Captions or a transcript are the prerequisite for audio/video in the first release; without processing the visuals, we must not claim to have summarized visual content" — `docs/handoff.md:47`.
- Transcribing audio when no transcript exists is not committed — `docs/handoff.md:55`.
- Acceptance suggestion: "when captions are missing, clearly report that the item is unsupported" — `docs/handoff.md:113`.
- Proposal: "podcast and video sources with accessible transcripts or captions" — `docs/proposal.md:36`.

### Issue #6 discussion
- The issue body notes intermittent RSS 404s since about 2025-12, and transcript blocking from cloud IPs (`gh issue view 6`).
- Comment from `pushkarsingh32` (2026-10-04), who discloses operating the service: suggests getyoutubetranscript.com, a credit-based API with channel listing (latest 30 videos) and transcripts, error codes, and 100 free credits.
- Maintainer note (2026-10-04): no decision. Options to evaluate:
  - the official Data API with the user's key
  - local caption fetching
  - other providers

  Criteria: works without mandatory paid accounts, reliability, ToS compliance, privacy, cost.
- Context: deployment is local only (D-011), so requests come from the user's own network.

## Current Specs
- `source-management`: "Preview a source from a pasted URL"; "Explain unsupported and duplicate sources"; "Fetch user-supplied URLs safely"; "Identify CatchUp in outgoing requests"; "Honor rate limits when fetching".
- `content-collection`: "Record entries the first time they are seen"; "Keep article text for summarization" (fetch the linked article when the feed text is short); "Readable titles for untitled entries".
- `digest-generation`:
  - "Summaries focus on substance": an item without substantive content is described in one short sentence.
  - "Summarize items once…": an item whose summary could not be produced is shown as unavailable.
- `local-deployment`: requests come from the user's own machine.

## External facts (verified 2026-10-04/05; live requests from this machine, residential IP)

**Channel pages and IDs** (live, `@GoogleDevelopers`, `@lexfridman`; HTTP 200, no consent redirect)
- Pages contain `<link rel="canonical" href=".../channel/UC…">`, `"externalId":"UC…"`, and `<link rel="alternate" type="application/rss+xml" href=".../feeds/videos.xml?channel_id=UC…">`.
- Watch pages contain `"videoDetails":{…"channelId":"UC…"}` and `"ownerProfileUrl":"http://www.youtube.com/@…"`. A bare `"channelId"` also matches unrelated channels on the page, so the `videoDetails` occurrence is the reliable one. There is no `itemprop="channelId"`.

**Channel RSS** (live; 4 requests, 5 s apart; all 200)
- The feed returns 15 entries per channel, consistent across requests. Fields:
  - `yt:videoId`, `yt:channelId`, title, link, author, published, updated
  - `media:group` with title, content, thumbnail, full description, and community stats
- Shorts are included (links `/shorts/<id>`).
- The 15 entries reached back to 2026-08-26 (Google) and 2026-01-31 (Lex), i.e. only the latest 15 uploads.
- `?playlist_id=UU<channel-suffix>` (uploads playlist) returned the same 15 videos.
- Intermittent 404s reported since about 2025-12 (issue #6; 2026-10-01 research in `docs/process/ai-usage-log.md`) did not occur in this sample.

**`youtube-transcript-api`**
- Latest version is 1.2.4 (2026-01-29), Python >=3.8,<3.15 (https://pypi.org/pypi/youtube-transcript-api/json).
- Open issues (https://github.com/jdepoix/youtube-transcript-api/issues):
  - #592 `PoTokenRequired` (`exp=xpe`), last comment 2026-08-27
  - #612: 429 retry does not rotate IP
  - #618 (2026-09-28): regional/proxy errors
- API (introspected 1.2.4):
  - `YouTubeTranscriptApi(proxy_config=None, http_client=None)`
  - `.fetch(video_id, languages=('en',), preserve_formatting=False)` returns a `FetchedTranscript` with `.snippets`, `.language_code`, `.is_generated`, `.to_raw_data()`
  - `.list(video_id)` returns a `TranscriptList` with `find_transcript`, `find_manually_created_transcript`, `find_generated_transcript`; a `Transcript` has `.fetch()` and `.translate()`
- Exceptions: `TranscriptsDisabled`, `NoTranscriptFound`, `VideoUnavailable`, `VideoUnplayable`, `AgeRestricted`, `InvalidVideoId`, `RequestBlocked`, `IpBlocked`, `PoTokenRequired`, `YouTubeRequestFailed`, `YouTubeDataUnparsable` (all subclass `CouldNotRetrieveTranscript`).
- Each fetch makes 3 requests (GET /watch, POST /youtubei/v1/player, GET /api/timedtext) with the library's own HTTP client, not CatchUp's `safe_fetch`.
- **Live:** two videos succeeded:
  - `Rnz9mOyxk0k`: manual English, 894 characters
  - `s7d2d8FhevU`: a 3.6-hour episode, manual English, 169,961 characters

  Auto-generated English tracks were also listed. This worked even though `exp=xpe` appeared in the watch page's caption URL.
- The README states that YouTube blocks most cloud-provider IPs (2026-10-01 research).

**YouTube Data API v3** (https://developers.google.com/youtube/v3/determine_quota_cost, updated 2026-09-15)
- Costs: `channels.list` 1 unit (accepts `forHandle`), `playlistItems.list` 1, `videos.list` 1, `captions.list` 50. `search.list` now has its own daily bucket of 100 calls.
- The default is 10,000 units/day, resetting at midnight Pacific.
- An API key works for public data: "unauthorized requests only retrieve public data" (getting-started). Listing uploads with a key alone was not tested.
- `captions.download` requires OAuth with edit permission on the video and costs 200 units (https://developers.google.com/youtube/v3/docs/captions/download).

**Terms**
- YouTube Terms of Service (https://www.youtube.com/t/terms) prohibit accessing the Service "using any automated means (such as robots, botnets or scrapers)". The exceptions are public search engines following robots.txt, or prior written permission.
- YouTube API Services Developer Policies (https://developers.google.com/youtube/terms/developer-policies) prohibit scraping or obtaining "scraped YouTube data or content". Stored API data must be refreshed or deleted after 30 days. Storing audiovisual content requires approval.
- RSS feeds are a published YouTube endpoint. Whether polling them counts as "automated means" under the ToS is not addressed in the sources checked (unverified).

**yt-dlp**
- Latest release is 2026.08.19.
- `--skip-download --write-subs --write-auto-subs --sub-langs` fetches subtitles only.
- Full YouTube support now requires yt-dlp-ejs plus a JavaScript runtime (deno).
- The PO Token Guide says the `web` client needs a PO token for subtitles.
- 2026 issues: #17412 (subtitle "no data blocks", later stopped), #17666 (some clients SABR-only), #17682 (403s, closed).
- Not run against YouTube.

## Code References
- `backend/src/catchup/sources/discovery.py:50-99` — declared-feed discovery (finds YouTube channel RSS)
- `backend/src/catchup/sources/feeds.py:63-87` — entry identity, link, text
- `backend/src/catchup/collection.py:14-29` — `article_text` (fetches the watch page for short descriptions)
- `backend/src/catchup/api/sources.py:116-125` — confirm-time first-add and article text
- `backend/src/catchup/models.py:83-87,153` — `content_text`, `content_origin`, `state`, `summary_unavailable`
- `backend/src/catchup/llm/prompts.py:24-36` — generic summary prompt
- `frontend/src/pages/DigestView.tsx:45-51`, `frontend/src/pages/Sources.tsx:107-112` — item and preview display

## Related History
- 2026-10-01 source feasibility research: YouTube RSS flaky, transcript library stale, cloud IPs blocked (`docs/process/ai-usage-log.md`).
- D-011 (local deployment only) makes residential-IP behavior the relevant case.
- Issue #6 was created 2026-10-04; it received the third-party comment and the maintainer note the same day.
