# Research: Podcast and YouTube sources with transcripts (#5, #6)

- Date: 2026-10-04 (YouTube sections first written the same day; supplementary podcast, long-transcript, and speech-to-text sections added the same day after #5 and #6 were merged into this change)
- Query: How does CatchUp handle a pasted YouTube URL, a podcast RSS feed, and an Apple Podcasts URL today? Where would transcripts fit into collection, storage, summarization, and display? How are long texts truncated today, and what are the current external facts (feeds, transcript formats, iTunes Lookup, official APIs, model limits, terms)?
- Git ref: main @ 6021cba
- Change: `add-podcast-and-video-sources` (renamed from `add-youtube-sources`)
- Issues: [#5](https://github.com/Zhuoang2/catchup/issues/5) podcasts, [#6](https://github.com/Zhuoang2/catchup/issues/6) YouTube, including the third-party suggestion and maintainer note on #6

## Summary

A YouTube channel URL already works as a generic RSS source today. The channel page declares its RSS feed, and `discover()` finds it. Each video becomes an item identified by `yt:video:<id>`, with the video description (a few hundred characters) as its text. Because that text is shorter than `CATCHUP_SHORT_TEXT_CHARS` (500), `article_text()` fetches the watch page and runs trafilatura on it. Summaries are therefore based on descriptions and page text, not on what is said in the video.

A podcast RSS feed also works as a generic feed today, as long as it is at most 5 MB. Episodes are summarized from their show notes, or from the episode web page when the notes are short. Enclosures and `<podcast:transcript>` tags are ignored. Feeds above 5 MB (live: The Vergecast 6.2 MB, The Daily 20.3 MB) fail with the size error. An Apple Podcasts URL fails with "No supported feed was found", because Apple pages declare no RSS link.

Nothing in the code knows about transcripts. There is no item state or display for "no transcript available", and the summary prompt is generic. Every item's text is cut to `CATCHUP_MAX_ITEM_CHARS` (20,000 characters) before summarization. That cut keeps about 12% of the 3.6-hour sample transcript (169,961 characters). The confirmed requirement is that audio and video are summarized only when a transcript or captions exist, and that a missing transcript is reported as unsupported (`docs/handoff.md:47,113`).

Live checks from this machine (residential IP, 2026-10-04) found:
- channel pages, the channel RSS feed, and `youtube-transcript-api` 1.2.4 all worked
- the YouTube feed lists only the latest 15 uploads, Shorts included
- YouTube's Terms of Service forbid automated access by scrapers and downloading content
- the official Data API can download captions only for videos the caller can edit
- `<podcast:transcript>` is on about 4.2% of all episodes indexed by Podcast Index. Hosts that support it (Buzzsprout, Transistor, Captivate, Spreaker, Libsyn) publish it on most recent episodes.
- feedparser 6.0.14 keeps only the last `<podcast:transcript>` tag of an item
- the iTunes Lookup API returns `feedUrl` for a show ID without authentication; it does not resolve episode IDs
- DeepSeek `deepseek-flash` has a 1M-token context and a 384K maximum output

## Detailed Findings

### Current behavior with a YouTube channel URL (live, 2026-10-04)
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

### Issue #5 scope
- The issue asks for:
  - podcast RSS feeds and Apple Podcasts URLs, resolved to RSS with the no-auth iTunes Lookup API
  - summaries of episodes that publish `<podcast:transcript>`
  - episodes without a transcript clearly marked as unsupported
- Its 2026-10-01 research note: transcript-tag adoption is low (~9% of episodes in a small sample) (`gh issue view 5`).

### Current behavior with podcast URLs (live, 2026-10-04, `discover()` on main)
- `https://feeds.buzzsprout.com/1.rss` resolved to the feed `https://rss.buzzsprout.com/1.rss` ("How to Start a Podcast", 11 entries).
  - The first entry's identity is `Buzzsprout-2562823`, from the RSS guid.
  - Its link is the episode web page `https://www.buzzsprout.com/1/2562823`.
  - Its text is 352 characters. That is under the threshold, so `article_text()` would fetch and extract the episode page.
- `https://lexfridman.com/feed/podcast/` returned 503 entries. The first entry's text is 2,164 characters of show notes, so the feed text is used as is (origin `"feed"`).
- `https://podcasts.apple.com/us/podcast/lex-fridman-podcast/id1434243584` raised `FetchError no_feed` "No supported feed was found at this URL."
  - The page declares no RSS link.
  - The probes are same-origin paths on `podcasts.apple.com`.
- `https://feeds.megaphone.fm/vergecast` (6,193,456 bytes) raised `FetchError fetch_failed` "The source response exceeds the 5 MB limit."
  - The limit is `MAX_BYTES = 5 * 1024 * 1024` — `backend/src/catchup/net/safe_fetch.py:18`.
  - The error is raised at `safe_fetch.py:163,175`.
- Other live feed sizes (curl, 2026-10-04):
  - Lex Fridman 2,107,356 bytes
  - The Daily, Apple's `feedUrl` `feeds.simplecast.com/Sl5CSM3S`: 513,923 bytes (65 items)
  - The Daily, full archive `feeds.simplecast.com/54nAGcIl`: 20,279,571 bytes (2,996 items)
- `parse_feed` reads only `id`/`link`/`title`/`published`/`content`/`summary` — `backend/src/catchup/sources/feeds.py:63-87`. It does not read:
  - enclosures (audio URL, length)
  - `itunes:duration`
  - `podcast:transcript`
- On confirm, only entries from the last `CATCHUP_FIRST_ADD_DAYS` (7) days are `pending`, up to `CATCHUP_FIRST_ADD_MAX` (5) of them. All others are `baseline`.
  - Code: `backend/src/catchup/api/sources.py:101-116`; config `backend/src/catchup/config.py:32-33`.
  - For a 503-episode feed, at most 5 episodes are pending and the rest are stored as baseline.

### Text length limits on the summarization path
- `CATCHUP_MAX_ITEM_CHARS` defaults to 20000 — `backend/src/catchup/config.py:35`, `.env.example:11`.
- The runner passes it to `summarize_items` — `backend/src/catchup/digest/runner.py:134`.
- `_summarize` sends `content_text[:max_chars]` in a single `chat_json` call with `max_tokens=SUMMARY_MAX_TOKENS` (4096). There is one call per item and no chunking — `backend/src/catchup/digest/summarize.py:27-41`, `backend/src/catchup/llm/prompts.py:7`.
- The cut is a plain character slice. No marker tells the model or the user that text was dropped.
- At most 4 summary calls run concurrently — `summarize.py:57`.
- A provider error that is not 429/500/503 (for example a 400 for an oversized request) raises `ProviderError` without retry — `backend/src/catchup/llm/client.py:73-76`. `_summarize` turns it into `summary_unavailable` — `summarize.py:39-40`. This is from code reading; it was not tested against a provider.
- The summary prompt asks for 2–4 sentences whatever the input length — `prompts.py:24-36`. The spec says the same ("Summaries focus on substance").
- The stored `Item.content_text` is unbounded `Text`, so a full transcript can be stored — `backend/src/catchup/models.py:83`.
- `DigestRun` tracks `items_total` and `items_done` only. No token counts or cost are recorded — `models.py:105-111`. `chat_json` does not read the response's `usage` — `client.py:89-107`.

## Current Specs
- `source-management`: "Preview a source from a pasted URL"; "Explain unsupported and duplicate sources"; "Fetch user-supplied URLs safely"; "Identify CatchUp in outgoing requests"; "Honor rate limits when fetching".
- `content-collection`: "Record entries the first time they are seen"; "Keep article text for summarization" (fetch the linked article when the feed text is short); "Readable titles for untitled entries".
- `digest-generation`:
  - "Summaries focus on substance": an item without substantive content is described in one short sentence.
  - "Summarize items once…": an item whose summary could not be produced is shown as unavailable.
- `local-deployment`: requests come from the user's own machine.
- `source-management` "Fetch user-supplied URLs safely": fetches stop reading above a size limit (5 MB in code). Podcast feeds above that limit fail.
- `content-collection` "Keep article text for summarization": the feed text is kept, and a short feed text triggers an article fetch. It says nothing about transcripts or enclosures.
- `digest-generation`:
  - "Summaries focus on substance": summaries are 2–4 sentences, regardless of the input length.
  - "Work with reasoning models by default": output budgets must leave room for reasoning.
  - "Include every pending item": every pending item appears in the digest.

## External facts (verified 2026-10-04; live requests from this machine, residential IP)

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

**`<podcast:transcript>`** (spec: https://github.com/Podcastindex-org/podcast-namespace/blob/main/docs/tags/transcript.md and `docs/examples/transcripts/transcripts.md`, fetched 2026-10-04)
- The namespace URI is `https://podcastindex.org/namespace/1.0`.
- The tag sits inside `<item>`, and an item may carry several: "Multiple tags can be present for multiple transcript formats."
- Attributes:
  - `url` (required)
  - `type` (required MIME type): `text/plain`, `text/html`, `text/vtt`, `application/json`, `application/x-subrip`
  - `language` (optional; defaults to the feed's `<language>`)
  - `rel` (optional; `rel="captions"` marks closed captions with time codes)
- The spec labels WebVTT and HTML "Recommended", and JSON and SRT "In use". It names WebVTT as the format to choose if only one is supported. WebVTT `<v Speaker>` voice tags carry speaker names.
- The JSON schema is `{"version":"1.0.0","segments":[{"speaker","startTime","endTime","body"}]}`. Segments may hold single words.
- HTML uses `<cite>` for the speaker, `<time>`, and `<p>`.

**Podcast transcripts in real feeds** (live, 2026-10-04)

| Feed | Size / items | Transcript types per episode | Episodes with a transcript | Transcript host | Latest-episode sample |
|---|---|---|---|---|---|
| https://podnews.net/rss | 2.3 MB / 151 | `text/vtt`, `rel=captions` | 150/151 | podnews.net | VTT 7,272 chars, 274 s |
| https://feeds.buzzsprout.com/1.rss | 42 KB / 11 | html, json, x-subrip, vtt | 11/11 | www.buzzsprout.com | 2,144 s. VTT 53,629; SRT 62,206; JSON 522,068 (word-level); HTML 308,944 (a whole web page) |
| https://feeds.transistor.fm/build-your-saas | 1.85 MB / 163 | vtt, srt, json, text/plain, text/html | 163/163 | share.transistor.fm | 2,486 s. txt 37,764; VTT 41,812; JSON 52,126 (`startTime` as strings) |
| https://mp3s.nashownotes.com/pc20rss.xml | 1.73 MB / 206 | one `application/srt` | 206/206 | same host | SRT 116,334 chars, 5,385 s; served as `application/octet-stream` |
| https://feeds.captivate.fm/designing-successful-startups/ | 1.41 MB / 121 | json, `application/srt`, html (some episodes html only) | 113/121 | transcripts.captivate.fm | 58:06. JSON 498,089 (word-level); SRT 79,985 |
| https://www.spreaker.com/show/7145406/episodes/feed | 173 KB / 38 | srt, text/plain, vtt (`language="en"`) | 29/38 | transcription.spreaker.com | 1,038 s. txt 16,434; VTT 27,853 |

- **Out-of-spec values.** `application/srt` is used in the wild but is not in the spec.
- **Namespace URI.** The Podcasting 2.0 feed declares the namespace as `https://github.com/Podcastindex-org/podcast-namespace/blob/main/docs/1.0.md`. A namespace-aware parser using the canonical URI found 0 of its 206 transcripts. 112 of the 113 feeds sampled used the canonical URI.
- **Other hosts.**
  - Libsyn (`feeds.libsyn.com/364304/rss`): 57 of 100 items carry SRT. One SRT was 7,240 characters for an 18:27 episode, which may be partial.
  - Podbean (one show): older items carry transcripts; the latest 10 do not.
- **Transcript host.** Transcripts are often served from a different host than the feed.
- **Size per minute.** Plain-text transcripts run about 900–950 characters per audio minute. VTT/SRT add 10–60% for timing lines. Word-level JSON is up to about 10× larger.
- **Duration format.** `itunes:duration` appears as seconds (`2486`) or `HH:MM:SS`/`MM:SS` (`58:06`).
- **Feeds without the tag.** Lex Fridman, The Vergecast, The Daily, Planet Money, and Self-Hosted have no `<podcast:transcript>` tags.
  - Their median show notes (last 10 items) run about 1.1k–4.2k characters.
  - Lex Fridman links an HTML transcript page inside the description text (for example `lexfridman.com/dhh-2-transcript`), not through the tag.

**feedparser and transcripts** (feedparser 6.0.14, the latest on PyPI, uploaded 2026-07-30; live, 2026-10-04)
- A transcript appears as `entry.podcast_transcript`, a single dict (`url`, `type`, optional `rel`/`language`).
- **Only the last tag of an item is kept.** For Buzzsprout's first item the raw XML has 4 tags (html, json, x-subrip, vtt), and feedparser returned only the vtt one (re-checked by Claude). For Transistor (vtt, srt, json, txt, html) it returned only html.
- It still finds the tag in the Podcasting 2.0 feed with the non-canonical namespace URI.
- Other fields:
  - `enclosures` is `[{'href', 'type': 'audio/mpeg', 'length'}]`
  - `itunes_duration` is the raw string
  - `content` is a list of `{type, value}` (Podnews: one text/html of 14,180 chars)

**iTunes Lookup API** (https://performance-partners.apple.com/search-api; live, 2026-10-04)
- **Show lookup.** `https://itunes.apple.com/lookup?id=1434243584&entity=podcast` returned `resultCount: 1` with `feedUrl: https://lexfridman.com/feed/podcast/`, without authentication.
  - Other fields: `collectionName`, `artistName`, `collectionViewUrl`, artwork URLs, `trackCount`, `releaseDate`, `primaryGenreName`.
  - The response is `content-type: text/javascript` with `cache-control: max-age=73264`.
- **Episodes.** `lookup?id=<showId>&entity=podcastEpisode&limit=1..200` returns the show plus episodes. Episode fields include `trackId`, `episodeGuid` (matches the RSS guid), `episodeUrl` (audio), `trackTimeMillis`, and `closedCaptioning`.
- **Episode IDs.** Looking up an episode ID (`?id=<episodeId>`) returned 0 results with and without `entity`.
- **URL shapes.**
  - Show: `https://podcasts.apple.com/{cc}/podcast/{slug}/id{showId}`
  - Episode: `https://podcasts.apple.com/{cc}/podcast/{episode-slug}/id{showId}?i={episodeId}` (the path ID is the show)
- **Rate limit.** The API "is limited to approximately 20 calls per minute (subject to change)".
- **RSS on Apple pages.** The show page (602 KB HTML) has no `application/rss+xml` link. An episode page embeds `"feedUrl"` in inline JSON, which is undocumented.
- **Archive versus Apple's `feedUrl`.** For The Daily, Apple's `feedUrl` (`Sl5CSM3S`, 65 items, 514 KB) differs from the 20 MB full-archive feed (`54nAGcIl`).

**Transcript adoption**
- Podcast Index daily counts (https://stats.podcastindex.org/daily_counts.json, 2026-10-04): `episodesWithTranscripts` 7,016,467 of `episodeCountTotal` 167,887,194, or 4.2%. The `feedsWithTranscripts` field equals the episode count and exceeds the total feed count, so it is unusable.
- A June 2026 report (https://chainofthought.show/reports/state-of-ai-podcast-feeds-2026/; 8 AI podcasts, 2,148 items) found 8.8% of episodes tagged, with 5 of 8 shows at zero.
- A sample of 107 feeds found through iTunes search (biased toward shows about podcasting; 24,305 episodes) gave these shares:
  - 43% of feeds had at least one transcript
  - 11.5% of all episodes had one
  - 34.2% of each feed's latest 5 episodes had one

**Model limits: DeepSeek** (https://api-docs.deepseek.com/quick_start/pricing and `/quick_start/token_usage`, fetched 2026-10-04)
- CatchUp docs name `deepseek-flash` as the tested model.
  - `deepseek-flash` (DeepSeek-V4.1-Flash): 1M context, maximum output 384K, thinking mode on by default.
  - Price per 1M tokens: input $0.15 off-peak / $0.30 peak (cache miss); output $0.60 / $1.20.
- `deepseek-v4-pro`: 1M context, maximum output 384K. Price: input $0.66 / $1.32; output $1.98 / $3.96.
- The docs give approximate ratios: 1 English character ≈ 0.3 token, 1 Chinese character ≈ 0.6 token. An offline tokenizer (`deepseek_v4_tokenizer.zip`, 1.9 MB) exists. It was not used; the user chose estimates.

**Long-transcript estimates** (from the DeepSeek ratios above; no model calls made)
- The 3.6-hour sample `s7d2d8FhevU` (169,961 characters, English, 787 characters per minute):

  | | Single call | Chunks of at most 20,000 characters |
  |---|---|---|
  | Input tokens | ≈ 51,000 (≈ 5% of a 1M context) | 9 calls with the same total input (≈ 51,000) plus per-call prompt overhead, then 1 combining call |
  | Output budget at `SUMMARY_MAX_TOKENS` (4096) | ≤ 4,096 | ≤ 40,960 (10 calls) |
  | Upper-bound cost at peak `deepseek-flash` prices | ≈ $0.015 input + ≤ $0.005 output | ≈ $0.015 input + ≤ $0.049 output |
  | Text the model sees, at today's 20,000-character cut | 11.8% | — |

- A Chinese episode of the same length, assuming about 250 characters per minute (an assumption, not measured): ≈ 54,000 characters, ≈ 32,000 tokens.
- A 1-hour English episode at 900–950 characters per minute: ≈ 55,000 characters, ≈ 17,000 tokens by the 0.3 ratio.
- Other OpenAI-compatible providers or local models may have much smaller contexts. Their limits were not checked.

**Speech-to-text when no transcript exists** (context; not a committed requirement — `docs/handoff.md:55`)
- **Terms.**
  - YouTube's Terms of Service prohibit to "download … any part of the Service or any Content" unless the Service expressly authorizes it or YouTube grants prior written permission (https://www.youtube.com/t/terms, fetched 2026-10-04).
  - Podcast audio is published as RSS enclosures for download. Enclosure URLs are often tracking redirects, for example `dts.podtrac.com/redirect.mp3/...`.
- **yt-dlp media downloads.** The PO Token Guide (https://github.com/yt-dlp/yt-dlp/wiki/PO-Token-Guide, fetched 2026-10-04) says most clients need a PO token for media (GVS) requests. The exceptions it lists "at this time" are `web_safari` (HLS), `android_vr`, and `web_embedded`.
- **Transcription APIs.**
  - OpenAI: files up to 25 MB, formats mp3/mp4/mpeg/mpga/m4a/wav/webm; longer audio must be split (https://developers.openai.com/api/docs/guides/speech-to-text). Prices from a third-party summary (https://costgoat.com/pricing/openai-transcription), not the official page: gpt-4o-mini-transcribe $0.003/min, gpt-4o-transcribe and whisper-1 $0.006/min.
  - Groq (https://console.groq.com/docs/speech-to-text): `whisper-large-v3-turbo` $0.04/hour, `whisper-large-v3` $0.111/hour. Limits are 25 MB (free) or 100 MB (dev), with a 10-second minimum bill. The endpoint is OpenAI-compatible (`/openai/v1/audio/transcriptions`).
  - The 3.6-hour sample at these rates: ≈ $0.65 (gpt-4o-mini-transcribe), ≈ $1.30 (gpt-4o-transcribe), ≈ $0.14 (Groq turbo).
- **This machine.** Apple M4, 32 GB, ffmpeg 8.1.2, yt-dlp 2026.07.04 installed (latest 2026.08.19). The Hugging Face cache holds `whisper-large-v3` and `whisper-medium` gguf models (`handy-computer`). No Whisper runtime is installed.
- **Docker.** Docker on macOS runs a Linux VM without Apple GPU access. This is a known platform limitation, not tested here. Transcription inside the CatchUp container on a Mac would run on the CPU.
- No audio was downloaded or transcribed in this research.

## Code References
- `backend/src/catchup/sources/discovery.py:50-99` — declared-feed discovery (finds YouTube channel RSS)
- `backend/src/catchup/sources/feeds.py:63-87` — entry identity, link, text
- `backend/src/catchup/collection.py:14-29` — `article_text` (fetches the watch page for short descriptions)
- `backend/src/catchup/api/sources.py:116-125` — confirm-time first-add and article text
- `backend/src/catchup/models.py:83-87,153` — `content_text`, `content_origin`, `state`, `summary_unavailable`
- `backend/src/catchup/llm/prompts.py:24-36` — generic summary prompt
- `frontend/src/pages/DigestView.tsx:45-51`, `frontend/src/pages/Sources.tsx:107-112` — item and preview display
- `backend/src/catchup/net/safe_fetch.py:18,163,175` — 5 MB response limit and its error
- `backend/src/catchup/api/sources.py:101-116` — first-add window (7 days, at most 5 pending)
- `backend/src/catchup/config.py:32-35` — `first_add_days`, `first_add_max`, `max_item_chars`
- `backend/src/catchup/digest/summarize.py:27-41,57` — per-item character cut, single call, 4 workers
- `backend/src/catchup/digest/runner.py:134` — passes `max_item_chars`
- `backend/src/catchup/llm/client.py:73-76,89-107` — non-retried provider errors; `chat_json` ignores `usage`
- `backend/src/catchup/models.py:105-111` — `DigestRun` progress counters, no token fields

## Related History
- 2026-10-01 source feasibility research: YouTube RSS flaky, transcript library stale, cloud IPs blocked (`docs/process/ai-usage-log.md`).
- D-011 (local deployment only) makes residential-IP behavior the relevant case.
- Issue #6 was created 2026-10-04; it received the third-party comment and the maintainer note the same day.
- 2026-10-04: the user decided to merge #5 and #6 into one change (`add-youtube-sources` renamed to `add-podcast-and-video-sources`). The user asked that long-transcript truncation be handled in this change, and asked whether speech-to-text (their Bilibili workflow) could be used for YouTube.
