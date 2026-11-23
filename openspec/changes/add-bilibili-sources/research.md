# Research: Bilibili uploaders as a source (#40)

- Date: 2026-11-22
- Query: How does CatchUp handle YouTube channels and podcasts today, where are source kinds listed, and how do discovery, preview and confirm work? What are the external facts about following a Bilibili uploader: ways to list an uploader's videos, subtitle availability, risk control and rate limits, and the terms of Bilibili, RSSHub and any other service involved?
- Git ref: `add-bilibili-sources` @ 795c5e7 (same as `main`)

## Summary

CatchUp follows RSS and Atom feeds, Apple Podcasts shows (resolved to their feed), YouTube channels (through the channel feed the page declares), X accounts (through the X API) and pages saved from the browser. A source's kind is a free-text column (`feed`, `podcast`, `youtube`, `capture`, `x`); the feed-based kinds are derived from the parsed feed on every check, and `x` and `capture` are set when the source is created. Videos and episodes are summarized only from transcripts (D-013): YouTube captions are fetched with `youtube-transcript-api` only when the user turns on "Fetch captions locally", one video at a time after all checks, at most 20 per run, and items without a transcript appear under Creator updates with a reason. Nothing in the code handles Bilibili. Bilibili publishes no feeds. Open-source tools list an uploader's videos through Bilibili's web API (`/x/space/wbi/arc/search`, signed with WBI, with a visitor cookie), and both yt-dlp and RSSHub say subtitles are returned only to a logged-in session. RSSHub's Bilibili route adds two fallbacks: an unsigned search endpoint, then a headless browser. Bilibili's user agreement (updated 2025-04-30) forbids obtaining the platform's content or data with any automated program without prior written permission, "for any reason". In January 2026 Bilibili's lawyers made the main community documentation of these APIs shut down.

## Detailed Findings

### Source kinds: where they are defined and listed

- The `sources.kind` column is `String(16)` with default `feed`; there is no check constraint on its values — `backend/src/catchup/models.py:87`. It was added in migration `0002_transcripts.py:15`. Migrations run up to `0008_run_progress.py`. A migration that adds a kind-specific table follows the X pattern (`0007_x_accounts.py`, table `x_accounts` keyed by `source_id`, `models.py:93-102`).
- Feed-based kinds are derived from the parsed feed: `youtube` when the feed URL is `https://(www.|m.)youtube.com/feeds/videos.xml`, `podcast` when more than half of the entries carry audio enclosures, otherwise `feed` — `backend/src/catchup/sources/feeds.py:289-295,357-366`.
- A source saved as `feed` is reclassified on each successful check when the parsed feed says otherwise — `backend/src/catchup/collection.py:96-97`.
- Kind lists in the backend:
  - Collection and runs: source checks cover every kind except `capture` and `x` (`backend/src/catchup/digest/runner.py:263-265`); X accounts are checked separately (`runner.py:266-269,311-329`); `sources_total` at start excludes only `capture` (`runner.py:204`), and the run then sets it to feed-based plus X sources (`runner.py:280`).
  - Selection: items are summarized when their transcript status is `found` or `text`, or when the status is empty and the kind is `feed`, `capture` or `x`; podcast and YouTube items otherwise wait, are deferred, or go to Creator updates — `runner.py:42-65`.
  - Context pass: only `feed`, `podcast`, `capture` and `x` items get linked pages; podcast items only once their transcript status is `text` — `backend/src/catchup/context/gather.py:113-125`.
  - Item creation sets `transcript_status` from the kind: `to_fetch` for every YouTube entry and for podcast entries with audio, `text` for other podcast entries, empty otherwise — `collection.py:136-138`, `backend/src/catchup/api/sources.py:243-245`.
- Kind lists in the frontend:
  - `SourceKind = 'feed' | 'podcast' | 'youtube' | 'capture' | 'x'` with the visible names "Website feed", "Podcast", "YouTube channel", "Saved from browser", "X account" — `frontend/src/components/ui.tsx:43-53`.
  - Icons per kind — `frontend/src/components/Icon.tsx:1-10`.
  - Transcript reasons, including "Blocked by YouTube" — `ui.tsx:57-62`.
  - Preview "method" line per kind, and the link to Settings when YouTube captions are off — `frontend/src/pages/Sources.tsx:66-82`.
  - Sources page lede, examples and rail ("YouTube channels — captions are opt-in in Settings") — `Sources.tsx:265,305-306,335-338`.
  - Home rail counts per kind (podcasts, YouTube, websites, X accounts) and the note that podcasts and videos are summarized only from transcripts or captions — `frontend/src/pages/Home.tsx:328-336`.
