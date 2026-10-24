# Research: a browser extension for CatchUp (issue #58)

- Date: 2026-10-20
- Query: What would a browser extension touch in CatchUp today? It might do two things: add the current site as a source, and bring in content the user can see while logged in, such as X posts with the author's replies. The query covers the HTTP API, how the server protects itself, the data model and the item pipeline, settings, the Sources page, the specs and docs, and external facts about browser extensions and X.
- Git ref: main @ f956842
- Method: three codebase research subagents, one external web-research subagent, and Claude's own reading and probes. External facts are marked **(external)** and cite their URL.

## Summary

- **Clients send only URLs, settings, and booleans.** The server fetches every page itself. No route accepts text or HTML from a client, and items are created in only two places: confirming a source, and checking a source's feed during a run.
- **Every item belongs to a source with a fetchable feed.** Each digest run fetches every source's `feed_url`. A source is one of three kinds, `feed`, `podcast`, or `youtube`, decided from the feed.
- **The server's only access control is a Host-header allow list** (default `localhost`, `127.0.0.1`, `[::1]`). It has no CORS, no CSRF protection, no authentication, and no Origin checks. A probe showed that a cross-site form POST with no body reaches `POST /api/digest-runs`.
- **Outbound fetches are public-address only**, and send no cookies or credentials. Pages behind a login therefore cannot be read by the server.
- **The docs place an extension "later".** It is a stretch feature. The handoff says logged-in content may come from "pages in the user's already logged-in browser with their authorization", but "do not read the user's saved passwords, and do not upload session cookies for general-purpose login" (`docs/handoff.md:55`). No spec mentions extensions.
- **External facts:**
  - A Chrome MV3 extension can fetch the local server from its service worker, if it has host permissions. Google has "no current plans" to apply Chrome's Local Network Access prompt to extensions.
  - X's Terms of Service prohibit "crawling or scraping the Services in any form". X's automation rules list scripting the website among practices that may lead to suspension. X's self-serve API is pay-per-use, at $0.005 per post read.

## Detailed Findings

### 1. HTTP API surface

- **Error shape.** Errors are `{"error": {"code", "message", ...}}`. A validation error returns 422 `invalid_request` with a fixed message, never echoing input — `backend/src/catchup/errors.py:17-36`.
- **Health.** `GET /api/health` returns `{"status": "ok"}` — `main.py:79-81`.
- **Source preview.** `POST /api/sources/preview` takes `{url}` — `api/sources.py:25-26, 66-92`.
  - **What it does:** it runs discovery — `sources/discovery.py:58-167`:
    - a feed URL;
    - an HTML page's `<link rel=alternate>`;
    - an Apple Podcasts lookup;
    - up to 8 same-origin path probes.
  - **What it returns:** `{feed_url, site_url, title, follows_site_feed_notice, kind, captions_enabled, entries[≤5]}`. It writes nothing.
  - **Caching:** the raw response is cached for 10 minutes under its final URL, at most 50 entries, none over 5 MiB — `net/feed_cache.py:12-34`.
- **Source confirm.** `POST /api/sources` takes `{feed_url}`, and returns 201 — `api/sources.py:29-30, 95-175`.
  - **Fetch:** it uses the cached preview, or `safe_fetch(feed_url)`, with no discovery.
  - **What it stores:**
    - the Source, with `input_url` set to the submitted feed URL (`:125-128`);
    - its items: the newest entries, at most `first_add_max` (5), within `first_add_days` (7), are `pending`, and the rest are `baseline` (`:119-138`);
    - a `SourceCheck`.
  - **Article text:** within the same request, it fetches the article page for short pending items (`:142-146`).
- **Source errors** — `api/sources.py:33-50`:
  - `invalid_url`, `blocked_address`, `fetch_failed` (with `http_status`), `feed_unavailable`, `rate_limited` (with `retry_after`), `no_feed`, `not_a_feed`;
  - `duplicate` (with `existing_source`): 422 on preview, 409 on confirm.
- **List and delete.**
  - `GET /api/sources` returns rows with the latest check — `api/sources.py:178-195`.
  - `DELETE /api/sources/{id}` returns 204 — `:198-204`.
