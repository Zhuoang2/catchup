# Research: Show an item's important image in the digest (issue #49)

- Date: 2026-10-19
- Query: For issue #49 ("Show an item's important image in the digest"), what image information reaches CatchUp today, from feeds (`media:content`, `media:thumbnail`, image enclosures, `itunes:image`, `<img>` in the entry HTML), from article extraction, and from YouTube and podcast feeds? Where is it kept or dropped? What does the model receive and return per item, and how is a digest stored and served? How does the reading layout render items and Creator updates, and what headers, service-worker rules, and docs bear on loading a remote image in the browser? What do the user's real sources publish, and do their image hosts block hotlinking? User decisions recorded on the issue: the model decides which image, if any, is important; the image is first loaded directly from the source site (hotlinking), not stored as a copy.
- Git ref: main @ dba8ec8 (the working tree also has the untracked change folders `openspec/changes/add-item-images/` and `openspec/changes/add-linked-pages-and-author-replies/`)

## Summary

Today no image information survives collection. `parse_feed` reads only the entry's title, link, id, dates, transcript tags, audio enclosures, and the first `content` value (else `summary`). It flattens that HTML to text with a parser that keeps only text nodes, so every `<img>` `src` and `alt` is dropped, while `<figcaption>` text is kept. The installed feedparser (6.0.14) already exposes `media_content`, `media_thumbnail`, image `enclosures`, `itunes:image` (`entry.image`), and the raw HTML with `<img src alt>`, but none of these are read. When the feed text is short, `article_text` fetches the page and calls trafilatura's `extract` with its defaults (`output_format="txt"`, `include_images=False`), and only the plain text is stored. `items` and the `digest_items` snapshot have no image column, the model client sends and receives text-only JSON (`{"summary": ...}`, `{"topics": [...]}`), and the digest API returns no image field. The frontend renders no `<img>` anywhere (icons are inline SVG), a test asserts that a rendered digest contains no `img`, the backend sets no CSP or Referrer-Policy, and the service worker ignores all non-navigation requests. In the four real feeds checked, images appear as `<img>` in entry HTML (Simon Willison, The Verge, one Terry Tao post), as `media:content` that is mostly author avatars (Terry Tao), and as `media:thumbnail` (YouTube). All four sampled image hosts answered 200 both with and without a `Referer: http://127.0.0.1:8800/` header.

## Detailed Findings

### 1. Image information in collection today

**Feed parsing (`backend/src/catchup/sources/feeds.py`)**
- `parse_feed` calls `feedparser.parse(response.content)` with the bytes only. No base URL or response headers are passed — `feeds.py:153-154`.
- Fields read per entry:
  - `published_parsed` / `updated_parsed` — `feeds.py:163-164`
  - the first `content` value, else `summary` — `feeds.py:165-166`
  - `title` — `feeds.py:168`
  - `link` — `feeds.py:169-174`
  - `id` — `feeds.py:175`, `feeds.py:178`
  - `podcast_transcript` (fallback) — `feeds.py:181-186`
  - `enclosures`, only to test for an `audio/` type (`has_audio`) — `feeds.py:187-188`
- Feed-level fields read: `language` (`feeds.py:158`), `link` (`feeds.py:194`), `title` (`feeds.py:198`).
- The entry HTML becomes text through `plain_text` (`feeds.py:167`). Its `_Text` parser implements only `handle_data` and joins fragments with single spaces — `feeds.py:87-99`. Tag attributes are never seen, so `<img src>` and `alt` are dropped. Text inside `<figure>`/`<figcaption>` is kept as ordinary text.
  - Checked locally against the repository code: `plain_text('<p>Body <img src="…/y.png" alt="Y alt"> <figure><img src="/rel.png" alt=""><figcaption>Cap</figcaption></figure></p>')` returns `'Body Cap'`.
- `FeedEntry` fields: `identity_key`, `link`, `title`, `published_at`, `content_text`, `has_audio`, `transcripts` — `feeds.py:119-127`. `Feed` fields: `feed_url`, `site_url`, `title`, `entries`, `youtube_host`, `audio_share` — `feeds.py:130-150`. Neither has an image field, and the entry's HTML is not kept.
- `FeedEntry` is constructed in one place in `src/` (`feeds.py:189-193`) and once positionally in tests (`backend/tests/test_sources_api.py:135`).
- The separate lxml pass `_transcript_candidates` walks only RSS `<item>` elements and reads `guid`, `link`, and `podcast:transcript` — `feeds.py:44-84`.
- What the installed feedparser 6.0.14 exposes for the same document. This was checked with a throwaway script outside the repository. None of these keys are read by `parse_feed`:
  - `entry.media_content`: a list of dicts (`url`, `medium`, `type`, `width`, `height`)
  - `entry.media_thumbnail`: a list of dicts (`url`, `width`, `height`)
  - `entry.enclosures`: includes `image/*` enclosures (`href`, `type`, `length`)
  - `entry.image`: `{'href': …}`, from an item-level `itunes:image`
  - `parsed.feed.image`: from RSS `<image>` or a channel `itunes:image`
  - `entry.content[0].value` / `entry.summary`: HTML in which feedparser's sanitizer keeps `<img alt src>`
  - A relative `src` such as `/rel.png` stays relative, because no base URL is passed.
  - For a YouTube Atom entry, `media:group` yields `media_thumbnail` (the `ytimg.com` thumbnail), `media_content` (type `application/x-shockwave-flash`), and `summary` (from `media:description`).

