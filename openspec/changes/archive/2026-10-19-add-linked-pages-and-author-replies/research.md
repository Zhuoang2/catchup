# Research: Read linked pages and the author's replies in comments when summarizing an item

- Date: 2026-10-19
- Query: How does CatchUp gather the text of an item, fetch pages, run a digest, store items and summaries, and cite sources today, and what do the user's real sources expose, so that issue #48 can be proposed? #48 asks for two things. F7: open the links inside an entry, judge whether they relate to it, and summarize the related ones together with it. F8: read the post author's own replies in the post's comment section, starting with websites that have comment sections (X comes later, see #41). User decisions on #48: for F7 the implementer chooses the defaults (which links count, how many, the budget), and a user setting may later control the depth; F8 starts with websites that have comment sections.
- Git ref: main @ dba8ec8

## Summary
An item's text today is one plain-text string. `parse_feed` turns the entry HTML into text with `plain_text`, which drops every `href`. No inline link, entry author, or comment element is kept, although feedparser exposes `comments`, `wfw_commentrss`, `slash_comments`, `links`, and `author`. Only when that text is shorter than 500 characters does `article_text` fetch the item's own page through `safe_fetch` (public addresses only, 5 MiB, 30 s per fetch, 1 s spacing per host within a run) and replace the text with trafilatura's default extraction. That extraction carries no URLs, and it includes a page's comment text without the commenters' names; the unmerged #47 change rewrites the replacement rule. A run checks sources one at a time with these page fetches inline in the collecting stage. It then summarizes each item from its title and `content_text` only (4 workers, 4,096 output tokens, splitting by a context-window budget), groups the summaries, and records token totals per run; there is no per-item or per-run budget for fetches or tokens. Items, summaries, and digest snapshots carry one link per item, and the UI renders summaries as plain text without links. On the user's sources: Simon Willison's entries have a median of 8 links, about half of them `/tags/` links, 8 of 30 entries are short enough to trigger a page fetch, and the site has no comment section. The Verge's entries are truncated teasers with no comment elements; its pages were not fetched because of robots.txt. Terry Tao's WordPress feed exposes `comments`, `wfw:commentRss`, and `slash:comments`, each per-post comment feed returns the newest 10 comments with display names only, and the post HTML marks the author's comments with `bypostauthor` and `comment-author-teorth`.

## Detailed Findings

### 1. How an item's text is gathered today

**Feed parsing (`backend/src/catchup/sources/feeds.py`)**
- `parse_feed(response)` calls `feedparser.parse(response.content)` with the bytes only. No response headers or base URL are passed — `feeds.py:153-154`.
- The entry body is the first `content` element's value, else `summary` — `feeds.py:165-166`. For RSS this is `content:encoded` when present, else `description`; for Atom it is `<content>`, else `<summary>`.
- That HTML is turned into text by `plain_text(description)` — `feeds.py:167`.
  - `plain_text` uses an `HTMLParser` subclass, `_Text`, that keeps only `handle_data` fragments and joins them with single spaces — `feeds.py:87-99`.
  - Tag attributes, including every `href`, are dropped. Paragraph and line breaks are collapsed to single spaces — `feeds.py:99`.
- `FeedEntry` holds `identity_key`, `link`, `title`, `published_at`, `content_text`, `has_audio`, `transcripts` — `feeds.py:119-127`. There is no field for the entry's HTML, its inline links, its author, or any comment element.
- The entry `link` is the feed's `link` if it is an absolute http(s) URL with a host, else the feed URL — `feeds.py:169-174`.
- `Feed` holds `feed_url`, `site_url`, `title`, `entries`, `youtube_host`, `audio_share`; `shared_links` is the set of entry links that appear more than once — `feeds.py:130-150`. `site_url` is the channel `link`, else the feed URL's origin — `feeds.py:194`.
- Only one other piece of the raw XML is read: podcast `<podcast:transcript>` elements, through a separate lxml pass — `feeds.py:44-84`, `:157`.
- Observed with the pinned feedparser 6.0.14 (`backend/uv.lock:620-621`) on a local synthetic feed (2026-10-19):
  - The sanitized entry HTML keeps `<a href>` (scripts and `on*` attributes are removed). A relative `href` stays relative, because no base URL is given to `feedparser.parse`.
  - feedparser exposes `entry.links` (the Atom `<link>` list, including `rel="replies"` with `thr:count`), `entry.comments` (RSS `<comments>`), `entry.wfw_commentrss` (`wfw:commentRss`), `entry.slash_comments` (`slash:comments`), and `entry.author` (`dc:creator` or Atom `author`). CatchUp reads none of them; the code reads only `published_parsed`/`updated_parsed`, `content`, `summary`, `title`, `link`, `id`, `podcast_transcript`, and `enclosures` — `feeds.py:158-188`.
  - A search of `backend/src` for `href`, `comment`, `wfw`, `slash`, and `replies` finds only `sources/discovery.py:33-34` and `:117-118`, which read `<link rel="alternate">` feed hrefs from an HTML page during source preview.

**Article fallback (`backend/src/catchup/collection.py`)**
- `article_text(entry, fallback_links, threshold, *, spacer)` returns `(text, origin)` — `collection.py:39-54`:
  - feed text at least `threshold` characters long, or `entry.link` in `fallback_links` → `(entry.content_text, "feed")`, no fetch — `:41-42`;
  - otherwise `safe_fetch(entry.link, spacer=spacer)` with the default 5 MB limit — `:44`;
  - `FetchError` → feed text — `:45-46`;
  - `trafilatura.extract(response.content, url=response.url)` with default options; non-empty result → `(text.strip(), "article")`, replacing the feed text — `:48-50`;
  - empty extraction or any extractor exception → feed text — `:51-54`.