- **Digest runs** — `api/runs.py:14-32`:
  - `POST /api/digest-runs` takes no body, returns 202, and starts a daemon thread.
  - **Refusals:** 409 `run_active`, or 409 `model_not_configured` — `digest/runner.py:127-138`.
  - `GET /api/digest-runs/active` and `GET /api/digest-runs/{id}` return run detail — `runner.py:410-437`.
- **Digests.** `GET /api/digests`, `GET /api/digests/latest`, and `GET /api/digests/{id}` read only snapshots — `api/digests.py:14-104`.
- **Settings** — `api/settings.py`:
  - `GET` and `PUT /api/settings/model` (`:78-109`);
  - `POST /model/test` (`:112-137`);
  - `GET` and `PUT /preferences`, partial updates (`:140-170`).
- **Static UI.** The SPA is served from the same origin, for any non-`/api` path — `main.py:83-102`.

### 2. How the server protects itself

- **Host allow list.** A custom middleware, `allowed_host`, checks the `Host` header — `main.py:50-77`.
  - It requires exactly one header, with no whitespace, path, or userinfo, and a port from 1 to 65535.
  - The hostname must be in `CATCHUP_ALLOWED_HOSTS` (default `localhost,127.0.0.1,[::1]`, `config.py:71-75`). The port is not checked against a list.
  - Anything else gets 400 `invalid_host`.
  - It was added after a DNS-rebinding finding (`docs/process/requirements-changes.md:16`), and is pinned by `tests/test_allowed_hosts.py`.
- **No CORS, CSRF, auth, or Origin checks.** There is no CORS middleware and no OPTIONS handler. There is no CSRF token, no API token or login, no cookies, and no Origin or Referer check anywhere in `backend/src/catchup/` — `main.py:50, 93` are the only middlewares.
  - `README.md:129-130` says CatchUp has "no login", and `local-deployment/spec.md:31` says "the instance has no login".