**Article extraction (`backend/src/catchup/collection.py`)**
- `article_text(entry, fallback_links, threshold, *, spacer)` — `collection.py:39-54`:
  - It returns the feed text, with origin `"feed"`, when the feed text is at least `threshold` characters, or when the link is a fallback link. No page is fetched in that case — `collection.py:41-42`.
  - Otherwise it fetches `entry.link` with `safe_fetch` (`collection.py:44`), under the default 5 MiB limit (`net/safe_fetch.py:18`).
  - It then calls `extract(response.content, url=response.url)` with no other options (`collection.py:48`), and returns `(text.strip(), "article")` when the text is non-empty (`collection.py:49-50`).
  - Every failure falls back to the feed text — `collection.py:45-46`, `collection.py:51-54`.
- Installed trafilatura is 2.3.0 (`backend/uv.lock:1721-1722`; the constraint is `trafilatura>=2,<3` in `backend/pyproject.toml:19`). The defaults of `extract` in that version:
  - `output_format="txt"`
  - `include_images=False`, `include_links=False`
  - `include_tables=True`, `include_comments=True`
  - `with_metadata=False`

  The fetched page HTML is not kept after extraction.
- The threshold is `short_text_chars`, default 500 (`config.py:36`, `config.py:57`). So pages are fetched only for entries whose feed text is shorter than 500 characters. For other entries, no article page, and so no `og:image`, is ever requested.
- Callers store only `(content_text, content_origin)`:
  - run-time checks: `collection.py:99-101` (text posts in a podcast feed) and `collection.py:110-122` (new entries)
  - confirming a source: `api/sources.py:141-151`