- trafilatura 2.3.0 defaults, read from `inspect.signature(trafilatura.extract)` on 2026-10-19: `output_format="txt"`, `include_links=False`, `include_images=False`, `include_tables=True`, `include_comments=True`, `with_metadata=False`.
  - So the extracted article text carries no URLs.
  - On a local synthetic WordPress-style page (article plus `ol.commentlist` with `li.comment ... bypostauthor`), default `extract` appended both comment bodies after the article text. The commenter names (`cite.fn`) were not in the output, so the text did not say who wrote which comment. With `include_comments=False` the comments were left out. With `include_links=True, output_format="markdown"` the inline link came out as `[link](https://github.com/x/y)`. For the same measurement on saved real WordPress pages, see External Facts (Terry Tao).
- `threshold` is `settings.short_text_chars`, default 500 — `config.py:57`. `fallback_links` is `{source.feed_url, feed.feed_url} | feed.shared_links` — `collection.py:83`.
- Callers:
  - run-time check, new non-transcript entries — `collection.py:110-113`;
  - run-time check, a pending text-only entry of a podcast source that is re-seen — `collection.py:94-104`;
  - source confirmation, only for entries marked `pending` (at most `first_add_max`, default 5, from the last `first_add_days`, default 7) — `api/sources.py:118-123`, `:141-145`.
  - Podcast episodes with audio and YouTube items never use it; they keep `(entry.content_text, "feed")` until a transcript replaces the text — `collection.py:107-113`, `:20-36`; `digest/runner.py:62-108`.
- `content_origin` values: `"feed"`, `"article"`, `"transcript"` — `collection.py:30`, `:42`, `:50`; `digest/runner.py:105`. Only `"transcript"` changes behavior (`digest/summarize.py:75`).
- `check_source` (`collection.py:57-142`) runs per source, in one transaction:
  - fetches the feed with `max_bytes=settings.max_feed_bytes` — `:62`;
  - for each unseen entry, calls `article_text` inline, so article fetches happen during the collecting stage, one after another — `:93-130`;
  - writes the `SourceCheck` row and commits only at the end — `:132-142`.