- Kind lists in the extension: the popup's "Follow this site" preview names `feed`, `podcast`, `youtube` and `x` and falls back to the raw kind string for anything else — `extension/src/popup.ts:270-282`. The only host-specific extractor is X (`extension/src/extract/x.ts:4`); the generic page extractor runs on any other site (`extension/src/extract/page.ts`).

### Discovery, preview and confirm

- `POST /api/sources/preview` first checks for an X address (`x_username`, `backend/src/catchup/sources/x_accounts.py:28-40`): X hosts are recognized before any discovery and read only through the X API — `api/sources.py:165-169`. Everything else goes to `discover()` — `api/sources.py:170-194`.
- `discover()` (`backend/src/catchup/sources/discovery.py:59-170`):
  - Apple Podcasts show pages are resolved through `itunes.apple.com/lookup` (`:61-74`).
  - Otherwise it fetches the URL, uses it if it parses as a feed (`:97-109`), else reads `<link rel="alternate">` feeds the HTML declares (`:111-140`), else tries up to 8 common feed paths on the same origin (`:51-56,146-167`), and finally reports "No supported feed was found at this URL." (`:170`). A pasted page that answers an HTTP error still gets the probes (`:93-95,168-169`).
  - YouTube channels are found because the channel page declares its feed; there is no YouTube-specific code in discovery.
- The preview returns the feed title, feed and site URLs, kind, whether captions are on, and five recent entries — `api/sources.py:183-194`.
- Confirm re-reads the cached preview response, saves the source with `kind=feed.kind`, records every entry, and marks as pending only entries published within `first_add_days` (most recent `first_add_max`); YouTube Shorts are skipped when "Skip Shorts" is on — `api/sources.py:197-279`.
- A source is identified by its `feed_url` (unique) — `models.py:85`, duplicates are reported — `api/sources.py:47-56,175-177,215-217`.
- Every request goes through `safe_fetch` (public-address check, timeouts, size limits, redirects re-checked) with a User-Agent naming CatchUp and the project URL — `backend/src/catchup/net/safe_fetch.py:44-51`. Per-host spacing of 1 s within a run — `backend/src/catchup/net/host_spacing.py:9-20`.

### YouTube channels

- Collection: a new YouTube entry gets `transcript_status = "to_fetch"` and keeps the feed description as `content_text`, without fetching the watch page — `collection.py:136-142`. Shorts (`/shorts/` links, `feeds.py:238-239`) are recorded as `baseline` when "Skip Shorts" is on — `collection.py:143-145`.
- Caption pass (`runner.py:68-124`, called after all checks at `runner.py:341-344`):
  - oldest recorded video first, one at a time;
  - when captions are off, the item becomes `captions_off` (Creator updates reason) — `:95-96`;
  - at most `captions_per_run` (default 20, `CATCHUP_CAPTIONS_PER_RUN`) — `:97-101`, `backend/src/catchup/config.py:55,79`;
  - after a "blocked" result no further caption requests in that run — `:113-114`;
  - the video id comes from the feed entry id `yt:video:<id>` — `:102-103`.
- Caption fetching (`backend/src/catchup/transcripts/youtube.py:97-132`) uses `youtube-transcript-api` (pinned `>=1.2.4,<1.3`, `backend/pyproject.toml`), through a `requests` session that applies CatchUp's User-Agent and the per-host spacer (`youtube.py:20-34`). It picks the original-language track from player metadata (`:37-81`), and maps library errors to statuses `caption_wait`, `unplayable_wait`, `blocked`, `captions_failed` (`:121-132`).
- Waits: `caption_wait_hours` (default 24) and `transcript_wait_days` (default 7) — `config.py:53-54,77-78`; expiry in `select_pending` (`runner.py:53-62`).
- Settings: `app_settings.youtube_captions` (default off) and `youtube_skip_shorts` (default on) — `models.py:58-66`; API `api/settings.py:40-41,281-301`; Settings group 3 "YouTube" with the risk note about YouTube's Terms of Service — `frontend/src/pages/Settings.tsx:398-406`. The per-run copy is `TranscriptContext` — `backend/src/catchup/transcripts/context.py:9-16`.
- README section on YouTube captions and the ToS warning — `README.md:568-578`.

### Podcasts