- The source preview response lists entries as `title`, `link`, `published_at` only — `api/sources.py:80-91`.
- **In-flight change `keep-feed-text-when-extraction-misses` (#47)**, planned, 0 of 3 tasks done:
  - It changes `article_text` to store the feed text, a blank line, and the extracted text when the extraction does not cover the feed text (`openspec/changes/keep-feed-text-when-extraction-misses/proposal.md`, "What Changes"; spec delta in `specs/content-collection/spec.md`).
  - Its `tasks.md` lists the extractor and its settings as out of scope. Its proposal lists no API, database, frontend, or configuration change ("Impact").
- **Change `add-linked-pages-and-author-replies` (#48)** has an untracked `research.md` written today. It also documents `plain_text` and `feeds.py`, for links inside entries.

**YouTube**
- YouTube items get `transcript_status="to_fetch"` and are stored with the feed text and origin `"feed"`, without an article fetch — `collection.py:107-113`. Their feed text is the `media:description` text (the `summary` key, as above).
- Captions, when found, replace `content_text` — `digest/runner.py:103-107`. The video id comes from the `yt:video:` identity key — `digest/runner.py:90-91`.
- With caption fetching off (the default, `models.py:54`), items become Creator updates with reason `captions_off`, and no model call is made — `digest/runner.py:83-84`, `digest/runner.py:45-46`.
- The feed's `media:thumbnail` is not read (see the fields listed above).

**Podcasts**
- An episode is recognized by an `audio/` enclosure (`feeds.py:187-188`), and only transcripts provide its text (`collection.py:20-36`).
- `itunes:image`, at item or channel level, is not read. The test fixtures contain no `itunes:image`, `media:*`, or image enclosure; they contain only `audio/mpeg` enclosures (`backend/tests/fixtures/podcast-*.xml`).

### 2. Data model, model input and output, and the digest API

**Tables (`backend/src/catchup/models.py`)**
- `Item`: `id`, `source_id`, `identity_key`, `link`, `title`, `published_at`, `discovered_at`, `content_text` (plain text), `content_origin`, `summary`, `summary_language`, `state`, `transcript_status` — `models.py:73-92`. It has no image or HTML column.
- `Digest` — `models.py:128-138`. `DigestTopic` (`kind` is `"topic"` or `"creator_updates"`) — `models.py:141-149`.
- `DigestItem` is the per-item snapshot: `digest_id`, `topic_id`, `position`, `item_id` (FK `SET NULL`), `title`, `link`, `source_name`, `source_kind`, `published_at`, `summary`, `summary_unavailable`, `update_reason` — `models.py:152-167`. It has no image column.

**Migrations (`backend/src/catchup/migrations/versions/`)**
- `0001_initial`: creates `items` (`0001_initial.py:52-67`) and `digest_items` (`0001_initial.py:99-112`).
- `0002_transcripts`: adds columns with `op.batch_alter_table`, including `digest_items.update_reason` (`0002_transcripts.py:32-33`). Its downgrade drops columns with `recreate="never"` (`0002_transcripts.py:36-51`).
- `0003_digest_snapshot` is the head. It adds `digests.language` and `digest_items.source_kind`, both nullable — `0003_digest_snapshot.py:13-17`.
- Migrations run to `head` at startup — `db.py:32-36`, called from `main.py:29-35`.

**What the model receives and returns**
- The runner builds `SummaryInput(item.id, item.title, item.content_text, item.summary, item.summary_language, item.content_origin)` — `digest/runner.py:221-225`. The dataclass is at `digest/summarize.py:15-22`.
- `_summarize` picks a prompt and calls `client.chat_json(messages, max_tokens=SUMMARY_MAX_TOKENS)` — `summarize.py:72-101`. Texts over the budget are split into parts, each part is summarized, and the notes are combined (`summarize.py:79-92`).
- The result must be a non-empty string under `"summary"`, or a `ProviderError` is raised — `summarize.py:94-97`. `SummaryResult` holds `id`, `summary`, `unavailable` — `summarize.py:25-29`.
- A stored summary in the current language is reused without a model call — `summarize.py:115-117`.
- `record()` writes only `item.summary` and `item.summary_language`, and increments `items_done` — `digest/runner.py:267-278`.
- Prompts (`backend/src/catchup/llm/prompts.py`):
  - `summary_messages`: the system prompt asks for 2–4 sentences about the item's substance and treats content as data. The output example is `{"summary": "A short factual summary."}`. The user message is `"Title: {title}\nContent:\n{text}"` — `prompts.py:24-36`.
  - `long_transcript_messages` includes "Do not describe visuals: no visual content was seen." — `prompts.py:39-49`.
  - `part_messages` — `prompts.py:52-62`. `combine_messages` — `prompts.py:65-68`.
  - `group_messages` returns `{"topics": [{"title", "overview", "item_refs"}]}` and is told "do not output links or source names" — `prompts.py:71-81`. `merge_messages` returns `topic_refs` — `prompts.py:84-94`.
- The grouping input is JSON with `ref`, `title`, `source`, `summary` per item — `digest/group.py:51-56`. Unknown or duplicate refs are discarded, and unplaced items go to "Other" — `group.py:26-48`.
- Model client: `chat_json(self, messages: list[dict[str, str]], max_tokens)` sends string content only, with `response_format={"type": "json_object"}`. It parses the reply as one JSON object — `llm/client.py:116-140`.

**Snapshot and API**
- The digest is saved in one transaction with delivery — `digest/runner.py:301-377`.
  - Topic items are copied as `title`, `link`, `source_name`, `source_kind`, `published_at`, `summary`, `summary_unavailable` from the `Item` and `SummaryResult` — `runner.py:337-347`.
  - Creator updates add `update_reason`, with `summary=None` — `runner.py:348-372`.
- `_serialize_digest` — `api/digests.py:57-102`:
  - topic item keys `title`, `link`, `source_name`, `source_kind`, `published_at`, `summary`, `summary_unavailable` — `digests.py:69-74`
  - Creator-update item keys `title`, `link`, `published_at`, `reason`, `source_kind`, grouped by `(source_name, source_kind)` — `digests.py:75-89`
  - top-level keys `id`, `created_at`, `model_id`, `item_count`, `source_count`, `language`, `creator_updates`, `transcript_wait_days`, `prompt_tokens`, `completion_tokens`, `topics` — `digests.py:91-101`
- `/api/digests/latest` (`digests.py:41-46`) and `/api/digests/{id}` (`digests.py:49-54`) share `_serialize_digest`. The list endpoint returns topic titles only — `digests.py:14-38`.

### 3. Frontend reading layout, links, and remote loading

**Component (`frontend/src/components/DigestArticle.tsx`)**
- Types: `DigestItem` (`title`, `link`, `source_name`, `source_kind`, `published_at`, `summary`, `summary_unavailable`), `Topic`, `CreatorUpdate`, `Digest` — `DigestArticle.tsx:10-25`.
- Topic item markup — `DigestArticle.tsx:66-78`. Each `article.item` contains:
  - `p.item-meta`: `KindIcon`, source name, `time`
  - `h3.item-title > a[href][target="_blank"][rel="noopener noreferrer"]`, with an external-link SVG icon and a visually hidden "(opens the original)"
  - then `SummaryText`, or `p.summary-unavailable`
- Creator updates markup — `DigestArticle.tsx:80-98`:
  - `section.creator#creator` with `h2.creator-title` and `p.creator-lede`
  - per source, `section.creator-group` with `h3.creator-source`
  - `ul.creator-list > li.creator-item`: the link (same `target`/`rel`, `DigestArticle.tsx:88`) and `span.creator-meta` (time, `ReasonLabel`)
- The same component renders the main screen (`pages/Home.tsx:223`) and a saved digest (`pages/DigestView.tsx:29`).
- `SummaryText` renders summary text as React text (paragraphs and `- ` lists), never as HTML — `components/ui.tsx:110-125`. `KindIcon` — `ui.tsx:50-54`.

**Grid and styles**
- `.page`: 12 columns with `--gutter` gaps; children span 8 by default — `styles/layout.css:13-14`. `.digest-layout` and `.digest-body` use `display: contents` — `layout.css:19`.
- `.topic` and `.creator` are full-width subgrids — `layout.css:21`.
  - Topic title and overview take columns 1–3 — `layout.css:22`.
  - `.topic > .items` takes columns 4 to -1, as a 9-column grid spanning rows 1–3 — `layout.css:23`.
  - Each `.item` spans all 9; consecutive items are separated by a top border — `layout.css:24-25`.
- In the `@container (width > 1100px)` block — `layout.css:26-31`:
  - `.items > .item` becomes a subgrid with rows `auto auto 1fr`
  - `.item-meta` (row 1) and `.item-title` (row 2) take item columns 1 to span 3
  - `.summary` and `.summary-unavailable` take columns 4 to -1 and rows 1 to -1
- D-018 records the summary measure as 580 px at 1440 px, in page columns 7–12 — `docs/process/decision-log.md:183-204`.
- Creator groups span 3 columns, and every third group starts at column 4 — `layout.css:32-35`.
- At `@container (max-width: 900px)`, the page, topics, items, and creator section become one column — `layout.css:54-69`.
- The container queries measure `.app`, which has `container-type: inline-size` — `styles/base.css:4`.
- Item and creator component styles — `styles/components.css:111-127`. Icon sizes — `base.css:13-14`, `components.css:12-13`.
- Theme tokens: light at `styles/tokens.css:1-40`, dark under `@media (prefers-color-scheme: dark)` at `tokens.css:42-67`. Tokens cover `--bg`, `--surface`, `--fg`, `--muted`, `--subtle`, `--border`, `--hover`, accent, and status colors. There is no image-specific token. Theme-color metas — `frontend/index.html:10-11`.
- `frontend/scripts/check-style-coverage.py` compares the class names used in `.tsx` files with the owned stylesheets and the archived C7 prototype (`check-style-coverage.py:60-78`). It is not a step in `.github/workflows/ci.yml:29-46`, which runs `npm test -- --run` and `npm run build`.

**Images, links, and network**
- No `<img>` element exists in `frontend/src` (repository grep). The only `<img` strings are test inputs (`pages/DigestView.test.tsx:29`, `:43`).
- Icons are inline SVG (`components/Icon.tsx:19-22`). Tab and app icons are `<link>` elements (`index.html:6-9`) and manifest entries (`public/manifest.webmanifest:9-14`).
- All frontend requests go to the same origin, through `request()` to `/api…` — `api/client.ts:14-15`. The Vite dev server proxies only `/api` to `http://127.0.0.1:8000` — `frontend/vite.config.ts:6-10`. Compose publishes `127.0.0.1:8000` — `compose.yaml:5-6`.
- Service worker (`frontend/public/sw.js`):
  - It caches only `/offline.html` (`sw.js:1-9`) and deletes other caches on activate (`sw.js:11-17`).
  - Its fetch handler returns without calling `respondWith` for any request whose `mode` is not `navigate` (`sw.js:19-20`), so image requests go straight to the network.
  - It is registered only in production builds — `src/main.tsx:8-11`.
- Backend response headers (`backend/src/catchup/main.py`):
  - The `allowed_host` middleware (`main.py:50-77`), the `/assets` `StaticFiles` mount (`main.py:88-91`), and the SPA fallback `FileResponse` (`main.py:93-102`) are the only response-shaping code.
  - No `Content-Security-Policy`, `Referrer-Policy`, `Cross-Origin-*`, or `X-Frame-Options` header is set anywhere in `backend/src` or `frontend/` (repository grep). `index.html` has no CSP or referrer `<meta>` — `index.html:1-18`.
  - External background: with no policy set, browsers apply their default referrer policy, `strict-origin-when-cross-origin`. For a cross-origin subresource, that sends only the page's origin, for example `http://127.0.0.1:8000/`.

### 4. Privacy and security context already documented

- README:
  - Collected content is sent to the configured model provider — `README.md:82-84`, `README.md:129-130`.
  - There is no login, the compose file binds to loopback, and how to expose the instance — `README.md:122-130`.
  - The User-Agent format and `CATCHUP_USER_AGENT_CONTACT` — `README.md:208-212`.
  - "CatchUp does not transcribe audio or summarize video visuals." — `README.md:214-215`.
- `docs/handoff.md:49`: without processing the visuals, do not claim to have summarized visual content.
- Decision log:
  - D-013 rejected a third-party transcript service partly because "it sends data to a third party" — `docs/process/decision-log.md:96`.
  - D-015: the service worker never caches app code or API responses — `decision-log.md:120-125`.
- Outgoing identification:
  - Backend source requests go through `safe_fetch`, whose `httpx.Client` sets `User-Agent: user_agent()` — `net/safe_fetch.py:34-41`, `safe_fetch.py:113`.
  - The YouTube caption session sets the same User-Agent — `transcripts/youtube.py:20-34`.
  - Backend fetches also carry DNS, redirect, timeout, and size checks — `safe_fetch.py:100-182`.
- The repository has no `SECURITY.md` or threat-model document (`git ls-files`). No existing doc mentions images, hotlinking, or requests that the browser makes to third-party hosts.

### 5. Tests that cover these paths

**Backend parsing and collection**
- `test_discovery.py`:
  - `test_parses_all_feed_fixtures` — `test_discovery.py:48`
  - `test_normalizes_identity_date_and_text`: asserts `content_text == "News summary ."` for `<p>News <b>summary</b>.</p>`, and `"Atom text"` for an Atom entry — `test_discovery.py:56-72`
  - untitled-entry tests — `test_discovery.py:75-107`
  - unsafe links — `test_discovery.py:115`
- `test_feed_transcripts.py:18-115`: the transcript candidate parser.
- `test_collection.py`:
  - `test_short_feed_excerpt_is_replaced_with_extracted_article` (also asserts a `CatchUp/` User-Agent on every call) — `test_collection.py:253-271`
  - fallbacks — `test_collection.py:270-308`
- `test_sources_api.py:134`: `test_large_article_keeps_feed_text` calls `article_text` directly, with a positional `FeedEntry` (`:135`).
- The fixtures contain no image elements (`backend/tests/fixtures/`).

**Backend digest JSON and storage**
- `test_digest_history.py`:
  - `test_latest_digest_matches_detail_with_all_saved_fields` — `test_digest_history.py:64-100`
  - `test_digest_detail_uses_snapshot_positions_and_survives_source_deletion`, which asserts the exact dict of a topic item (`test_digest_history.py:289-292`) and equality after source deletion (`:296`) — `test_digest_history.py:273-297`
  - `test_saved_language_and_kind_survive_setting_change_and_source_deletion` — `test_digest_history.py:300-317`
  - restart persistence — `test_digest_history.py:320-327`
- `test_creator_updates.py:174-223`: grouping and order of Creator updates in the JSON.
- `test_digest_stages.py:68-77`: summary prompt phrases and the `{"summary":` example.
- `test_digest_runner.py:124-719`: the run lifecycle and snapshot.
- `test_core_flow.py:30`: the end-to-end API flow with a fixture model.
- `test_db.py`:
  - the table set — `test_db.py:17-29`
  - the migration files list — `test_db.py:39-45`
  - the head revision asserted as `"0003_digest_snapshot"` — `test_db.py:63`
  - the 0003 upgrade and downgrade — `test_db.py:134-165`

**Frontend rendering**
- `DigestArticle.test.tsx:16-29`: slot order and an axe scan.
- `DigestView.test.tsx`:
  - `renders saved topics, text summaries, dates and safe original links` — `DigestView.test.tsx:25-61`. A topic titled `<img src=x onerror=alert(1)>` renders as text, and `document.querySelector('img, strong')` must be `null` (`:46`). The link has `target="_blank"` and `rel="noopener noreferrer"` (`:50-51`).
  - Creator updates rendering, including `rel` — `DigestView.test.tsx:134-182`
  - `keeps every item in one markup order…`: each `article.item`'s children must be exactly `p.item-meta`, `h3.item-title`, then `div.summary` or `p.summary-unavailable` — `DigestView.test.tsx:248-276`
- `Home.test.tsx:42-60`: the Home and saved-digest article markup must be identical (`outerHTML`).
- `styles/tokens.test.ts`:
  - contrast in both themes — `tokens.test.ts:75-84`
  - `places digest headings beside summaries only above 1100px` — `tokens.test.ts:233-272`. It forbids grid placement on item children outside the wide container (`:241-245`). It asserts that the only `.items > .item…` rules outside it are `.items > .item` and `.items > .item + .item` (`:263-266`).
  - no vertical rules on items — `tokens.test.ts:274-281`
  - one item separator — `tokens.test.ts:283-290`
- `src/test/accessibility.ts:4-8`: `expectAccessible` runs axe with only `color-contrast` disabled.
- `sw.test.ts:73-84`: the service worker does not intercept `/api`, `/assets`, or other non-navigation requests.

## Code References

- `backend/src/catchup/sources/feeds.py:87-99` — `plain_text`; keeps text nodes only, drops all attributes
- `backend/src/catchup/sources/feeds.py:119-127` — `FeedEntry` fields (no image)
- `backend/src/catchup/sources/feeds.py:153-203` — `parse_feed`; the fields read per entry and feed
- `backend/src/catchup/sources/feeds.py:187-188` — enclosures checked only for `audio/`
- `backend/src/catchup/collection.py:39-54` — `article_text`; `extract(response.content, url=response.url)` at `:48`
- `backend/src/catchup/collection.py:107-122` — new item creation: text, origin, transcript status
- `backend/src/catchup/api/sources.py:80-91`, `:141-151` — preview entries; confirm path calling `article_text`
- `backend/src/catchup/models.py:73-92`, `:152-167` — `Item` and `DigestItem` columns
- `backend/src/catchup/migrations/versions/0003_digest_snapshot.py:13-24` — latest migration (head)
- `backend/src/catchup/db.py:32-36` — `migrate()` to head
- `backend/src/catchup/digest/runner.py:221-225`, `:267-278`, `:301-377` — summary inputs, recording, snapshot write
- `backend/src/catchup/digest/summarize.py:72-101`, `:115-117` — per-item model call and the summary-cache shortcut
- `backend/src/catchup/llm/prompts.py:24-94` — every prompt and its JSON example shape
- `backend/src/catchup/digest/group.py:26-56` — grouping payload and ref validation
- `backend/src/catchup/llm/client.py:116-140` — `chat_json`: string messages, JSON object response
- `backend/src/catchup/api/digests.py:57-102` — digest detail JSON
- `backend/src/catchup/main.py:50-102` — middleware and static serving (no security headers)
- `backend/src/catchup/net/safe_fetch.py:18`, `:34-41`, `:113` — 5 MiB limit, User-Agent
- `frontend/src/components/DigestArticle.tsx:10-25`, `:66-98` — types, item markup, Creator updates markup
- `frontend/src/components/ui.tsx:110-125` — `SummaryText`
- `frontend/src/styles/layout.css:13-35`, `:54-69` — page grid, item subgrid, narrow layout
- `frontend/src/styles/components.css:111-127` — item and creator styles
- `frontend/src/styles/tokens.css:1-67` — light and dark tokens
- `frontend/public/sw.js:19-30` — navigation-only fetch handler
- `frontend/index.html:1-18` — no CSP or referrer meta
- `frontend/src/pages/DigestView.test.tsx:47`, `:248-276` — no-`img` assertion; fixed item child order
- `frontend/src/styles/tokens.test.ts:233-272` — the allowed set of item layout rules
- `backend/tests/test_digest_history.py:289-292` — exact topic item dict
- `backend/tests/test_db.py:63` — head revision assertion

## Current Specs

- `digest-generation`
  - "Summarize items once and group them by topic": "reuse a stored summary instead of summarizing the same item again"; every item appears exactly once — `openspec/specs/digest-generation/spec.md:56-57`.
  - "Citations come from stored data": source name and link come "from stored item and source records"; model item references that match no item "MUST be discarded" — `spec.md:71-72`.
  - "Summaries focus on substance": 2–4 sentences; "Summaries of transcripts MUST NOT describe visual content" — `spec.md:110-111`.
  - "Creator updates": per item, title, publish time, link, and reason. The system "MUST NOT call the model for these items, and MUST NOT show their show notes or descriptions" — `spec.md:132-144`.
- `digest-history`
  - "Reopen a saved digest": for each summarized item, its summary, title, source name and kind, publish date, and link. "The content shown MUST be the content that was saved, and MUST NOT be regenerated." Digests saved before a field was recorded "are shown without" it — `openspec/specs/digest-history/spec.md:19-26`.
  - "Open the latest digest": "the same content as reopening it" — `spec.md:51-52`.
- `user-interface`
  - "Digest reading layout": each item MUST show its source kind, its source name and publish time, its title linked to the original, and its summary. Above 1100 px: "its source line and linked title beside its summary". From 901 to 1100 px: stacked within the item area. At 900 px and wider, "every item's summary MUST have the same width and end at the right edge". At 1440 px, at most 40 Chinese or 80 Latin characters per summary line. At 900 px and below: "source line, title, and summary MUST stack in one column, in that order". The main screen and History "MUST use the same layout" — `openspec/specs/user-interface/spec.md:30-42`.
  - "Themes follow the system with accessible contrast": text at least 4.5:1, component boundaries at least 3:1, in both themes — `spec.md:19-20`.
  - "Readable Creator updates": title linked to the original, publish time, and reason — `spec.md:68-69`.
  - "Keyboard and screen-reader support": generated text carries its language — `spec.md:131-140`.
- `content-collection`
  - "Keep article text for summarization": short feed text triggers an article fetch and extraction, with fallback to the feed text. Podcast and YouTube items are never summarized from show notes, descriptions, or linked pages — `openspec/specs/content-collection/spec.md:80-81`. The in-flight #47 delta modifies this requirement.
  - "Space requests to the same host during a run": at least 1 s between requests; "This covers feed checks and article fetches" — `spec.md:98-99`.
- `source-management`
  - "Fetch user-supplied URLs safely": private, loopback, and metadata addresses are refused, including through redirects; responses other than feeds use a 5 MB limit — `openspec/specs/source-management/spec.md:123-124`.
  - "Identify CatchUp in outgoing requests": "Every request CatchUp makes to a source SHALL carry a User-Agent that names CatchUp" — `spec.md:146-147`.
- `transcripts`
  - "Opt in to fetching YouTube captions locally": while off, videos "MUST NOT be summarized from their descriptions or watch pages" and are listed under Creator updates — `openspec/specs/transcripts/spec.md:90-91`.
- `local-deployment`
  - "Offline page when the server is not running": "The service worker MUST NOT cache application code or API responses" — `openspec/specs/local-deployment/spec.md:84-85`.
  - "Local-only access by default" — `spec.md:30-31`.
- `model-settings`: no requirement mentions images or model input types. The requirements cover provider configuration, key protection, allowed hosts, errors, and the context window (`openspec/specs/model-settings/spec.md:8-67`).

## External Facts

Checked on 2026-10-19 around 11:00 UTC with `curl 8.2.1`: read-only `GET`/`HEAD` requests, default curl User-Agent, no cookies, and no browser `Sec-Fetch-*` headers. Feeds were parsed with the project's feedparser 6.0.14. The counts are a snapshot of the feed at that time. No article text was recorded.

**Feeds**

| Source | Feed | Image elements in the feed | Per entry | Alt text |
|---|---|---|---|---|
| Simon Willison | `https://simonwillison.net/atom/everything/`, Atom, 30 entries | `<img>` only, inside escaped HTML in `<summary type="html">` (14 `&lt;img`). No `media:*`, `enclosure`, `itunes:image`, `<logo>`, or `<icon>`. | 9 of 30 entries have images: 1–3 each (7 entries 1, 3 entries 2, 1 entry 3). | All 14 non-empty, 115–1478 characters long. No `width`/`height` attributes. Host `static.simonwillison.net` (13 `.webp`, 1 `.jpg`). |
| The Verge | `https://www.theverge.com/rss/index.xml`, Atom, 10 entries | `<img>` inside `<content type="html">`, which `parse_feed` uses. `<summary>` is shorter (349 vs 1496 characters on the first entry). 12 `<figure>`, 10 `<figcaption>`. Feed `<icon>`: 1. No `media:*` or `enclosure`. | 10 of 10 entries: 1 lead image each, one entry 2. | 6 of 11 non-empty (12–254 characters), 5 empty. `width`+`height` on 1 of 11. Host `platform.theverge.com` with query parameters `quality=90&strip=all&crop=…` (9 `.jpg`, 1 `.jpeg`, 1 `.webp`). |
| Terry Tao (WordPress.com) | `https://terrytao.wordpress.com/feed/`, RSS 2.0, 10 items | 11 `media:content medium="image"`: 10 are the author's Gravatar avatar (`1.gravatar.com/avatar/…?s=96`), 1 is the post image. 1 `<img>` in `content:encoded`, inside `<figure>`, with `width`/`height`. Channel `<image>` is the site icon (`secure.gravatar.com/blavatar/…`). | 1 of 10 items has a content image (`/2026/10/16/sair-open-math-os-released/`). | Empty alt. |
| YouTube (channel `UC_x5XG1OV2P6uZZ5FSM9Ttw`) | `https://www.youtube.com/feeds/videos.xml?channel_id=UC_x5XG1OV2P6uZZ5FSM9Ttw`, Atom, 15 entries | Each entry has a `media:group` with 1 `media:thumbnail` (`https://i1.ytimg.com/vi/<id>/hqdefault.jpg`, 480×360), 1 `media:content` (`application/x-shockwave-flash`, `https://www.youtube.com/v/<id>?version=3`, 640×390), and `media:description`. No `<img>`. | 1 thumbnail per entry. The first entry's link is a `/shorts/` URL. | None (thumbnails carry no alt). |

**Article pages: `og:image`**
- Simon Willison:
  - A post without images (`/2026/Oct/18/llm-tools-datasette/`, the #47 post) declares no `og:image` (`twitter:card` is `summary`).
  - A post with 2 feed images (`/2026/Oct/15/latex/`) declares `og:image` and `twitter:image` as `https://static.simonwillison.net/static/2026/latex-tool.webp`, which is the second of its two feed images. The first is `tiny-little-office.webp`.
- The Verge (`/policy/1013573/spd-officer-fired-flock-ice-husband`): `og:image` is the same Getty lead image as in the feed, with a different `crop` parameter. The page also declares `og:image:alt`, `og:image:type` (`image/jpeg`), 1200×628, and `twitter:image`.
- Terry Tao:
  - A post without images (`/2026/10/18/will-it-be-a-golden-age-or-a-dark-age-for-mathematics-and-science/`) declares `og:image` as the site blavatar (`secure.gravatar.com/blavatar/…?s=200`, 200×200, alt `""`).
  - The post with an image (`/2026/10/16/sair-open-math-os-released/`) declares `og:image` as `https://terrytao.wordpress.com/wp-content/uploads/2026/10/image-1.png` (1631×894, alt `""`), with `twitter:image` at `?w=640`.
- YouTube watch page (`/watch?v=LJ2v4-FvPcA`, one request): `og:image` and `twitter:image` are `https://i.ytimg.com/vi/LJ2v4-FvPcA/maxresdefault.jpg`, 1280×720.

**Image host headers**

Each image was requested once with `HEAD` and once with `GET`, each with no `Referer` and with `Referer: http://127.0.0.1:8800/`. All four requests per image returned the same status and body size.

| Image | Status (no Referer / with Referer) | Content-Type | Cross-Origin-Resource-Policy | Access-Control-Allow-Origin | Cache-Control | Size | Set-Cookie |
|---|---|---|---|---|---|---|---|
| `https://static.simonwillison.net/static/2026/latex-tool.webp` (Cloudflare) | 200 / 200 | `image/webp` | not sent | not sent | `max-age=31536000` | 172,126 B | none |
| `https://platform.theverge.com/wp-content/uploads/sites/2/2026/09/gettyimages-2265184860.jpg?quality=90&strip=all&crop=0,0,100,100` (nginx, `Vary: Accept`) | 200 / 200 | `image/jpeg` | not sent | `*` | `public, max-age=31536000` | 1,246,295 B | none |
| `https://terrytao.wordpress.com/wp-content/uploads/2026/10/image-1.png?w=1024` (nginx, `server-timing: a8c-cdn`, `Vary: Accept`) | 200 / 200 | `image/png` | not sent | not sent | not sent | 46,530 B | none |
| `https://i1.ytimg.com/vi/LJ2v4-FvPcA/hqdefault.jpg` (`sffe`) | 200 / 200 | `image/jpeg` | `cross-origin` | `*` | `public, max-age=300` | 12,290 B | none |

The YouTube thumbnail response also sent `Timing-Allow-Origin: *`, `X-Content-Type-Options: nosniff`, and `Cross-Origin-Opener-Policy-Report-Only: same-origin`.

## Related History

- Issue #47 and the planned change `keep-feed-text-when-extraction-misses` (commit `dba8ec8`, the current `main` head) modify `article_text` and the content-collection spec, with the extractor settings out of scope.
- Issue #48 ("Read linked pages and the author's replies in comments when summarizing an item", open). Its change folder has an untracked `research.md` from today that also covers `feeds.py` parsing and `plain_text`.
- D-013 (`docs/process/decision-log.md:84-102`): podcasts and YouTube are summarized from transcripts only, and descriptions and show notes are never summarized. The archived podcast design added a prompt statement that "no visuals were seen" (`openspec/changes/archive/2026-10-05-add-podcast-and-video-sources/design.md:279`), which is now `prompts.py:44`.
- D-015 (`decision-log.md:120-141`): owned CSS design system, a navigation-only service worker, and migration `0003` adding per-item `source_kind` and the digest `language` to the snapshot.
- D-018 (`decision-log.md:183-204`): one item per row, with the source line and title in page columns 4–6 and the summary in columns 7–12.
- `docs/proposal.md:4` notes that the proposal snapshot is text only; figures exist only in the PDF.
- `git log --grep` for image, img, or thumbnail finds only Docker image and release commits (`be97470`, `a0ba6e2`), no feature work on item images.