- **Claude's probe (2026-10-20, a throwaway instance with `TestClient`, Host `127.0.0.1:8000`, `Origin: https://evil.example`):**
  - **`POST /api/digest-runs`** with `Content-Type: application/x-www-form-urlencoded` and an empty body passed the host check and reached `start_run`. It returned 409 `model_not_configured`, because no model was configured. With a configured model, this request starts a run.
  - **`POST /api/sources/preview`** with `text/plain` returned 422 `invalid_request`. FastAPI 0.132 and later reject a body whose content type is missing or not JSON (https://fastapi.tiangolo.com/advanced/strict-content-type/). `backend/uv.lock:604` pins 0.142.2, but `backend/pyproject.toml:11` allows `>=0.115`.
  - **A CORS preflight** (`OPTIONS`, for `DELETE`) returned 405 with no `Access-Control-*` headers. Browsers therefore block cross-origin JSON, PUT, and DELETE requests.
- **Request limits.** There is no request body limit and no rate limit on incoming requests. The only concurrency guard is one active run at a time — `runner.py:128-131`.
- **Bind address and ports.**
  - `catchup serve` defaults to `127.0.0.1:8000` — `cli.py:14-18`.
  - The Docker image listens on `0.0.0.0:8000` — `Dockerfile:20-31`.
  - `compose.yaml:5-6` publishes `127.0.0.1:8000:8000`. The user's e2e container publishes `127.0.0.1:8800` instead (local setup, not in the repo).
  - The Vite dev server proxies `/api` to `127.0.0.1:8000` — `frontend/vite.config.ts:7-8`.
- **`CATCHUP_SECRET_KEY`** encrypts only the provider API key, with Fernet over `sha256(secret)` — `crypto.py:11-18`; `models.py:43`. The key is never returned, and never sent to a changed base URL — `api/settings.py:92-95, 121-122`.
- **Service worker and PWA.**
  - The service worker is registered with scope `/` in production — `frontend/src/main.tsx:8-9`.
  - It precaches only `/offline.html`, and handles only failed navigations. It does not intercept API calls — `frontend/public/sw.js:1-29`; `src/sw.test.ts:73`.
  - The manifest has `start_url "/"` and `scope "/"` — `public/manifest.webmanifest:4-6`.
- **Frontend client.** It calls same-origin `fetch('/api' + path)` with no auth headers — `frontend/src/api/client.ts:14-33`.

### 3. Outbound fetching (what the server can read)

- **`safe_fetch`** — `net/safe_fetch.py`:
  - **Requests:**
    - http(s) only, with no userinfo (`:76-79`);
    - DNS is checked before every hop, and non-global, private, loopback, link-local, and NAT64-wrapped private addresses are refused (`:72-97`).
  - **Limits:**
    - at most 5 redirects;
    - a 5 MiB body limit, or 32 MiB for feeds;
    - a 30 s deadline;
    - one retry on short `Retry-After` (`:18-20, 105-178`).
  - **No credentials:** it sends no cookies or credentials, only a `CatchUp/<version>` User-Agent, with `trust_env=False` (`:34-41, 113`).
  - **Host spacing:** requests to one host are at least 1 s apart — `net/host_spacing.py:10-27`.
- **robots.txt** is checked only for context fetches (#48), once per origin, against a shared budget of 60 per run — `context/robots.py:9-32`; `context/gather.py:23, 50`.
- **Login pages.** Context links to login or share pages, and to `x.com` and `twitter.com`, are dropped, and a redirect to a login page is not stored — `context/links.py:16-49`; content-collection spec, "Gather related context for website items".
- **Not through `safe_fetch`:**
  - the model provider (the OpenAI SDK, `llm/client.py:66-68`);
  - YouTube captions (`transcripts/youtube.py:20-34`).

### 4. Data model and item identity

- **Source** — `models.py:60-71`. Fields: `title`, `site_url`, `feed_url` (**unique**), `input_url`, `kind` (`"feed"` by default), `created_at`, `last_check_at`, `last_check_status`.
- **Item** — `models.py:74-102`:
  - **Keys:** **`UniqueConstraint(source_id, identity_key)`** (`:77`), and an index on `(source_id, link)`. `source_id` cascades on delete.
  - **Non-null:** `identity_key`, `link`, `title`, `content_text`, `content_origin`, `state`.
  - **Nullable:**
    - `published_at`;
    - `summary` and `summary_language`;
    - `transcript_status`;
    - `entry_links`;
    - `comments_url`, `comment_feed_url`, `comment_count`, and `entry_author`;
    - `context_status`;
    - `image_candidates` and `summary_images`.
- **ItemContext** (#48) — `models.py:105-116`. Fields: `ref`, `kind`, `url`, `title`, `text`, `position`, `used`. It cascades with its item.
- **Runs and checks:**
  - **SourceCheck** — `models.py:119-131`: `status`, `possible_gap`, `error`, `http_status`, counts.
  - **DigestRun** — `:134-151`: status, progress, tokens, and errors.
- **Digests:**
  - **Digest** — `:154-164`.
  - **DigestTopic** — `:167-175`: kind is `topic` or `creator_updates`.
  - **DigestItem** — `:178-195`: it snapshots `title`, `link`, `source_name`, `source_kind`, `published_at`, `summary`, `context_links`, and `images`. Its `item_id` is `SET NULL` on delete, so snapshots survive a source deletion.
- **AppSettings** — `models.py:49-57`. A single row: `digest_language`, `youtube_captions`, `youtube_skip_shorts`, `show_images`.
- **Migrations.** The head is `0005_item_images` — `migrations/versions/0005_item_images.py:7`. Migrations run at startup — `db.py:32-36`; `main.py:32`.

### 5. Source kinds

- **How the kind is decided** — `Feed.kind`, `sources/feeds.py:281-287`:
  - `youtube` if the final URL is a YouTube `/feeds/videos.xml` (`:355-356`);
  - `podcast` if more than half the entries have audio enclosures (`:330-331, 357`);
  - otherwise `feed`.
- **When it is set.** At confirm — `api/sources.py:127`. Collection can upgrade a `feed` source to another kind, and never downgrades — `collection.py:96-97`.
- **Where code branches on kind:**
  - collection — `collection.py:113, 126-128, 134, 147`;
  - confirm — `api/sources.py:136-141`;
  - the context pass, which reads feed items and podcast text posts only — `context/gather.py:28, 33`;
  - `select_pending` and the caption pass — `runner.py:45-70`;
  - the snapshot's `source_kind` — `runner.py:317, 354, 383`;
  - the digest API — `api/digests.py:71, 84-89`;
  - the frontend `SourceKind` type — `frontend/src/components/ui.tsx:43-46`;
  - the frontend: `frontend/src/pages/Sources.tsx:59-76, 221-222`, `pages/Home.tsx:305-307`, `components/DigestArticle.tsx:81, 108`.
- **Social sites.** Bluesky, Mastodon, and Reddit work only through their RSS feeds, as `feed` sources.
  - The Sources copy names Bluesky and Mastodon — `Sources.tsx:207, 236`; `:184` says "social profiles".
  - Reddit is named in `README.md:179`, and its support ends on 2026-11-13 — `README.md:222-223`.
  - X is not supported — `README.md:229-230`.

### 6. How an item flows to a digest (fields read and written)

- **The feed entry.** `FeedEntry` — `sources/feeds.py:250-264`. Fields: `identity_key`, `link`, `title`, `published_at`, `content_text`, `has_audio`, `transcripts`, `links`, `comments_url`, `comment_feed_url`, `comment_count`, `author`, `images`.
  - **Identity:** the entry id, else the link when it is not shared, else `sha256(title + published)` (`:318-320`).
- **Collection.** `check_source` — `collection.py:76-165`:
  - **Fetch:** it fetches `source.feed_url`; on failure it records a failed check.
  - **New entries:** it skips known identity keys and known links, and writes every Item field. The state is `pending`, or `baseline` for skipped Shorts.
- **Content origin:**
  - `article_text` (`collection.py:55-73`) keeps the feed text when it has at least 500 characters. Otherwise it fetches the page and extracts it with trafilatura: the result is the article, or the feed text plus the article.
  - The `content_origin` values are `feed`, `article`, and `transcript` (`:46`; `runner.py:107`).
- **Transcripts.**
  - Podcast transcript resolution — `collection.py:36-52, 113-123`.
  - The YouTube caption pass, keyed by the `yt:video:` identity — `runner.py:64-110`.
- **The context pass** — `context/gather.py:21-161`:
  - **Reads:** `link`, `entry_links`, `comment_count`, `comment_feed_url`, `entry_author`.
  - **Writes:** `ItemContext` rows, and `context_status` (`gathered` or `none`). It clears a cached summary when rows were stored.
  - **Caps:**
    - 3,000 characters per link, and 16,000 for all links (`:84, 108`);
    - author replies: 10, and 4,000 characters (`context/comments.py:17-24`).
- **Image candidates** (#49). `_entry_images` — `feeds.py:94-133`: at most 8; no avatars, 1×1 pixels, or channel images; none for entries with audio.
- **Selecting items to summarize.** An item is summarized when its transcript status is `found` or `text`, or is null on a feed source — `select_pending`, `runner.py:38-61`.
- **The summary call:**
  - **Input:** `SummaryInput` — `summarize.py:15-25`, built at `runner.py:224-232`.
  - **Cache:** a summary is reused when its language matches — `summarize.py:146`.
  - **Long items:** they are split into parts, and long transcripts use their own prompt — `summarize.py:81-100`.
  - **Images:** at most 3 are chosen — `:125`.
  - **What `record` writes:** `summary`, `summary_language`, `summary_images`, and `ItemContext.used` — `runner.py:274-289`.
- **Grouping.** `GroupItem(id, title, source_name, summary)` — `runner.py:302-308`; `digest/group.py:45-96`.
- **Creator updates.** Items without a summary, with a reason — `runner.py:35-58, 364-388`.
- **The snapshot.** `DigestItem` copies the item's fields, and the item becomes `delivered` — `runner.py:313-393`.

### 7. Assumptions that tie items to a fetchable feed

- **Where items are created.** Only `confirm` (`api/sources.py:147`) and `check_source` (`collection.py:136`) create items.
- **Every run fetches every source.** It starts from `source.feed_url` — `runner.py:184, 206-211`.
- **`link` is required.** The context pass fetches `item.link` for author replies — `context/gather.py:119`.
- **`published_at` is nullable.** At first add, entries without a date are never pending — `api/sources.py:119-124`. It is also a sort key in the snapshot — `runner.py:374`.
- **`possible_gap`.** It is set when no previously seen entry is matched — `collection.py:104-107, 157`.
- **No new content.** A run with nothing to summarize and no creator updates ends as `no_new_content` — `runner.py:262-269`.
- **Deleting a source** cascades to its items, contexts, and checks. Digests keep their snapshots — `api/sources.py:198-204`; `models.py:82, 109, 124, 185`.

### 8. Settings and environment

- **Preferences:** `digest_language` (1–40 characters), `youtube_captions`, `youtube_skip_shorts`, `show_images` — `api/settings.py:140-170`.
- **Environment** (`config.py:30-78`), with defaults:
  - **First add:** `CATCHUP_FIRST_ADD_DAYS` 7, `CATCHUP_FIRST_ADD_MAX` 5.
  - **Content:**
    - `CATCHUP_SHORT_TEXT_CHARS` 500;
    - `CATCHUP_LONG_ITEM_CHARS` 20000;
    - `CATCHUP_SINGLE_CALL_CHARS` unset.
  - **Context:**
    - `CATCHUP_LINKS_PER_ITEM` 8;
    - `CATCHUP_CONTEXT_FETCHES_PER_RUN` 60;
    - `CATCHUP_AUTHOR_REPLIES` true.
  - **Captions and transcripts:** `CATCHUP_CAPTIONS_PER_RUN` 20, `CATCHUP_CAPTION_WAIT_HOURS` 24, `CATCHUP_TRANSCRIPT_WAIT_DAYS` 7.
  - **Grouping:** `CATCHUP_GROUPING_BATCH_CHARS` 200000.
  - **Feeds:** `CATCHUP_MAX_FEED_BYTES` 32 MiB.
  - **Server:**
    - `CATCHUP_ALLOWED_HOSTS`;
    - `CATCHUP_SECRET_KEY`;
    - `CATCHUP_USER_AGENT_CONTACT`;
    - `CATCHUP_DATA_DIR`;
    - `CATCHUP_FRONTEND_DIST`.

### 9. Frontend Sources page

- **Preview.** A `type=url` input; typing clears the preview. Submitting POSTs `/sources/preview` — `frontend/src/pages/Sources.tsx:146-155, 187-190`.
- **What the preview shows:** title, kind badge, feed and site URLs, method text, the follow-site notice, and 5 entries — `Sources.tsx:56-87`.
- **Confirm.** It POSTs `/sources` with `{feed_url}` only — `Sources.tsx:157-169`.
- **Errors.** Messages per error code and HTTP status. A network failure shows "Could not connect to CatchUp." — `Sources.tsx:21-53`.
- **Listing and delete.** Each row shows a kind and status chip. Delete has an inline confirmation — `Sources.tsx:89-101, 135-144, 171-181, 209-219`.

### 10. External facts: Chrome Manifest V3 **(external)**

- **Content scripts.**
  - **How they are injected:** statically, through `content_scripts`, or programmatically, with `scripting.executeScript`. The second needs host permissions, or `activeTab`.
  - **What they can do:** they read and modify the page DOM in an isolated world, and call only a few extension APIs directly — https://developer.chrome.com/docs/extensions/develop/concepts/content-scripts
  - **Their fetches:** since Chrome 85, they are subject to CORS and carry the page's origin. Chrome advises relaying them through the background context — https://www.chromium.org/Home/chromium-security/extension-content-script-fetches/
- **Permissions.**
  - **`activeTab`:** it grants temporary access to the current tab after a user gesture, such as "executing an action", a context menu, or a shortcut. It shows no install warning. Whether opening a popup counts is not stated, so it is **unverified** — https://developer.chrome.com/docs/extensions/develop/concepts/activeTab
  - **`host_permissions`:** they allow fetches to the listed hosts, and show install warnings. They can be optional, and are then requested at runtime inside a user gesture — https://developer.chrome.com/docs/extensions/develop/concepts/declare-permissions ; https://developer.chrome.com/docs/extensions/reference/api/permissions
  - **Ports:** a match pattern without a port matches any port, so `http://localhost/*` covers :8000 and :8800 — https://developer.chrome.com/docs/extensions/develop/concepts/match-patterns
- **The service worker.**
  - **Lifetime:** Chrome stops it after 30 s idle, after 5 min on one request, or when a fetch response takes longer than 30 s — https://developer.chrome.com/docs/extensions/develop/concepts/service-workers/lifecycle
  - **Cross-origin fetches:** host permissions allow extension pages and the service worker to request other origins — https://developer.chrome.com/docs/extensions/develop/concepts/network-requests. That extension pages bypass CORS is stated by Chromium — https://www.chromium.org/Home/chromium-security/extension-content-script-fetches/
  - **The Origin header** the server sees for such a fetch (`chrome-extension://<id>`) is **unverified** in official docs.
- **Local Network Access.**
  - **For web pages:** Chrome 142 prompts before public sites send requests to loopback or local addresses — https://developer.chrome.com/blog/local-network-access
  - **For extensions:** Google has "no current plans" to apply it, and extensions with correct host permissions are not affected. The fact-check also found reports of an early Chrome 142/143 bug that blocked extension service-worker fetches to localhost, fixed in Chrome 144 (**unverified** here) — the LNA adoption guide (updated 2026-05-18), https://docs.google.com/document/d/1QQkqehw8umtAgz5z0um7THx-aoU251p705FbIQjDuGs/mobilebasic ; https://groups.google.com/a/chromium.org/g/chromium-extensions/c/pUDh8RiTjJk
  - **Content scripts and navigations:** whether content-script fetches (page origin), or top-level form navigations, trigger the prompt is **unverified**.
- **Messaging and storage.**
  - **`externally_connectable`:** without it, no web page can message the extension — https://developer.chrome.com/docs/extensions/reference/manifest/externally-connectable
  - **Messaging:** messages from content scripts should be treated as possibly crafted by an attacker — https://developer.chrome.com/docs/extensions/develop/concepts/messaging
  - **`chrome.storage`:** `local` holds 10 MB; `session` is in memory and hidden from content scripts by default — https://developer.chrome.com/docs/extensions/reference/api/storage
- **Interface options:**
  - the Side Panel API, from Chrome 114 — https://developer.chrome.com/docs/extensions/reference/api/sidePanel
  - context menus, which also grant `activeTab` — https://developer.chrome.com/docs/extensions/reference/api/contextMenus
- **Installing.**
  - **Unpacked:** chrome://extensions, Developer mode, then Load unpacked — https://developer.chrome.com/docs/extensions/get-started/tutorial/hello-world
  - **Developer mode:** from Chrome 134, unpacked extensions stay enabled only while Developer mode is on — https://groups.google.com/a/chromium.org/g/chromium-extensions/c/cTdMVtxxooY
  - **A stable ID:** the manifest `key` keeps the extension ID stable — https://developer.chrome.com/docs/extensions/reference/manifest/key
- **Edge** runs the same MV3 code, including `sidePanel`, `scripting`, `storage`, and `contextMenus` — https://learn.microsoft.com/en-us/microsoft-edge/extensions/developer-guide/api-support

### 11. External facts: Firefox and Safari **(external)**

- **Firefox.**
  - **MV3:** generally available since Firefox 109 — https://extensionworkshop.com/documentation/develop/manifest-v3-migration-guide/. It uses `background.scripts` (an event page), not `background.service_worker`; MDN advises declaring both keys — https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/manifest.json/background
  - **Host permissions:** the user can revoke them — https://developer.mozilla.org/en-US/docs/Mozilla/Add-ons/WebExtensions/manifest.json/host_permissions
  - **Signing:** release Firefox installs only Mozilla-signed add-ons, listed or unlisted on AMO — https://extensionworkshop.com/documentation/publish/signing-and-distribution-overview/
  - **Temporary add-ons:** they are removed on restart — https://extensionworkshop.com/documentation/develop/temporary-installation-in-firefox/
- **Safari.**
  - **Packaging:** extensions are packaged into an Xcode app with `xcrun safari-web-extension-packager` — https://developer.apple.com/documentation/safariservices/packaging-a-web-extension-for-safari
  - **Unsigned extensions:** they load only with "Allow unsigned extensions", which resets when Safari quits. "Add Temporary Extension…" loads one that is removed after 24 hours or when Safari quits — https://developer.apple.com/documentation/safariservices/running-your-safari-web-extension
  - **Unverified:** whether a free Apple account is enough for a local macOS extension, and whether Safari extension fetches to `http://localhost` work.

### 12. External facts: X **(external)**

- **Terms of Service** (effective October 9, 2026, https://x.com/en/tos):
  - Without prior written consent, "crawling or scraping the Services in any form, for any purpose" is prohibited.
  - Accessing the Services by any means other than X's published interfaces is also prohibited.
  - **Liquidated damages:** $15,000 per 1,000,000 posts, above 1,000,000 posts in 24 h.
  - **Browser extensions** and user-initiated copying are not mentioned.
- **Automation rules** (updated April 2026, https://help.x.com/en/rules-and-policies/x-automation): non-API automation, such as scripting the X website, is listed among things not to do, and may lead to permanent suspension.
- **Developer Policy** (https://docs.x.com/developer-terms/policy): apps need users' "express and informed consent" for actions taken on their behalf. Up to 500 Post or User objects may be shared with each person per day, by non-automated means such as downloads.
- **API pricing** (https://docs.x.com/x-api/getting-started/pricing):
  - Pay-per-use is the self-serve plan; Enterprise is still offered. A post read costs $0.005, a user read $0.010. Reads are capped at 3M posts per month. A $20 credit comes after the first credit purchase. Repeat reads within the same UTC day are deduplicated, which X calls a soft guarantee.
  - Pay-per-use launched on 2026-02-06, when Basic and Pro "remain available" — https://devcommunity.x.com/t/announcing-the-launch-of-x-api-pay-per-use-pricing/256476. Migrations of Basic start after 2026-06-01 and of Pro after 2026-09-01 — https://devcommunity.x.com/t/important-update-legacy-x-api-basic-plans-are-moving-to-pay-per-use-ppu/266305 ; https://devcommunity.x.com/t/important-update-legacy-x-api-pro-plans-are-moving-to-pay-per-use-ppu/273255

### 13. External facts: reading pages the user views **(external)**

- **User data.** Chrome Web Store policy treats website content and browsing activity as user data, even when it is processed on the device — https://developer.chrome.com/docs/webstore/program-policies/user-data-faq
- **Limited Use.** Data may be used only for the disclosed single purpose, with prominent disclosure, consent, and a privacy policy — https://developer.chrome.com/docs/webstore/program-policies/limited-use
- **Login restrictions.** Extensions must not facilitate circumventing login restrictions — https://developer.chrome.com/docs/webstore/program-policies/policies

## Code References

- `backend/src/catchup/main.py:50-77` — the Host allow-list middleware; the only access control.
- `backend/src/catchup/main.py:83-102` — the SPA and static files on the same origin.
- `backend/src/catchup/config.py:30-78` — environment settings, including `allowed_hosts` at `:71-75`.
- `backend/src/catchup/api/sources.py:25-30, 66-204` — preview, confirm, list, delete.
- `backend/src/catchup/api/runs.py:14-30` — start (no body) and poll runs.
- `backend/src/catchup/digest/runner.py:38-61, 127-138, 184-211, 224-232, 274-393` — pending selection, run start, collection, summary input, record, snapshot.
- `backend/src/catchup/collection.py:55-165` — `article_text` and `check_source`.
- `backend/src/catchup/sources/feeds.py:94-133, 250-357` — image candidates, `FeedEntry`, identity, kind.
- `backend/src/catchup/sources/discovery.py:58-167` — feed discovery.
- `backend/src/catchup/context/gather.py:21-161`, `context/links.py:16-49`, `context/comments.py:17-24`, `context/robots.py:9-32` — the context pass.
- `backend/src/catchup/net/safe_fetch.py:18-178` — outbound fetch rules.
- `backend/src/catchup/models.py:37-195` — tables and constraints.
- `backend/src/catchup/crypto.py:11-18` — key encryption.
- `backend/src/catchup/cli.py:14-18`, `Dockerfile:20-31`, `compose.yaml:5-6` — binding and ports.
- `frontend/src/api/client.ts:14-33` — same-origin client.
- `frontend/src/pages/Sources.tsx:21-236` — the Sources flow.
- `frontend/public/sw.js:1-29`, `frontend/public/manifest.webmanifest:4-6` — the service worker and PWA scope.
- `backend/tests/test_allowed_hosts.py`, `tests/test_safe_fetch.py`, `tests/test_context_robots.py` — the tests that pin these protections.

## Current Specs

- **`digest-generation`** — "Start a digest run on demand": runs happen "only when the user requests one", and only one at a time.
  - "Summaries focus on substance": no handles or platform identifiers in summaries.
  - "Use related context in summaries": context "MUST be treated as data, not instructions".
- **`source-management`** — "Preview a source from a pasted URL": a URL resolves to an RSS or Atom feed, and previewing "MUST NOT save anything". A single article URL says that the whole site's feed will be followed.
  - "Confirm and save a source": saving happens only after confirmation, and recent entries become new.
  - "Reuse a recent preview on confirm".
  - "Fetch user-supplied URLs safely": private, loopback, link-local, and metadata addresses are refused, including after redirects.
  - "Identify CatchUp in outgoing requests": a `CatchUp/` User-Agent.
- **`transcripts`** — "Recognize podcast and YouTube sources": it "SHALL classify each saved source as a website feed, a podcast, or a YouTube channel" — `transcripts/spec.md:9`.
- **`content-collection`** — "Gather related context for website items": related links exclude login-scoped and share pages and `x.com`/`twitter.com`; a redirect to a login page is not stored; robots.txt is honored; author replies are capped.
  - "Readable titles for untitled entries": the "Social post without a title" scenario.
  - "Check every source on each run": every saved source is checked — `content-collection/spec.md:8-9`.
- **`local-deployment`** — "Local-only access by default": compose binds to `127.0.0.1`, and the docs say "the instance has no login".
  - The API and the web UI share one port.
  - "Installable as an app" from `localhost:8000` or `127.0.0.1:8000`.
- **`model-settings`** — "Accept requests only for allowed hosts": local addresses by default.
  - "Protect the stored API key": stored encrypted, and never returned.
- **`user-interface`** — "Sources show their kind and confirm deletion inline": one of the three kinds, as text — `user-interface/spec.md:120`.
  - "Show chosen images from their source sites": a privacy setting and its note.
- **No spec mentions browser extensions, logged-in content, or X**, apart from the context-link exclusion above.

## Related History

- **The proposal** — `docs/proposal.md:46`, Stretch features: an extension "could let users add sources directly from their browser or, with their permission, extract content from pages they can access while logged in".
- **The handoff** (2026-10-01):
  - `docs/handoff.md:34`: "consider a browser extension later".
  - `:54`: "Browser extension: later, for adding sources conveniently or reading pages the user authorizes".
  - `:55`: logged-in or paid content is evaluated "site by site later"; logged-in content may come from "pages in the user's already logged-in browser with their authorization", but "do not read the user's saved passwords, and do not upload session cookies for general-purpose login".
  - `:75`: "no need to add multi-agent systems, microservices, or extensions just to look substantial".
- **`AGENTS.md:12`** — "Browser extensions, authenticated content, existing-page change detection, and automatic scheduling are not initial-release requirements."
- **Decisions:**
  - D-006 (2026-10-02): the JSON API "is reusable by the planned browser extension" — `docs/process/decision-log.md:38-39`.
  - D-011: local deployment only.
  - D-014: a PWA, no native packaging.
  - D-020: context drops login pages and `x.com`.
  - No decision covers the extension itself.
- **Requirement changes** — `docs/process/requirements-changes.md`:
  - `:10`: the extension and logged-in content moved to stretch.
  - `:15` (2026-10-02): X is not supported; later options are "a user-supplied X API key, or the browser extension".
  - `:16`: allowed hosts were added after DNS rebinding.
- **User feedback** — `work/user-feedback.md`, local:
  - **F5** (2026-10-17): X accounts do not work; tracked by #41. The user treated it as part of the extension work.
  - **F8** (2026-10-19): read the author's replies and interactions. The X part depends on #41; the blog part was done in #48.
- **The course** — `docs/handoff.md:83-88`: Alpha due 2026-11-05, and the final demo and report due 2026-12-10.
- **Issues:**
  - **#41** (X accounts): "This belongs to the later browser-extension work".
  - **#58** (this change): two possible uses, local-only, user-initiated collection, and site terms.