- Episodes (entries with an audio enclosure) are summarized only from transcripts the feed publishes (`<podcast:transcript>`), fetched during the check — `collection.py:36-52,157-159`; formats VTT, SRT, podcast-namespace JSON (`{"segments": [{"body": ...}]}`), HTML and plain text — `backend/src/catchup/transcripts/convert.py:54-106`.
- Episodes without a transcript wait up to 7 days, then go to Creator updates — `runner.py:53-57`.

### Creator updates and the digest view

- Items whose transcript status is one of `captions_off`, `no_captions`, `blocked`, `captions_failed`, `no_transcript` become Creator updates, grouped by source — `runner.py:38,51-52`, `backend/src/catchup/api/digests.py:84-95`.
- The digest view explains them as "listed without a summary because no transcript or captions were available" — `frontend/src/components/DigestArticle.tsx:106`.
- Images chosen by the summary are shown with `referrerPolicy="no-referrer"` — `DigestArticle.tsx:43-44`.

### Website feeds: what would happen to a Bilibili feed added as a plain feed

These are facts about the existing code paths; no Bilibili request was made.

- A feed whose URL is not a YouTube feed and whose entries carry no audio is kind `feed` — `feeds.py:289-295`.
- Its entries are summarized from the feed description, and when the description is shorter than `short_text_chars` (default 500, `config.py:74`), CatchUp fetches the entry link to extract article text — `collection.py:55-73`. For a video feed the entry link is the video page.
- Images in the description (for example a cover image) become image candidates — `feeds.py:355`.
- Links in the description become related links for the context pass; the link filter skips YouTube watch pages, `youtu.be`, Vimeo videos and X, but has no rule for `bilibili.com` — `backend/src/catchup/context/links.py:37-45`.

### Tests that cover the kinds today (for orientation)

- Backend: `backend/tests/test_feeds.py`, `test_discovery.py`, `test_sources_api.py`, `test_x_sources_api.py`, `test_feed_transcripts.py`, `test_transcript_convert.py`, `test_caption_pass.py`, `test_youtube_captions.py`, `test_youtube_shorts.py`.
- Frontend: `frontend/src/pages/Sources.test.tsx`, `Settings.test.tsx`, `Home.test.tsx`, `components/ui.test.tsx`. Extension: `extension/src/test/popup.test.ts`.

### External: ways to list an uploader's videos

Read from open-source code on GitHub on 2026-11-22. No request was made to Bilibili from this machine.