**In-flight change `keep-feed-text-when-extraction-misses` (#47, not merged)**
- Planned on main (`dba8ec8`). Implemented on branch `keep-feed-text-when-extraction-misses` (commits `0e0e087`, `80a9dff`, in a Droid worktree), touching `collection.py`, `test_collection.py`, `test_sources_api.py`.
- Its delta (`openspec/changes/keep-feed-text-when-extraction-misses/specs/content-collection/spec.md`) changes "Keep article text for summarization": the extracted text replaces the feed text only when it covers it (at least 60% of the feed's distinct words of 3+ characters, `design.md` D1). Otherwise the stored text is the feed text, a blank line, then the extracted text, with origin `"article"` (D2).
- Its proposal lists "Following the links inside an entry belongs to #48" as out of scope (`proposal.md`, "Out of scope").
- The trigger case is the Simon Willison entry `llm-tools-datasette 0.1.1` (18 Oct 2026), whose ~250-character feed text was replaced by a 310-character sidebar extraction (`proposal.md`, "Why").

### 2. Fetching limits and safety

**`safe_fetch` (`backend/src/catchup/net/safe_fetch.py:100-192`)**
- Signature: `safe_fetch(url, *, same_origin=None, budget=None, spacer=None, max_bytes=None)` — `:100-101`.
- Constants: `MAX_BYTES = 5 MiB`, `MAX_REDIRECTS = 5`, `FETCH_DEADLINE_SECONDS = 30` — `:18-20`.
- One `httpx.Client` per call, `follow_redirects=False`, `trust_env=False`, CatchUp User-Agent — `:113`. User-Agent: `CatchUp/<version> (+https://github.com/Zhuoang2/catchup[; contact])` — `:34-41`.
- Per hop, in order — `:115-128`:
  - wall-clock deadline check — `:107-111`, `:117`;
  - `same_origin` check: scheme and netloc must equal the given origin — `:119-120`;
  - `_check_address`: http/https only, a host, no userinfo; every `getaddrinfo` answer must be global and not private, loopback, link-local, reserved, multicast, or unspecified; NAT64 `64:ff9b::/96` is unwrapped first — `:72-97`;
  - `budget[0]` request counter decremented, error at 0 — `:122-125`;
  - `spacer.wait(current)` — `:126-127`.
- Timeouts per request: connect 5 s, read 15 s, write 5 s, pool 5 s, each capped by the remaining deadline — `:131-134`. The 30 s deadline covers the whole call, including redirects, a retry, and the body stream — `:105`, `:173`, `:179`.
- 429, or 503 with `Retry-After`: one retry if the delay is at most 10 s and fits the deadline; else `FetchError("rate_limited", ...)` — `:138-145`.
- Redirects: 301/302/303/307/308 with `Location`, joined to the current URL, each hop re-checked; more than 5 hops → error — `:146-158`.
- Size: `Content-Length` above the limit → error before reading; streamed body above the limit → error — `:160-178`.
- `raise_for_status()` turns any 4xx/5xx into `FetchError("fetch_failed", ..., status)` — `:159`, `:186-189`.
- The response has `url` (final URL), `content`, `content_type`, `status_code` — `:64-69`, `:180-183`. No content-type check is made inside `safe_fetch`.
- `same_origin` and `budget` are used only by feed discovery's common-path probes (`budget = [8]`) — `sources/discovery.py:145-154`.
- No code reads robots.txt. A search for "robots" in `backend/src`, `frontend/src`, `README.md`, `openspec/specs`, and the decision log finds nothing.

**Host spacing (`backend/src/catchup/net/host_spacing.py:9-27`)**
- `HostSpacer(min_interval=1.0)` keeps the last request time per lower-cased hostname, under a lock, and sleeps until 1 s has passed since the last request to that host — `:10-27`.
- A digest run creates one spacer — `digest/runner.py:199` — and passes it to every `check_source` call (feed, article, podcast transcript fetches) and, through `TranscriptContext`, to YouTube caption requests — `runner.py:200-209`; `transcripts/youtube.py:20-34`.
- Source confirmation creates its own spacer for its article fetches — `api/sources.py:131`, `:142`. Preview/discovery passes no spacer — `sources/discovery.py:83`, `:120`, `:152`.

**Rate-limit reporting**
- `is_rate_limited(check)`: HTTP 429, or 503 with the rate-limit message prefix — `net/rate_limit.py:7-10`. It is applied to source checks only (run detail and source list) — `digest/runner.py:417`, `api/sources.py:188`. An article fetch's `FetchError`, including `rate_limited`, is swallowed by `article_text` and leaves no record — `collection.py:45-46`.

**Feed cache (`backend/src/catchup/net/feed_cache.py:11-34`)**
- In-memory `FeedCache(ttl=600, max_entries=50)`, single-use `pop`, used only from preview to confirm — `:12`, `:29-34`; `main.py:42`; `api/sources.py:98`; `sources/discovery.py:77-78`.
- `put` skips responses larger than `MAX_BYTES` (5 MiB) — `:20-22`. Article pages are not cached.

**Instance settings that bound work (`backend/src/catchup/config.py:30-72`)**

| Setting | Env var | Default | Bounds |
|---|---|---|---|
| `first_add_days` | `CATCHUP_FIRST_ADD_DAYS` | 7 | lookback for entries marked new on confirm — `:55` |
| `first_add_max` | `CATCHUP_FIRST_ADD_MAX` | 5 | entries marked new on confirm — `:56` |
| `short_text_chars` | `CATCHUP_SHORT_TEXT_CHARS` | 500 | feed text length below which the article page is fetched — `:57` |
| `grouping_batch_chars` | `CATCHUP_GROUPING_BATCH_CHARS` | 200000 | grouping payload per call — `:58` |
| `max_feed_bytes` | `CATCHUP_MAX_FEED_BYTES` | 33554432 | feed document size — `:39`, `:59` |
| `transcript_wait_days` | `CATCHUP_TRANSCRIPT_WAIT_DAYS` | 7 | podcast hold — `:40`, `:60` |
| `caption_wait_hours` | `CATCHUP_CAPTION_WAIT_HOURS` | 24 | YouTube hold — `:41`, `:61` |
| `captions_per_run` | `CATCHUP_CAPTIONS_PER_RUN` | 20 | caption fetches per run — `:42`, `:62` |
| `long_item_chars` | `CATCHUP_LONG_ITEM_CHARS` | 20000 | transcript length for the overview + key points prompt — `:43`, `:63` |
| `single_call_chars` | `CATCHUP_SINGLE_CALL_CHARS` | unset | overrides the per-call text budget — `:44`, `:64` |
| `user_agent_contact` | `CATCHUP_USER_AGENT_CONTACT` | unset | appended to User-Agent — `:45`, `:70` |

- The first four use plain `int()`; the rest use `positive_env`, which rejects values ≤ 0 — `config.py:11-21`, `:55-64`. `test_core_flow.py:38` sets `short_text_chars=0`.
- Fixed in code, not configurable: 5 MiB non-feed size limit, 30 s per-fetch deadline, 5 redirects, 1 s host spacing, 4 summary workers (`digest/summarize.py:120`), `SUMMARY_MAX_TOKENS = 4096` (`llm/prompts.py:7`).
- There is no limit on the number of article fetches per source or per run, no total run deadline, and no limit on items per run (`digest-generation` "Include every pending item").
- User preferences live in `AppSettings` (`digest_language`, `youtube_captions`, `youtube_skip_shorts`) — `models.py:49-56` — and are read and written by `GET`/`PUT /api/settings/preferences` — `api/settings.py:35-38`, `:139-166`. The Settings page holds them in one `Preferences` type — `frontend/src/pages/Settings.tsx:8`, `:63-67`, `:106-107`. The runner reads them once at run start — `digest/runner.py:175-178`.

### 3. The digest run

**Stages (`backend/src/catchup/digest/runner.py:166-391`)**
- `queued` (created by `start_run`, `:125-137`) → `collecting` (`:198`) → `summarizing` (`:264`) → `grouping` (`:289`) → `succeeded` / `no_new_content` / `failed`. Active statuses: `ACTIVE` — `:30`.
- Before collecting, the model's context window is looked up once if not stored — `:184-197`.
- Collecting: each source is checked in order of id, one at a time — `:204-209`; then the YouTube caption pass — `:210`, `:62-108`.
- Item selection: pending items joined with their source, classified by `select_pending` — `:212-220`, `:36-59`. Summary inputs: `SummaryInput(item.id, item.title, item.content_text, item.summary, item.summary_language, item.content_origin)` — `:221-225`. Final per-source outcomes are written before any model call — `:230-251`.
- Summarizing: `call_budget = single_call_chars or max(2000, context_window - 4096 - 2000)` when the window is known, else 60,000 characters — `:282-284`. `record()` stores each summary on its `Item` with the run language and increments `items_done` — `:267-278`.
- Grouping uses `GroupItem(id, title, source_name, summary)` — `:290-297`.
- Snapshot and delivery happen in one transaction — `:301-377`.
- Errors: auth/balance → `failed` with "Check the model settings."; other `ModelError` → `failed`; unexpected errors are logged with the message replaced — `:378-391`.

**Progress reporting**
- `run_detail` returns `status`, `items_total`, `items_done`, `waiting_count`, `deferred_count`, token totals, `sources_total`, and `source_checks` — `runner.py:394-420`.
- The frontend polls `/api/digest-runs/{id}` every 1000 ms while the run is active — `frontend/src/pages/Home.tsx:160-175`. During `queued`/`collecting` it shows "Sources checked: n of N" from `source_checks.length` / `sources_total`; later "Items summarized: n of N" — `Home.tsx:61-70`. Because `check_source` writes its row at the end (`collection.py:132-142`), article fetches inside a source show no separate progress.

**Summarization (`backend/src/catchup/digest/summarize.py`, `backend/src/catchup/llm/prompts.py`)**
- Cache: an item with a stored summary in the current language is not summarized again — `summarize.py:114-119`.
- Four worker threads; results are recorded on the runner thread — `summarize.py:120-125`.
- What the model receives per item — `summarize.py:72-97`:
  - text within the budget: one call. `summary_messages` sends `Title: {title}\nContent:\n{text}` — `prompts.py:24-36`. A transcript longer than `long_item_chars` uses `long_transcript_messages` instead — `summarize.py:75-78`, `prompts.py:39-49`;
  - longer text: `split_parts` (blank lines, then lines, then whitespace, then a hard cut preferring sentence punctuation, nothing dropped) — `summarize.py:32-69`. Each part goes through `part_messages`, then the notes go through `combine_messages` — `summarize.py:80-92`, `prompts.py:52-68`.
  - The model never receives the item's link, source name, or any URL. Its only input is the title and `content_text` — `prompts.py:35`, `:61`.
- Summary prompt rules: treat content as data, not instructions; 2–4 sentences on substance; leave out identifiers, handles, metadata, timestamps; one short sentence if there is no substance ("e.g. only a link") — `prompts.py:26-33`.
- Language: `language_instruction` — English, Simplified Chinese, the original language, or a typed language name — `prompts.py:14-21`.
- Output: JSON `{"summary": "..."}`, `max_tokens=4096`; empty or missing summary → `ProviderError` → item marked unavailable — `summarize.py:93-101`.

**Grouping (`backend/src/catchup/digest/group.py`)**
- Payload per item: `{"ref": "i<n>", "title", "source", "summary"}` — `group.py:51-56`. Batches are split above `grouping_batch_chars`, then merged — `:59-96`. Model refs are validated, and unplaced items go to "Other" ("其他" for zh-Hans) — `:26-48`. Prompts tell the model not to output links or source names — `prompts.py:71-94`.

**Model client and token usage (`backend/src/catchup/llm/client.py`)**
- `chat_json` uses `response_format={"type": "json_object"}` and an httpx2 timeout of connect 10 s, read 300 s — `client.py:116-131`.
- Retries: up to 3 attempts with 0.25 s / 0.5 s backoff for 429, 500, 503, and empty content; 401 → `AuthFailed`, 402 → `InsufficientBalance` — `client.py:73-95`.
- Usage: prompt and completion tokens from each response are summed under a lock; `usage_totals()` returns `None` if no response reported usage — `client.py:110-114`, `:125-130`.
- The runner stores the totals on `DigestRun.prompt_tokens/completion_tokens` (`runner.py:149-151`, `:299`, `:376`) and sets `(0, 0)` when no item reaches the model (`:252-254`). The saved digest returns them from its run — `api/digests.py:96-97`. The UI shows "Tokens: N in / M out" or "Tokens: not reported" — `frontend/src/components/format.ts:39-42`; `DigestArticle.tsx:46-47`; `Home.tsx:84-85`, `:105`.
- There is no per-item token record and no token or cost budget per run.

### 4. Data model and citations

**Tables (`backend/src/catchup/models.py`)**
- `Item` — `models.py:73-92`: `id`, `source_id`, `identity_key`, `link`, `title`, `published_at`, `discovered_at`, `content_text` (one text column), `content_origin`, `summary`, `summary_language`, `state` (`pending`/`baseline`/`delivered`), `transcript_status`. Unique `(source_id, identity_key)`, index `(source_id, link)` — `:75-78`.
- No table or column stores an entry's inline links, fetched linked pages, comment URLs, comment counts, comments, or the post author.
- `Source` — `models.py:59-70`: `title`, `site_url`, `feed_url`, `input_url`, `kind` (`feed`/`podcast`/`youtube`), `created_at`, `last_check_at`, `last_check_status`. No per-source options.
- `SourceCheck` — `models.py:95-107`; `DigestRun` — `:110-125`; `Digest` — `:128-138`; `DigestTopic` — `:141-149`.
- `DigestItem` (snapshot) — `models.py:152-167`: `title`, `link`, `source_name`, `source_kind`, `published_at`, `summary`, `summary_unavailable`, `update_reason`, `item_id` (`SET NULL` on item delete). One link per item.
- Migrations (Alembic, run at startup — `db.py:32-36`): `0001_initial` — `migrations/versions/0001_initial.py:13-112`; `0002_transcripts` (source kind, transcript status, YouTube preferences, context window, token columns, creator updates) — `0002_transcripts.py:13-33`; `0003_digest_snapshot` (digest language, item source kind) — `0003_digest_snapshot.py:13-17`. Head is `0003_digest_snapshot`.

**How a digest cites sources today**
- The snapshot copies `item.title`, `item.link`, the source title, and kind into `DigestItem` — `runner.py:340-346`. The `digest-generation` requirement "Citations come from stored data" fixes this; model refs that do not match an item are discarded — `group.py:38-42`.
- `GET /api/digests/{id}` and `/latest` return `{id, created_at, model_id, item_count, source_count, language, creator_updates, transcript_wait_days, prompt_tokens, completion_tokens, topics: [{title, overview, items: [{title, link, source_name, source_kind, published_at, summary, summary_unavailable}]}]}` — `api/digests.py:57-102`.
- Frontend type `DigestItem` mirrors those item fields — `frontend/src/components/DigestArticle.tsx:10-13`. Each item renders the source kind, source name, time, its title linked to `item.link` (`target="_blank" rel="noopener noreferrer"`), and the summary or "Summary unavailable" — `DigestArticle.tsx:66-77`.
- `SummaryText` splits the summary string into paragraphs and `- ` list lines; it renders plain text, with no links or Markdown — `frontend/src/components/ui.tsx:110-125`.

### 5. Tests that cover these areas (`backend/tests`)
- **Global isolation:** every test blocks real DNS and sockets, and makes host-spacing and `safe_fetch` sleeps virtual — `conftest.py:8-20`.
- **Collection and article text:** `test_collection.py`. Helpers `feed_bytes`, `item`, `serve` build RSS with a `<description>` and mock it with respx — `:21-84`. `run_check` calls `check_source` without a spacer — `:67-77`. Article tests: replacement `:253-268`; 503 or empty extraction falls back `:271-281`; blocked address `:284-294`; extractor exception `:297-308`.
- **Confirm path:** `test_sources_api.py`. An oversized article keeps the feed text, calling `article_text` directly — `:134-140`. Text-only posts in a podcast source use article handling — `:165+`. A pending entry on confirm gets its article — `:378-391`.
- **Feed parsing:** `test_discovery.py:50-110` (fixtures `rss.xml`, `atom.xml`, `no-ids.xml`, `no-dates.xml`, `bluesky-untitled.xml`; plain text, titles, identities); `test_feed_transcripts.py` (podcast transcript elements). Fixtures are in `backend/tests/fixtures/`.
- **`safe_fetch`:** `test_safe_fetch.py` — non-public and mixed DNS answers `:29-40`, NAT64 `:42-54`, slow drip deadline `:56`, redirect to metadata `:74`, invalid URLs `:88`, timeout `:94`, oversized stream `:101`, 6 MB feed limit `:109`, redirects `:121-141`, User-Agent `:143-180`, Retry-After and rate-limit policy `:184-267`.
- **Host spacing:** `test_host_spacing.py:18-55` (per host, case-insensitive; spacer used on redirect and retry); runner-level spacing across two sources — `test_digest_runner.py:658-698`, which patches `catchup.digest.runner.HostSpacer`.
- **Runner:** `test_digest_runner.py` uses `FakeModel` (`:24-49`), `seed` (`:59-75`), and `stub_collection`/`stub_outcomes`, which replace `catchup.digest.runner.check_source` (`:78-103`). Tokens — `:419-449`; outcomes, failures, recovery, progress — `:124-655`.
- **Summaries and grouping:** `test_digest_stages.py` (cache and language `:30`, prompt rules `:68`, auth failure `:79`, grouping refs and batches `:119-170`); `test_long_summaries.py` (single call, split and combine, transcript prompt, part failure, CJK splitting `:34-98`).
- **End to end:** `test_core_flow.py:30` — preview, confirm, run, and stored citations, with `short_text_chars=0`, so no article fetch happens.
- **Digest JSON:** `test_digest_history.py:57-356`. Frontend: `frontend/src/components/DigestArticle.test.tsx`, `frontend/src/pages/DigestView.test.tsx`, `frontend/src/pages/Home.test.tsx`.
- **Config:** `test_config.py:8-42` covers only the transcript-related settings and the removed `CATCHUP_MAX_ITEM_CHARS`.

## Code References
- `backend/src/catchup/sources/feeds.py:87-99` — `_Text` / `plain_text`, the step that drops hrefs.
- `backend/src/catchup/sources/feeds.py:119-127` — `FeedEntry` fields.
- `backend/src/catchup/sources/feeds.py:153-203` — `parse_feed`; body selection `:165-167`.
- `backend/src/catchup/collection.py:39-54` — `article_text`.
- `backend/src/catchup/collection.py:57-142` — `check_source`; article calls `:99-101`, `:110-113`.
- `backend/src/catchup/api/sources.py:94-170` — `confirm`; article call `:141-145`; spacer `:131`.
- `backend/src/catchup/net/safe_fetch.py:18-20`, `:72-97`, `:100-192` — limits, address check, fetch loop.
- `backend/src/catchup/net/host_spacing.py:9-27` — `HostSpacer`.
- `backend/src/catchup/net/feed_cache.py:11-34` — preview-to-confirm cache.
- `backend/src/catchup/net/rate_limit.py:7-10` — `is_rate_limited`.
- `backend/src/catchup/config.py:30-72` — `Settings`.
- `backend/src/catchup/digest/runner.py:166-391` — `run_digest`; `:394-420` — `run_detail`.
- `backend/src/catchup/digest/summarize.py:15-29`, `:72-134` — inputs, per-item summary, workers.
- `backend/src/catchup/llm/prompts.py:7-94` — all prompts and token budgets.
- `backend/src/catchup/digest/group.py:51-96` — grouping payload and batching.
- `backend/src/catchup/llm/client.py:73-140` — retries, usage, timeouts.
- `backend/src/catchup/models.py:73-92`, `:152-167` — `Item`, `DigestItem`.
- `backend/src/catchup/migrations/versions/0003_digest_snapshot.py` — current migration head.
- `backend/src/catchup/api/digests.py:57-102` — digest JSON.
- `frontend/src/components/DigestArticle.tsx:10-25`, `:66-77` — digest types and item rendering.
- `frontend/src/components/ui.tsx:110-125` — `SummaryText`.
- `frontend/src/pages/Home.tsx:61-70`, `:160-175` — progress and polling.

## Current Specs
Read with `openspec list --specs` and `openspec show <id> --type spec` (main @ dba8ec8).

- **content-collection**
  - "Keep article text for summarization": "When that text is very short, the system SHALL try to fetch the linked article through the safe fetcher and extract its main text, and fall back to the feed text if extraction fails." Podcast episodes and YouTube videos "MUST NOT be summarized from their show notes, descriptions, or linked pages." Scenario "Feed provides only a short excerpt": the stored text "is the extracted article text" — `openspec/specs/content-collection/spec.md:80-89`. The #47 delta (not merged) rewrites this requirement (see area 1).
  - "Space requests to the same host during a run": "at least 1 second between consecutive requests to the same host. This covers feed checks and article fetches." — `:98-107`.
  - "Identify rate-limited checks" applies to source checks — `:91-96`.
  - "Check every source on each run" defines outcomes per source — `:8-38`.
- **digest-generation**
  - "Summarize items once and group them by topic": "summarize each item that has text for summarization individually, and reuse a stored summary" — `openspec/specs/digest-generation/spec.md:56-69`.
  - "Citations come from stored data": "Every item in a digest MUST show its source name and original link taken from stored item and source records." — `:71-76`.
  - "Summaries focus on substance": "2–4 sentences about the item's substance"; "An item without substantive content MUST be described in one short sentence saying so." — `:110-119`.
  - "Summarize long texts in full": the budget is computed from the context window, 60,000 characters when unknown; "The system MUST NOT drop any part of the text." — `:166-183`.
  - "Report model token usage": totals per run, shown in the run view and the saved digest; "Prices are not shown." — `:185-194`.
  - "Show run progress and per-source outcomes": stage, items summarized out of total, each source's outcome — `:19-24`.
  - "Include every pending item" (no item limit) — `:26-43`.
  - "Retry transient model errors" — `:121-130`.
  - "Digest language chosen by the user" — `:78-87`.
- **source-management**
  - "Fetch user-supplied URLs safely": refuse private, loopback, link-local, and cloud-metadata addresses, including through redirects; "Fetches MUST time out and MUST stop reading responses above a size limit"; "All other responses, such as article pages and transcripts, SHALL use a 5 MB limit." — `openspec/specs/source-management/spec.md:123-144`.
  - "Identify CatchUp in outgoing requests": "Every request CatchUp makes to a source SHALL carry a User-Agent that names CatchUp" — `:146-155`.
  - "Honor rate limits when fetching": one retry for a delay up to 10 s — `:157-174`.
  - "Confirm and save a source": up to 5 entries from the last 7 days marked new — `:105-114`.
  - "Preview a source from a pasted URL" lists the preview fields; no per-source options exist — `:8-60`.
- **transcripts**
  - Podcast and YouTube items are summarized only from transcripts or captions — `openspec/specs/transcripts/spec.md:8-20`, and D-013.
  - "Limit and space caption requests": a per-run cap (default 20), spaced per host, stop after a block — `:143-157`.
- **digest-history**
  - "Reopen a saved digest": for each summarized item, "its summary, title, source name and source kind, publish date when known, and a link to the original"; "The content shown MUST be the content that was saved, and MUST NOT be regenerated." — `openspec/specs/digest-history/spec.md:19-43`.
- **user-interface**
  - "Digest reading layout": each item shows its source kind, source name and publish time, "its title linked to the original", and "its summary: paragraphs, with "- " lines as a list" — `openspec/specs/user-interface/spec.md:30-67`.
- `model-settings` and `local-deployment` have no requirement about item text, fetching, or summaries.

## External Facts
Fetched read-only with `curl` GET between 10:55 and 11:02 UTC on 2026-10-19; nothing was posted. "CatchUp sees" numbers come from running CatchUp's own `parse_feed` (main @ dba8ec8) on the saved feed bytes. Link counts come from the `<a href>` elements in each entry body. CatchUp has no robots.txt handling: a search of `backend/src`, `frontend/src`, `README.md`, the specs, and the decision log finds no "robots".

**Simon Willison's Weblog — https://simonwillison.net/atom/everything/**
- 200, `application/xml; charset=utf-8`, 109,107 bytes, Atom, 30 entries (2026-10-07 to 2026-10-18). The body is in `<summary type="html">` (30 of 30); there is no `<content>` element and no per-entry author.
- CatchUp sees `content_text` of 187 / 772 / 6,548 characters (min / median / max). **8 of 30 entries are below `short_text_chars` (500)**, so they trigger an article fetch today. Among them are `/2026/Oct/18/llm-tools-datasette/` (254), `/2026/Oct/13/web-edit/` (187), and `/2026/Oct/12/datasette-ports/` (274).
- Links per entry: 3 / 8 / 40, 327 in total. Every entry ends with a "Tags:" paragraph of same-site `/tags/` links (30 of 30).
  - same-site `/tags/` links: 157;
  - other same-site posts and anchors: 23 (e.g. `https://simonwillison.net/2026/Oct/12/web-edit/`), plus 18 on `tools.simonwillison.net`;
  - github.com: 38, of which 11 are `/releases/tag/` links; plus 2 on gist.github.com;
  - docs and changelog pages: 18 (e.g. `https://llm.datasette.io/en/stable/changelog.html#v0-33`, `https://docs.python.org/3.15/whatsnew/3.15.html`);
  - discussion and social: 10 (6 news.ycombinator.com, 3 twitter.com, 1 reddit.com);
  - other external articles: 62;
  - 14 `<img>` tags, all on `static.simonwillison.net`.
- Entry kinds, inferred from the leading markup (the feed has no type element): Release 10 (`<p><strong>Release:</strong> <a href=…/releases/tag/…>`), link-blog 6 (`<p><strong><a href=EXTERNAL>`), quotation 6 (`<blockquote cite=…>`, titles "Quoting …"), Tool 3, Research 1, other notes 4. Three link-blog entries end with a "Via Hacker News" link (e.g. `/2026/Oct/13/redesigning-source-control-at-anthropic/` → `news.ycombinator.com/item?id=50073633`).
- The #47/#48 entry `https://simonwillison.net/2026/Oct/18/llm-tools-datasette/` (254 characters) has 5 hrefs:
  - `https://github.com/simonw/llm-tools-datasette/releases/tag/0.1.1`
  - `https://github.com/pydantic/httpx2`
  - `https://llm.datasette.io/en/stable/changelog.html#v0-33`
  - `https://simonwillison.net/tags/datasette`
  - `https://simonwillison.net/tags/llm`
- Other short entries also link to login-scoped or share pages, e.g. `https://claude.ai/code/session_…` (`/2026/Oct/13/web-edit/`) and `https://chatgpt.com/share/…` (`/2026/Oct/10/python-actions/`).
- The feed has no comment elements (no `wfw:`, `slash:`, `thr:`, or `rel="replies"`).
- Post pages (`/2026/Oct/18/llm-tools-datasette/` 13,955 bytes; `/2026/Oct/12/python-3-15/` 26,531; `/2026/Oct/13/redesigning-source-control-at-anthropic/` 18,598; all 200 `text/html`) have **no comment section**: no element whose id or class contains "comment", no form, no iframe, and no Disqus, Coral, OpenWeb, spot.im, Viafoura, giscus, or utterances embed.
  - The only external script is `plausible.io`.
  - `<head>` declares `<link rel="webmention" href="https://webmention.io/simonwillison.net/webmention">` and a pingback link; no webmentions are rendered.
  - Long-form pages link to the author's profiles (Mastodon `fedi.simonwillison.net/@simon`, Bluesky, Twitter), not to per-post threads.
- trafilatura's default `extract` of the saved llm-tools-datasette page returns 310 characters, the same with `include_comments=False`. This matches the #47 sidebar extraction.
- robots.txt (`User-agent: *`) disallows only `/admin/` and `/search/`.

**The Verge — https://www.theverge.com/rss/index.xml**
- 200, `application/xml; charset=UTF-8`, 29,767 bytes. **Atom despite the URL**, 10 entries. Each entry has `author/name`, `id` (`https://www.theverge.com/?p=NNNNNNN`), `summary type="html"`, and `content type="html"`. It declares the `thr` namespace but uses no `thr:` element.
- CatchUp sees `content_text` of 680 / 684 / 1,127 characters. **0 of 10 are below 500**, so no article is fetched. 9 of 10 bodies end with a self-link, "Read the full story at The Verge.", so the stored text is the feed's truncated opening.
- Links per entry: 1 / 3 / 7, 32 in total. They are the 9 self-links, 7 other same-site articles or newsletters, 1 author page, 1 Threads post, and 14 other external links, 3 of them Best Buy affiliate links. There are no GitHub, docs, or share links. 11 `<img>` tags on `platform.theverge.com`.
- No comment elements in the feed.
- The article page was **not fetched**. theverge.com/robots.txt disallows `/` (allowing only `/sp/`) for `Claude-User`, `ClaudeBot`, `Claude-Web`, `Claude-SearchBot`, and `anthropic-ai`. So whether The Verge has a comment section, how it is served, and whether it needs a login were not determined.
- For `User-agent: *`, article paths and `/rss/index.xml` are not disallowed. `/users/*/comments`, `/users/*/replies`, `/login`, `/account`, `/auth/*`, `/sso`, `/search`, and `/share*` are.

**Terry Tao, What's new (WordPress.com) — https://terrytao.wordpress.com/feed/**
- 200, `application/rss+xml; charset=UTF-8`, 62,508 bytes, RSS 2.0, 10 items, generator `http://wordpress.com/`.
- Per item: `title`, `link`, `comments`, `dc:creator`, `pubDate`, `category`, `guid isPermaLink="false"` (`http://terrytao.wordpress.com/?p=NNNNN`), `description` (excerpt), `content:encoded` (full HTML), `wfw:commentRss`, `slash:comments`, `post-id` (namespace `com-wordpress:feed-additions:1`), and `media:content`.
  - `dc:creator` is "Terence Tao" on all 10, including a guest post by another author (p=18496).
- CatchUp sees `content_text` (from `content:encoded`) of 134 / 1,523 / 23,073 characters. **3 of 10 are below 500**. They are short announcement posts, each linking to one or two external pages:
  - `/2026/10/15/simons-foundation-launches-15m-effort-…/` (134) → `https://www.simonsfoundation.org/news/simons-foundation-launches-15m-effort-to-help-mathematicians-navigate-ai-era/`
  - `/2026/10/14/first-proof-third-batch-webinar/` (164) → `https://1stproof.org/`, `https://icarm.io/news/first-proof-third-batch-results-webinar/`
  - `/2026/10/13/2026-ams-committee-on-education-workshop-report/` (370) → `https://www.ams.org/about-us/governance/committees/2026CoEWorkshop`
- Links per item: 1 / 1.5 / 12, 37 in total: 28 external pages (university, workshop, PDF slides, other blogs), 3 YouTube, 2 x.com, 2 same-site posts, 1 image upload, 1 mailto. No tag or category links in bodies, no GitHub, no share links.
- **Comment elements** (namespaces `wfw` = `http://wellformedweb.org/CommentAPI/`, `slash` = `http://purl.org/rss/1.0/modules/slash/`):
  - `<comments>`: `https://terrytao.wordpress.com/2026/10/15/why-are-we-even-doing-all-this/#comments` (`#respond` on a post with 0 comments);
  - `<wfw:commentRss>`: `https://terrytao.wordpress.com/2026/10/15/why-are-we-even-doing-all-this/feed/`;
  - `<slash:comments>` per item: 21, 20, 2, 16, 8, 46, 10, 5, 0, 4 (min 0, max 46).
- **Per-post comment feed** `…/2026/10/15/why-are-we-even-doing-all-this/feed/` (post 18439, 46 comments): 200, `application/rss+xml`, 27,629 bytes, channel title "Comments on: Why are we even doing all this?".
  - It returns **only the newest 10 items**; `?paged=2` returned the same 10.
  - Each item has exactly `title` ("By: <name>"), `link` (`…/comment-page-1/#comment-698332`), `dc:creator`, `pubDate`, `guid` (`http://terrytao.wordpress.com/?p=18439#comment-698332`), `description`, and `content:encoded`.
  - There is no author URL or e-mail; identity is only the `dc:creator` display name (9 distinct names in 10 items).
  - There is no threading element, but 6 of 10 bodies begin with "In reply to <a href=…#comment-N>name</a>."
  - The post author wrote 0 of these 10 (0 of 46 on the page).
- A second per-post feed, for an older post where the author does reply: `https://terrytao.wordpress.com/2018/03/28/246c-notes-1-meromorphic-functions-on-riemann-surfaces-and-the-riemann-roch-theorem/feed/` (post 10498). 200, 16,545 bytes, 10 items, **2 with `dc:creator` "Terence Tao"** (titles "By: Terence Tao"). Pingbacks also appear as items, with `dc:creator` set to the linking page's title.
- Site-wide comment feed `https://terrytao.wordpress.com/comments/feed/`: 200, 25,542 bytes, 10 items, titles "Comment on <post title> by <name>". 1 of 10 is by "Terence Tao".
- **Post HTML**, post 18439 (292,140 bytes, body class `postid-18439`, shortlink `https://wp.me/p3qzP-4Np`):
  - Comments are **rendered server-side** in `<div id="comments" class="commentlist">` under `<h2 class="comments-title">46 comments</h2>`.
  - Each comment is `<div class="comment byuser comment-author-<login> … depth-N vcard" id="comment-NNNNNN">`; the theme uses no `ol.commentlist` or `li.comment`.
  - The name is in `p.comment-author > strong.fn`, wrapped in `<a class="url" rel="ugc external nofollow">` when the commenter gave a URL, so the HTML has author URLs that the feed lacks.
  - The text is in `div.comment-content`. Replies are nested in `<ul class="children">` with `depth-1`…`depth-3` and `parent` classes. The reply link carries `data-commentid`, `data-postid`, and `data-replyto`.
  - `bypostauthor`: 0.
- **Post HTML**, post 10498 (1,070,391 bytes, "67 comments": 62 comment divs plus 5 `pingback`):
  - **`bypostauthor` appears 10 times**, always with `comment-author-teorth`, e.g. `class="comment byuser comment-author-teorth bypostauthor odd alt depth-2 vcard parent"`.
  - The author's name markup is `<strong class="fn"><a href="http://www.math.ucla.edu/~tao" class="url" …>Terence Tao</a></strong>`. Depth classes go up to `depth-5`.
- Neither post paginates comments. The navigation div is empty, and there are no `comment-page-2` links, although permalinks use `/comment-page-1/#comment-N`.
- trafilatura's default `extract` (as in `collection.py:48`) of the saved pages, measured locally:
  - post 18439: 31,868 characters, against 7,374 with `include_comments=False`;
  - post 10498: 84,210 against 58,373.
  - The comment text is included without commenter names (see area 1).
- REST API:
  - `https://terrytao.wordpress.com/wp-json/wp/v2/comments?post=18439&per_page=5` → 404 (an HTML "Page not found" page).
  - `?rest_route=/wp/v2/comments&post=18439` → 200 with the home page HTML (the route is ignored).
  - The response's `link` header points the API at `https://public-api.wordpress.com/wp-json/?rest_route=/sites/terrytao.wordpress.com`. `public-api.wordpress.com/robots.txt` is `User-agent: * / Disallow: /`, so neither that API nor the v1.1 `/replies/` endpoint was called. Its author fields were not observed.
- robots.txt (`*`): feeds, post paths, and `/wp-json/` are not disallowed. Disallowed include `/wp-admin/`, `/wp-login.php`, `/next/`, and `/public.api/`.

**YouTube channel feed — https://www.youtube.com/feeds/videos.xml?channel_id=UCbfYPyITQ-7l4upoX8nvctg** (Two Minute Papers, a stand-in for the user's channel)
- 200, `text/xml; charset=UTF-8`, 32,186 bytes, Atom, 15 entries; CatchUp classifies it as `youtube`.
- The body is `media:group/media:description`: plain text with no HTML and no `<a>` elements. It has bare URLs: 2 / 9 / 23 per entry, 158 in total (x.com 95, a sponsor 13, youtube.com 6, github.com 4, arxiv.org 2, others).
- YouTube items are summarized only from captions (`transcripts` spec, D-013), so this description text is not sent to the model.
- No comment elements; `media:community` holds only `media:starRating` and `media:statistics views=`.
- youtube.com/robots.txt has `Disallow: /feeds/videos.xml` for `*`, and also `/comment`, `/api/`, `/youtubei/`. The feed was fetched once before robots.txt was read, and no further YouTube requests were made.

## Related History
- **D-004** (OpenAI-compatible adapter, DeepSeek): "collected content is sent to the configured provider" — `docs/process/decision-log.md:24-28`.
- **D-013**: podcasts and YouTube are summarized only from transcripts; summarizing show notes and descriptions was rejected "because it would claim to cover content that was not processed"; long texts are summarized in full with a budget from `context_window` — `docs/process/decision-log.md:84-102`.
- **Requirement changes** (`docs/process/requirements-changes.md`):
  - 2026-10-03: extracting the linked article for Reddit link posts was deferred — `:18`.
  - 2026-10-04: the Reddit link-post extractor (#2) was dropped, and Reddit RSS ends 2026-11-13 — `:19`.
  - 2026-10-05: the summary budget comes from `context_window`, and the captions library bypasses `safe_fetch`'s spacing and rate-limit handling — `:23`.
  - 2026-10-19: the #47 coverage rule — `:36`.
- **AI usage log** (2026-10-19): the user's original F7/F8/F9 request and decisions (translated), and the split into #47, #48, #49, and a comment on #41 — `docs/process/ai-usage-log.md:1096-1109`.
- **Issue #41** (X accounts, Todo) has a 2026-10-19 comment: when X is supported, also read the author's own replies in the thread; "The general version, for blog comment sections, is #48."
- **Sibling change:** `openspec/changes/add-item-images/` (#49, important images) exists with only `.openspec.yaml`. Its issue also lists the feed parser and article extraction as text-only.
- **README:** "Articles and transcripts remain limited to 5 MiB"; "X, pages without feeds, and content behind a login or paywall are not supported in this release." — `README.md:196`, `:213-214`.