- **No official feed.** Bilibili pages declare no RSS or Atom feed (issue #40, observed 2026-10-17).
- **No official API for other uploaders.** The Bilibili Open Platform gives developers API access for accounts linked to them ("关联UP主", accounts the developer owns or is authorized to operate), for example to publish videos in bulk; data may be read only within what the linked uploader agreed to (developer agreement, sections 一.1, 一.4, 四.2; see the terms section below).
- **Web API used by open-source tools:**
  - yt-dlp's `BilibiliSpaceVideoIE` lists `space.bilibili.com/<mid>/video` through `https://api.bilibili.com/x/space/wbi/arc/search` with a WBI signature — https://github.com/yt-dlp/yt-dlp/blob/master/yt_dlp/extractor/bilibili.py (lines 1337-1416 at the time of reading). WBI keys come from `/x/web-interface/nav` and are cached 30 s (lines 52, 134-157); the signature is an MD5 over the sorted query plus a mixed key (lines 159-166).
  - RSSHub's route `/bilibili/user/video/:uid` (radar rule `space.bilibili.com/:uid`) uses the same endpoint with a WBI signature and a visitor cookie, retries a `-352` answer up to 3 times, then falls back to `/x/series/recArchivesByKeywords` (no signature), then to a headless browser (Playwright) that opens a video page and captures the list request — https://github.com/DIYgod/RSSHub/blob/master/lib/routes/bilibili/video.ts. The route declares `requirePuppeteer: true`.
  - The visitor cookie (`buvid3`, `buvid4`, `bili_ticket` and generated values) is built from `/x/frontend/finger/spi` and a ticket endpoint — https://github.com/DIYgod/RSSHub/blob/master/lib/routes/bilibili/cache.ts.
- **Risk control, as these tools describe it:**
  - `-352`: the API's risk-control rejection. RSSHub's comment says that from Cloudflare Workers it "rejects requests one by one with -352 and lets roughly a third through" (`video.ts`). yt-dlp reports "Request is rejected by server (352)".
  - HTTP `412`: yt-dlp reports "Request is blocked by server (412), please wait and try later". RSSHub's comments say the space page and new-visitor-cookie endpoints answer plain requests with a 412 "proof-of-work challenge" (`video.ts`, `cache.ts`).
  - `-401` is also reported as a block by yt-dlp.
  - RSSHub can be given logged-in cookies per account (`BILIBILI_COOKIE_<uid>`) and `dm_img` parameters (`BILIBILI_DM_IMG_LIST`, `BILIBILI_DM_IMG_INTER`) — https://github.com/DIYgod/RSSHub/blob/master/lib/config.ts (lines 94-97).
- **Rate limits.** Bilibili publishes no rate limits for these endpoints. RSSHub limits its own subtitle requests to 5 per second (`cache.ts`). RSSHub's demo instance caches for 120 minutes (FAQ). A third-party claim of about 200 requests per IP per hour on rsshub.app could not be confirmed in official documentation.
- **Maintenance signal.** Both tools change this code often (RSSHub's repository was last pushed 2026-11-22), and RSSHub keeps three fallbacks for one list request.

### External: subtitles

- Subtitles are listed by `https://api.bilibili.com/x/player/wbi/v2?bvid=<bvid>&cid=<cid>` (yt-dlp lines 255-276; RSSHub `cache.ts`), after looking up the video's `cid` (`/x/player/pagelist` or `/x/web-interface/view`). Each subtitle is a JSON file `{"body": [{"from", "to", "content"}, ...]}` that both tools convert to SRT.
- **Login.** yt-dlp warns "Subtitles are only available when logged in" when the response sets `need_login_subtitle`, treats a session as logged in only with a `SESSDATA` cookie, and its tests note "video has subtitles, which requires login" and "login required for CC subtitle" (lines 56-57, 267-269, 671-692). RSSHub sends either a configured (logged-in) cookie or a visitor cookie; its Cloudflare Workers deployment skips subtitles entirely (`cache.ts`). Whether a visitor cookie gets any subtitle list today was not checked (see "Facts that need a live check").
- **CC and AI subtitles.** Uploader-provided (CC) and Bilibili's automatic (AI) subtitles appear in the same list with a language code (`lan`) and a display name (`lan_doc`); the tools do not distinguish them further.
- **RSSHub output.** RSSHub attaches subtitles only in JSON Feed output (`?format=json`), as `data:` URLs with `text/srt` content, and not when `BILIBILI_EXCLUDE_SUBTITLES` is set (`video.ts`, `cache.ts`). RSS output carries the description only: an HTML block with an embedded player (unless `embed` is turned off), the cover image and the description text.
- **CatchUp today cannot read either form:** feedparser 6.0.14 (`backend/uv.lock:561-562`) has only XML parsers (`feedparser/parsers/loose.py`, `strict.py`), so a JSON Feed does not parse (`parse_feed` raises `FeedParseError` when `parsed.version` is empty, `feeds.py:299-301`); `safe_fetch` fetches only HTTP(S) URLs; and the JSON transcript converter reads only the podcast-namespace `segments` shape (`convert.py:54-70`).

### External: legal signal

- The most complete community documentation of Bilibili's web APIs, `SocialSisterYi/bilibili-API-collect`, is archived and emptied. Its README says that on 2026-01-28 the maintainer received a lawyer's letter from a law firm acting for Bilibili, alleging that systematically collecting and publishing documentation of Bilibili's non-public API interfaces, their calling logic, parameters, access control and security authentication, as documents and code examples, infringed Bilibili's rights (translated from Chinese) — https://github.com/SocialSisterYi/bilibili-API-collect (README, read 2026-11-22).
- yt-dlp (Unlicense) and RSSHub (AGPL-3.0) still publish working code for these endpoints.

### External: terms on storage, derived data, deletion, and exceptions

Read on 2026-11-22. All Bilibili texts are in Chinese; the quotes below are translated from Chinese, and the original wording is kept in the session notes.

**Bilibili user agreement** (《哔哩哔哩弹幕网用户使用协议》, https://www.bilibili.com/protocal/licence.html). Updated 2025-04-30, effective 2025-05-07. It covers registered users and anyone who uses Bilibili's services without an account (section 1.5).

- **Local storage.** Not addressed as such. Obtaining the content in the first place is prohibited when done by software: section 5.6(3) prohibits, "without Bilibili's prior express written permission", obtaining "the platform's services, content or data" "by any means (including but not limited to robot software, spider software, crawler software or any other automated program, script or software) and for any reason", by oneself or through others (translated from Chinese). Section 1.2 limits the services to use within Bilibili's platforms and says that separating the services from the platform by unlawful means such as malicious cracking is not a service Bilibili provides (translated from Chinese).
- **Derived results.** Not addressed for summaries of videos. Content belongs to its uploaders, who guarantee they hold the rights, and Bilibili may display it (section 4.2). Users may not modify, adapt or translate the software, technology and materials of Bilibili's services, "or create derivative works related to them" (section 8.2). Bilibili's self-produced and exclusively licensed content may not be reposted, spread or offered for viewing without permission (section 8.5) (translated from Chinese).
- **After stopping.** Not addressed for the user. The termination and account sections (10.5, 11) cover Bilibili deleting or keeping the user's own data.
- **Personal or research exceptions.** None. Section 1.2 says the services are for users' "non-commercial use" only; that is a limit, not an exception. Section 5.6(3) applies "for any reason" (translated from Chinese).

**Bilibili Open Platform developer service agreement** (《哔哩哔哩开放平台开发者服务协议》, https://openhome.bilibili.com/agreement/developer-service). Updated 2025-05-28, effective 2025-06-04. It applies only to registered developers and their linked uploader accounts.

- **Local storage.** Allowed within limits. Data may be processed (collected, stored, used, deleted) only for the agreement's purposes (section 七.4). It may be kept no longer than needed for those purposes (section 七.7). Data may be read and used only within what the linked uploader explicitly agreed to (section 四.2) (translated from Chinese).
- **Derived results.** Not addressed.
- **After stopping.** Everything must be deleted. On suspension or termination the developer must "immediately delete" user data and operating data obtained or produced through the platform, including copies and backups, and not use them again (section 十.4(1)). Data must also be returned and destroyed when Bilibili or the rights holder asks, and deleted beyond recovery when a user asks (section 四, items 4-5) (translated from Chinese).
- **Personal or research exceptions.** None. Section 五.4 repeats the ban on obtaining the service or its data with robot, spider or crawler software without written consent (translated from Chinese).

**RSSHub software** (https://github.com/DIYgod/RSSHub). License AGPL-3.0 (repository metadata, read 2026-11-22). The license governs the software, not the data: it allows running RSSHub, and requires offering the source of a modified version to users who interact with it over a network. It says nothing about storing, deriving or deleting Bilibili content; those questions fall back to Bilibili's terms above.

- Local storage: not addressed. Derived results: not addressed. After stopping: not addressed. Personal or research exceptions: not addressed.

**RSSHub demo and public instances** (https://docs.rsshub.app/guide/faqs, updated 2026-09-29; https://docs.rsshub.app/guide/instances, updated 2026-03-17). No terms of service, privacy policy or usage policy is published for `rsshub.app` or the listed community instances. The FAQ calls `rsshub.app` a demo instance that is "free to use", runs the latest build, caches for 120 minutes, and can be unreliable for routes with strict anti-crawling; the instances page encourages users to host their own instance.

- Local storage: not addressed. Derived results: not addressed. After stopping: not addressed. Personal or research exceptions: not addressed.

**yt-dlp** (https://github.com/yt-dlp/yt-dlp). The Unlicense (public domain dedication). It was read only as a reference for how the endpoints work; it is not a data source, and no option above uses it.

## Code References

- `backend/src/catchup/models.py:58-66,79-102,105-135` — app settings (YouTube options), Source (kind), XAccount, Item (transcript status, image candidates).
- `backend/src/catchup/sources/feeds.py:238-239,275-295,298-366` — Shorts, Feed kind, parse_feed and the YouTube feed host rule.
- `backend/src/catchup/sources/discovery.py:14-170` — discovery, Apple lookup, probes.
- `backend/src/catchup/sources/x_accounts.py:18-40` — host recognition before discovery.
- `backend/src/catchup/api/sources.py:165-279` — preview and confirm, kind-dependent transcript status.
- `backend/src/catchup/collection.py:36-175` — check_source, article_text, episode transcripts.
- `backend/src/catchup/digest/runner.py:38-124,195-210,247-344` — selection, caption pass, run start, checks.
- `backend/src/catchup/transcripts/youtube.py:1-132`, `transcripts/context.py:1-16`, `transcripts/convert.py:54-106` — caption fetching, per-run caption state, transcript conversion.
- `backend/src/catchup/context/gather.py:113-133`, `context/links.py:25-50` — context kinds and the link filter.
- `backend/src/catchup/net/safe_fetch.py:44-51`, `net/host_spacing.py:9-20` — User-Agent, spacing.
- `backend/src/catchup/config.py:49-83` — caption, wait and short-text settings.
- `backend/src/catchup/api/settings.py:40-41,281-301` — YouTube preferences API.
- `frontend/src/components/ui.tsx:43-62`, `Icon.tsx:1-10` — kind names, icons, reasons.
- `frontend/src/pages/Sources.tsx:66-90,265,305-306,335-338`, `Settings.tsx:339-441`, `Home.tsx:328-336` — preview method line, examples, Settings groups, Home rail.
- `frontend/src/components/DigestArticle.tsx:43-44,106` — images and Creator updates lede.
- `extension/src/popup.ts:270-282`, `extension/src/extract/x.ts:4` — popup kind labels, the only host-specific extractor.
- `backend/src/catchup/migrations/versions/0002_transcripts.py`, `0007_x_accounts.py`, `0008_run_progress.py` — kind column, kind-specific table pattern, latest migration.

## Current Specs

- `transcripts`:
  - "Recognize podcast and YouTube sources" (`openspec/specs/transcripts/spec.md:8-15`) names the three feed-based kinds and the two kinds that are never reclassified;
  - "Opt in to fetching YouTube captions locally" (`:100-109`): off by default, the description must state the conflict with YouTube's terms, no summaries from descriptions or watch pages;
  - "Limit and space caption requests" (`:153-155`), "Record why a transcript is unavailable" (`:168-176`, reasons including "blocked by YouTube"), "Skip YouTube Shorts by default" (`:190`).
- `source-management`:
  - "Preview a source from a pasted URL" (`:8-20`) lists the URL forms handled (feed, Apple Podcasts, HTML page, X account) and what the preview shows per kind;
  - "Explain unsupported and duplicate sources" (`:67-80`);
  - "Fetch user-supplied URLs safely" (`:128`) and "Identify CatchUp in outgoing requests" (`:155-158`): every request names CatchUp in its User-Agent.
- `content-collection`: "Check every source on each run", "Keep article text for summarization" (fetching the entry link for short entries), "Gather related context for website items".
- `digest-generation`: "Creator updates" (`:196-206`) lists the five reasons, including "blocked by YouTube".
- `user-interface`: "Sources show their kind and confirm deletion inline" (`:123-125`, names the five visible kinds); "Settings explain risk and keep secrets out of view" (`:134-138`, the groups Model provider, Digest, YouTube, browser extension, X accounts).
- `x-accounts`: "Recognize X account addresses" (`:8-15`) is the precedent for recognizing a host before discovery and for never requesting that host's pages.
- `browser-extension`: "Follow the current site from the browser" (the popup preview names kinds); "What the extension never does".

## Related History

- D-013 (`docs/process/decision-log.md:84-102`): podcasts and YouTube are summarized only from transcripts; summarizing show notes and descriptions was rejected "because it would claim to cover content that was not processed"; speech-to-text was not committed; downloading YouTube audio with yt-dlp was rejected under YouTube's terms.
- D-024 and D-025: the click-to-capture extension, and following X through the official X API with the user's own token.
- `docs/handoff.md` §4: logged-in content is for later, site by site; "do not upload session cookies for general-purpose login".
- The user's own Bilibili workflow used speech-to-text and a summary (`docs/process/ai-usage-log.md:419`); on 2026-10-17 the user asked whether Bilibili is supported, and the answer was that RSSHub is the only workaround (`ai-usage-log.md:956-964`), which opened #40.
- `docs/alpha-release.md:24` lists Bilibili (#40) as not started.

## Facts that need a live check (not done; each needs the user's approval)

1. What CatchUp's preview answers today for `https://space.bilibili.com/<mid>`: one page request plus up to 8 probes to `space.bilibili.com` (HTTP 412, or HTML without a feed).
2. Whether `/x/space/wbi/arc/search` and `/x/series/recArchivesByKeywords` answer this machine with a visitor cookie, and how often they return `-352` or 412.
3. Whether `/x/player/wbi/v2` lists any subtitles (CC or AI) without a logged-in cookie, and whether it sets `need_login_subtitle`.
4. Whether a self-hosted RSSHub answers `/bilibili/user/video/<uid>` from this machine, with and without its bundled browser. This needs the RSSHub Docker image, which is a download.
5. What `https://www.bilibili.com/robots.txt` and `https://api.bilibili.com/robots.txt` say.
