# Research: following X (Twitter) accounts

- Date: 2026-10-24
- Query: How do sources, keys, the browser extension, and saved X posts work today, and what does the official X API offer, so that a user can follow X accounts with their own X API credentials (#41)?
- Git ref: main @ f1b76c0

## Summary

- **Sources.** CatchUp follows sources of four kinds, stored as plain strings: `feed`, `podcast`, `youtube`, and the built-in `capture`.
  - A pasted URL is previewed by feed discovery, and confirmed by saving the source.
  - At confirm, recent entries become `pending`, and the rest `baseline`.
  - Each digest run checks every source except `capture`, gathers context, and summarizes `pending` items.
- **X today.** X accounts cannot be followed:
  - discovery has no X case, so a profile URL ends in a generic error;
  - the extension's popup says so on every X page;
  - README and the specs state it.
- **Saving X posts.** Since #58, the extension can save one X post with the author's visible replies, on the user's click. It appears in the digest as "X · Name", with an "author replies" context part.
- **The model key.** It is stored with Fernet encryption, derived from `CATCHUP_SECRET_KEY`. Only its last four characters are returned. It is never sent to a changed provider address.
- **The extension token.** It opens only a fixed list of routes.
- **The X API (v2, pay-per-use since 2026-02-06).**
  - **Endpoints:** a user lookup by username, and a user-posts timeline with `since_id`.
  - **Author replies:** a 7-day recent search can find an author's replies in a thread.
  - **Prices:** $0.005 per post read and $0.010 per user read, deduplicated per UTC day.
  - **Policy:** asks developers to keep stored posts in sync with deletions, and forbids using credentials owned by others.

## Detailed Findings

### 1. Source kinds and the data model

- `Source.kind` is a `String(16)` defaulting to `"feed"`. There is no enum or CHECK constraint anywhere — `backend/src/catchup/models.py:78`.
  - Other source columns: `title`, `site_url`, `feed_url` (unique), `input_url`, `last_check_at`, `last_check_status` — `models.py:70-81`.
- **How a feed's kind is decided:** `youtube` when the host is youtube.com and the path is `/feeds/videos.xml`; `podcast` when more than half the entries have audio; otherwise `feed` — `sources/feeds.py:288-294,362-364`.
- **`capture`** is one fixed source, with `feed_url="catchup:captures"`, created by the extension API — `api/extension.py:109-123`.
- **Items:**
  - unique on `(source_id, identity_key)`, with an index on `(source_id, link)` — `models.py:86-89`;
  - columns include `identity_key`, `link`, `title`, `published_at`, `content_text`, `content_origin`, `state`, `transcript_status`, `entry_links`, `entry_author`, `site_name`, `captured_replies`, `context_status`, `image_candidates`, and `summary_images` — `models.py:84-114`.
- **`state`:**
  - `pending` — `api/sources.py:135`, `collection.py:134-135`, `api/extension.py:154`;
  - `baseline` — `api/sources.py:135-137`, `runner.py:78`;
  - `delivered` — `runner.py:366,391`.
- **`content_origin`:**
  - `feed` and `article` — `collection.py:58-73`;
  - `transcript` — `collection.py:46`, `runner.py:107`;
  - `capture` — `api/extension.py:174`.
- **`DigestItem.source_kind`** is a snapshot of the kind — `models.py:201`.
- **Migrations, by what each one added** (`backend/src/catchup/migrations/versions/`):
  - `0002_transcripts.py:14-33`: `sources.kind`;
  - `0003`: `digest_items.source_kind`;
  - `0004`: the context columns and `item_contexts`;
  - `0005`: images;
  - `0006_captures.py:14-24`: `extension_tokens`, `items.site_name`, `items.captured_replies`. Its downgrade deletes `capture` sources (`:28`).

### 2. Adding a source: preview and confirm

- **Preview.** `POST /api/sources/preview` calls `discover()` — `api/sources.py:66-92`, `sources/discovery.py:58-167`. The order of steps:
  1. an Apple Podcasts URL goes through an iTunes lookup (`:60-73`);
  2. the URL is fetched, and a feed is accepted directly (`:96-108`);
  3. the HTML `<link rel=alternate>` candidates are tried (`:110-137`);
  4. up to 8 same-origin path probes (`:14,50-55,143-164`);
  5. otherwise the page's HTTP error, or `no_feed` (`:165-167`).
- **The preview response:** `feed_url`, `site_url`, `title`, `follows_site_feed_notice`, `kind`, `captions_enabled`, and up to 5 entries — `api/sources.py:81-92`.
  - A successful discovery caches the feed response for 600 s (50 entries) — `discovery.py:75-79`, `net/feed_cache.py:12-34`.
- **Confirm.** `POST /api/sources` saves the source, then for each entry:
  - up to `FIRST_ADD_MAX` entries (5), published within `FIRST_ADD_DAYS` (7), become `pending`;
  - all others become `baseline`;
  - YouTube Shorts become `baseline` when "skip Shorts" is on;
  - article text is fetched only for pending items.

  It also writes a `SourceCheck` with `run_id=None` — `api/sources.py:95-175`, at `:119-146` and `:158-162`.
- **Baseline items are never summarized:** the runner selects only `pending` items — `digest/runner.py:220`.
- **Duplicates** match on the final `feed_url`: preview answers 422 `duplicate`, and confirm 409 — `api/sources.py:42-50,73-75,111-113,163-170`.
- **Error codes:**
  - from fetching: `invalid_url`, `blocked_address`, `fetch_failed` — `net/safe_fetch.py:79-97,149-191`;
  - from discovery: `rate_limited`, `no_feed`, `not_a_feed`, `feed_unavailable`;
  - all are returned as 422, with `retry_after` or `http_status` details — `api/sources.py:33-39`.
- **X in discovery.** There is no special case for `x.com` or `twitter.com`, so a profile URL goes through the generic path.

### 3. Source checks and collection in a run

- **`check_source`** — `collection.py:76-165`:
  - a `FetchError` or `FeedParseError` becomes a `failed` `SourceCheck`, with the error and `http_status` (`:80-94`);
  - entries are matched by `identity_key` or by link (`:99-125`);
  - new entries are `pending` (`:133-135`);
  - `possible_gap` is set when no known entry matched (`:104-107,157`).
- **Identity keys:**
  - feeds: the entry id or guid, else the link, else a hash of title and date — `sources/feeds.py:325-327`;
  - YouTube video ids come from `yt:video:<id>` — `runner.py:92-93`;
  - captures: the normalized URL, with `#<time>` added after delivery — `api/extension.py:139-155`.
- **`start_run`** refuses with 409 `run_active`, or with `model_not_configured` — `runner.py:127-139`.
- **`run_digest`** — `runner.py:168-410`:
  - it checks every non-`capture` source in id order, with a shared `HostSpacer` (`:184-186,208-213`);
  - then `caption_pass` (`:214`), and `gather_context` for kinds `feed`, `podcast`, and `capture` (`:215`; `context/gather.py:28`);
  - `select_pending` sends `found`/`text` transcript items, and `feed`/`capture` items with no transcript status, to the summarizer (`:38-61`, at `:45`);
  - the source checks are rewritten from what was included (`:239-260`).
- **Error containment.** Only fetch and parse errors are contained per source. Any other exception fails the run as `run_failed` — `runner.py:403-410`.
- **Stages:** `queued` → `collecting` → `summarizing` → `grouping` → `succeeded` / `no_new_content` / `failed` — `runner.py:32,202,273,302,333,392`.
- **Counts:** `sources_total` counts sources whose kind is not `capture` — `runner.py:433`. `source_checks` carry `rate_limited` — `:434-439`.

### 4. Kind labels in the user interfaces

- **`frontend/src/components/ui.tsx:43-54`:**
  - `SourceKind = 'feed' | 'podcast' | 'youtube' | 'capture'`;
  - `kindNames`: "Website feed", "Podcast", "YouTube channel", "Saved from browser";
  - `KindIcon` renders nothing for an unknown kind.
- **`frontend/src/components/Icon.tsx:1-2,9-12`:** icons `podcast`, `youtube`, `feed`, `capture`.
- **`frontend/src/pages/Sources.tsx`:**
  - kinds in the `Preview` and `Source` types (`:10-19`);
  - the method text depends on the kind (`:59-63`);
  - row badges (`:221-222`);
  - "N pages waiting" for captures (`:223-225`);
  - copy mentioning social profiles and Bluesky/Mastodon (`:184,206-207,237`).
- **`frontend/src/pages/Home.tsx`:** captures are excluded from the source count (`:217`); the rail counts podcasts, YouTube, and websites (`:306-308`).
- **`frontend/src/components/DigestArticle.tsx`:** `source_kind` types (`:10-21`), and `KindIcon` (`:81,108`).
- **`extension/src/popup.ts:228-233`:** `kindLabels` for `feed`, `podcast`, and `youtube`, falling back to the raw kind.

### 5. The model API key: storage and protection

- **Encryption.** Fernet, keyed by `urlsafe_b64encode(sha256(CATCHUP_SECRET_KEY))` — `crypto.py:11-26`.
  - A missing secret raises `secret_not_configured` (400).
  - There is no rotation.
  - The secret is read at `config.py:33,57`, and the server starts without it.
- **Storage.** A single `model_config` row (id 1): `base_url`, `model_id`, `api_key_encrypted`, `api_key_last4`, `context_window`, `updated_at` — `models.py:37-46`.
- **Routes** (prefix `/api/settings`, `api/settings.py:20`):
  - `GET /model` returns `{base_url, model_id, key_set, api_key_last4}` — `:57-63,78-80`;
  - `PUT /model` — `:83-109`:
    - an empty key keeps the stored one only when `base_url` is unchanged;
    - otherwise it answers `api_key_required`, or `missing_api_key` when nothing is saved;
  - `POST /model/test` never sends the stored key to a changed URL — `:112-137`, at `:121-122`:
    - errors map to 401 (auth), 402 (balance), 429 (rate limit), and 502 (connection or provider);
  - there is no route to delete the key;
  - the validation handler never echoes the body — `errors.py:31-36`.
- **When the key is decrypted.** A run decrypts it at `runner.py:183`. A failure ends the run with "Check the model settings and instance secret." — `:401-402`.
- **Docs:** README `:29-34` (generating the secret), `:61-62` (no key to a new address), and `:166-174` (Docker; keep the secret). Also `.env.example:1-3`.
- **Tests:** `backend/tests/test_crypto.py:7-19`, `test_settings_api.py:49-181`.

### 6. The Settings page

- **The first-run lede:** "Three quick steps, and an optional browser extension. Your key stays on this computer, encrypted." — `frontend/src/pages/Settings.tsx:181-183`.
- **One model `<form>`** holds:
  - Step 1, Model provider (`:185-215`);
  - Step 2, Digest (`:216-233`);
  - Step 3, YouTube (`:234-242`);
  - the Save bar (`:243-245`).

  Save sends `PUT /settings/model`, then `PUT /settings/preferences` (`:155-175`).
- **Step 4, "Browser extension,"** is outside that form, with its own Connect form, a token shown once, and the list of connections — `:247-275`.
- **The key field:**
  - a password input that is never filled with the saved key;
  - it shows "Saved key ending in …", and the placeholder "Paste a new key to replace it";
  - it is cleared after Save;
  - there is no remove control — `:74,192-200,172`.
- **Tests:** `Settings.test.tsx:32-42` (lede), `:44-130` (extension), `:212-226` (key not revealed).

### 7. The browser extension today

- **Options.** Server address (default `http://127.0.0.1:8000`; only `127.0.0.1` or `localhost`) and token, in `chrome.storage.local`. Test connection calls `GET /api/extension/status` — `extension/src/options.ts:1-49`.
- **Popup start.** Without a token it shows "Connect this browser…". `api()` sends `Authorization: Bearer <token>`, and a network failure becomes "Could not connect to CatchUp." — `popup.ts:82-134`.
- **Page type:**
  - `isX` is true only when the host is exactly `x.com` or `twitter.com` — `popup.ts:139-140`;
  - `xPost` is true for a path like `/<user>/status/<id>` — `:141-143`.
- **On any X page**, post or profile, the popup shows "X accounts cannot be followed. You can save an individual post instead." It shows no Follow button — `:145-160`, at `:153`.
- **Follow this site.** `POST /sources/preview {url}`, then `POST /sources {feed_url}`, with the Sources page's error wording — `:220-260,27-47`.
- **Add this page:**
  - an X post runs `extractX`;
  - other pages run Readability, then the generic extractor;
  - the result is checked, then saved with `POST /captures` — `:169-218`.
- **Manifest.** `activeTab`, `scripting`, `storage`, with host permissions only for `127.0.0.1` and `localhost`. A test forbids background scripts and content scripts — `extension/public/manifest.json:6-9`, `src/test/manifest.test.ts:5-16`.

### 8. The extension token's scope

- **Tokens:** `cu_` + `token_urlsafe(32)`, stored as a SHA-256 hash — `api/extension.py:35-45`, `models.py:60-67`.
- **`cross_site_writes`** — `main.py:113-139`:
  - an unknown `Bearer cu_` gets 401;
  - an operation outside the list gets 403 `cross_site_request`;
  - a listed operation skips the Origin check.
- **The list** — `main.py:48-53`:
  - POST `/api/sources`, `/api/sources/preview`, `/api/captures`;
  - GET `/api/captures`, `/api/extension/status`;
  - DELETE `/api/captures/{id}`.
- **Token-only routes.** `require_connection` guards the status and capture routes. The source routes take a token, but do not require one — `api/extension.py:28-32`.
- **Tests that enumerate the scope:** `backend/tests/test_extension_api.py` at `:80-97`, `:113-124`, `:156-161`, `:444-451`, `:453-470`. No single test lists the whole allow-list.
- **The spec sentence listing the operations:** `openspec/specs/model-settings/spec.md:92`.

### 9. Saved X posts, end to end

- **The extractor** (`extension/src/extract/x.ts:2-76`):
  - it reads the `article[data-testid="tweet"]` that links to the status id;
  - the author comes from the first one-segment profile link in `User-Name`;
  - the text from `tweetText`;
  - replies from later articles by the same handle, at most 10 and 4,000 characters;
  - up to 8 images, and up to 50 links;
  - a `t.co` link is kept only when its label shows the full address.

  It returns title `<name> on X`, site name `X · <name>`, and author `<name> @<handle>`.
- **The server** — `api/extension.py:132-191`:
  - the identity key is the normalized URL;
  - replies are trimmed;
  - `site_name` falls back to the host;
  - all captures share the `catchup:captures` source.
- **Context.** Captured replies become `ItemContext` `A1`, kind `author_replies`, titled "Author replies (N)". They are added even after the fetch budget is spent. A capture's site is the item's own scheme and host — `context/gather.py:35-50,79,156-163`.
- **Related links** drop `x.com` and `twitter.com`, after stripping `www.` and `mobile.`. There is no `t.co` rule — `context/links.py:29-35`.
- **The prompt** labels it `Context A1 — author replies: … (host)`, and asks the model to leave out user handles — `llm/prompts.py:61-73`.
- **The digest:**
  - `source_name` is `coalesce(Item.site_name, Source.title)` — `runner.py:46,319`;
  - used contexts become `also_read` — `runner.py:360-363`, `api/digests.py:70-74`;
  - the UI shows "Saved from browser: X · Name" to screen readers — `DigestArticle.tsx:81,93-97`, `ui.tsx:43-54`.
- **Tests:** `x.test.ts:11-58`, `test_digest_runner.py:177-206`, `test_context_links.py:9-24,55-61`.

### 10. Limits, budgets, and rate limiting

- **`config.py:58-70`:**

  | Setting | Default |
  | --- | --- |
  | `FIRST_ADD_DAYS` | 7 |
  | `FIRST_ADD_MAX` | 5 |
  | `SHORT_TEXT_CHARS` | 500 |
  | `CAPTIONS_PER_RUN` | 20 |
  | `LINKS_PER_ITEM` | 8 |
  | `CONTEXT_FETCHES_PER_RUN` | 60 |
  | `AUTHOR_REPLIES` | on |
  | `LONG_ITEM_CHARS` | 20000 |

- **`safe_fetch`** — `net/safe_fetch.py:18-31,58-61,131-145`:
  - limits: 5 MB, 5 redirects, a 30 s deadline;
  - a 429, or a 503 with `Retry-After`, is retried once when the wait is 10 s or less;
  - otherwise it raises `rate_limited` ("The source is rate limiting requests.").
- **Per-host spacing:** at least 1 s between requests to the same host — `net/host_spacing.py:10`.
- **How a rate limit reaches the user:**
  - API errors carry `retry_after`, which the Sources page shows as "Rate limited — try again later (about N seconds)" — `api/sources.py:35-36`, `frontend/src/api/client.ts:22-28`, `Sources.tsx:31-33`;
  - run checks infer a rate limit from 429, or from 503 plus the message — `net/rate_limit.py:7-10`;
  - it shows as "Rate limited · try later" — `Sources.tsx:90-94`, `Home.tsx:39-43`;
  - after a run, failed and gap checks are listed under "Needs attention" — `Home.tsx:82,97,110`.
- **Caption pass.** It stops after YouTube blocks a request — transcripts spec `:149-150`.
- **No per-run cap on items summarized.** Summaries run with 4 workers — `digest/summarize.py:91,150`. The spec says "no limit on the number of items" — digest-generation `:31`.
- **Token usage is reported; prices are not shown** — digest-generation `:193-194`.

### 11. External facts: the X API (as of 2026-10-24)

Sources were read from docs.x.com, the OpenAPI spec (v2.172), DevCommunity posts, and the Terms of Service. Most docs pages carry no date. The Developer Agreement was last updated 2026-04-27, and the ToS took effect 2026-10-09.

- **Field names conflict between docs.** Guide pages use `tweet.fields`, `note_tweet`, and `referenced_tweets`. The OpenAPI spec uses `post.fields`, `note_post`, and `referenced_posts`. The docs do not say which the live API accepts — https://docs.x.com/x-api/fundamentals/data-dictionary, https://docs.x.com/openapi.json
- **User lookup: `GET /2/users/by/username/:username`.**
  - The username matches `^[A-Za-z0-9_]{1,15}$`.
  - Fields include `id`, `name`, `username`, `profile_image_url`, `description`, `protected`, `verified`, and `most_recent_tweet_id`.
  - For a protected account, the lookup returns its basic fields and `protected: true`. Its posts need authorization — https://docs.x.com/x-api/users/lookup/integrate
- **User posts timeline: `GET /2/users/:id/tweets`.**
  - Parameters: `max_results` 5–100, `pagination_token`, `since_id`/`until_id`, `start_time`/`end_time`, and `exclude=replies,retweets`.
  - It returns the 3,200 most recent posts, or 800 with `exclude=replies`.
  - Edited posts come back in their latest version — https://docs.x.com/x-api/posts/timelines/integrate
- **Long posts.** `note_tweet` holds the full text of posts over 280 characters. No official page says what `text` holds then; community reports say it is cut — data dictionary; https://devcommunity.x.com/t/issue-with-fetching-full-content-of-long-tweets-via-api/243304
- **Links and references:**
  - `entities.urls` gives the `t.co` URL, `expanded_url`, `unwound_url`, `display_url`, and, when available, `title` and `description`;
  - `referenced_tweets` marks retweets, quotes, and replies;
  - the referenced posts appear under `includes` with the `referenced_tweets.id` expansion;
  - media fields: `url` (photos), `preview_image_url`, `alt_text`, `type` — data dictionary; https://docs.x.com/x-api/fundamentals/expansions
- **An author's replies in a thread:**
  - a thread's `conversation_id` is the root post's id;
  - recent search (`GET /2/tweets/search/recent`) accepts `conversation_id:` and `from:`, covers 7 days, returns 10–100 results, and takes queries of up to 512 characters;
  - full-archive search reaches back to 2006, on pay-per-use, and bills its posts as post reads;
  - there is no replies endpoint;
  - whether an author's replies to their own posts are dropped by `exclude=replies` is not documented, and community reports conflict — https://docs.x.com/x-api/fundamentals/conversation-id, https://docs.x.com/x-api/posts/search/introduction
- **X Activity API.** `post.create` and `post.delete` events per user id, by stream or webhook; posts from protected accounts are not delivered — https://docs.x.com/x-api/activity/introduction
- **Authentication:**
  - **App-only Bearer token:** read-only access to public data. It comes from the console, or from `POST oauth2/token` with the API key and secret. One token is valid per app at a time, until it is invalidated; no expiry is documented — https://docs.x.com/fundamentals/authentication/oauth-2-0/application-only
  - **OAuth 2.0 with PKCE:** a two-hour token, with a refresh token when `offline.access` is requested — https://docs.x.com/fundamentals/authentication/oauth-2-0/authorization-code
  - **Accepted auth:** user lookup, user posts, and both searches accept a Bearer token or user context.
  - **What the developer creates in console.x.com:** they accept the agreement, describe their use, and create an App. Then they generate an API key and secret, a Bearer token, access tokens, and a client id and secret, each shown once — https://docs.x.com/x-api/getting-started/getting-access
- **Pricing (pay-per-use)** — https://docs.x.com/x-api/getting-started/pricing:
  - prices: a post read costs $0.005, and a user read $0.010, "per resource";
  - "owned reads" cost $0.001, only for the app owner's own data;
  - credits are bought upfront, with no subscription or minimum;
  - only successful responses that return data are billed — https://docs.x.com/x-api/fundamentals/post-cap
  - the same post is billed once per UTC day, which X calls a "soft guarantee";
  - the cap is 3 million post reads per monthly cycle;
  - the developer can set a spending limit, and use auto-recharge (minimum $5);
  - a verified phone number is needed to buy credits — https://docs.x.com/developer-terms/ppu-agreement
  - free credits: $20 after the first eligible purchase, which expire after 3 months — https://docs.x.com/x-api/getting-started/free-credits
  - since 2026-02-06 there is no free tier for new developers. Legacy Basic moved to pay-per-use after 2026-06-01, and Pro after 2026-09-01 — https://devcommunity.x.com/t/announcing-the-launch-of-x-api-pay-per-use-pricing/256476
  - **Arithmetic from the listed prices,** not from the docs: following 20 accounts that each post 10 times a day is 200 post reads, about $1 a day.
- **Rate limits, per 15 minutes** — https://docs.x.com/x-api/fundamentals/rate-limits:

  | Endpoint | Per app | Per user |
  | --- | --- | --- |
  | User lookup | 300 | 900 |
  | User posts | 10,000 | 900 |
  | Recent search | 450 | 300 |

  - A 429 comes with `x-rate-limit-reset` (a Unix time).
  - `GET /2/usage/tweets` reports posts consumed per day. No cost headers are documented — https://docs.x.com/x-api/usage/introduction
- **Policy** — https://docs.x.com/developer-terms/policy, https://docs.x.com/developer-terms/agreement:
  - **Credentials** (policy, lines 160 and 257 of the downloaded page):
    - "You must keep all API keys or other access credentials private."
    - Developers "may not use … API keys or other access credentials owned by others".
    - Developers may not "request that people provide their X password, account credentials, or developer application information (including consumer key) to you directly".
    - A self-hosted app run by its own owner, with the owner's own keys, is not addressed.
  - **Use cases:** "You may not register multiple applications for a single use case" (policy, line 156). Serving different end users with one application counts as one use case.
  - **Stored content:** stored X content must be kept up to date. Deleted or changed content must be removed or updated within 24 hours of a request. This also covers accounts that become protected or suspended.
  - **Display rules** for showing posts: the author's name, handle, and picture, the unaltered text, and a timestamp linked to the post. Whether an LLM summary counts as display is not addressed — https://docs.x.com/developer-terms/display-requirements
  - **AI:** X content must not be used to train or fine-tune foundation models. Sending content to an LLM for a summary is not addressed. The agreement forbids providing X content "to any third party" except as permitted; whether a model provider counts as one is not addressed.
  - **Terms of Service** (https://x.com/en/tos): access only through "currently available, published interfaces"; scraping "in any form" is prohibited.

### 12. X's terms on storage, derived data, deletion, and exceptions

Read from the pages downloaded on 2026-10-24. The Developer Agreement (https://docs.x.com/developer-terms/agreement) was last updated 2026-04-27. The pay-per-use agreement (https://docs.x.com/developer-terms/ppu-agreement) and the Developer Policy (https://docs.x.com/developer-terms/policy) show no date.

- **Local storage.** Allowed. Section II.A.2 of the Developer Agreement (and section 2 of the pay-per-use agreement) licenses copying "a reasonable amount" of X Content for display in the developer's services. The Developer Policy ("Content compliance") requires that content stored offline match its current state on X. The Agreement's section IV.B ("Removals") also covers content that is deleted, becomes protected, or is otherwise removed. Content deleted or changed on X must be deleted or changed as soon as reasonably possible, or within 24 hours of a request from X or the account owner.
- **Derived results.** They count as X Content. The Agreement's definitions (section I.12) include "any copies and derivative works thereof", so summaries and titles written from posts fall under the same rules.
- **After cancelling.** Everything must be deleted. The Agreement's termination clause (section VII.I, and the same clause in the pay-per-use agreement) says the developer may cancel. On termination, all licenses expire, and the developer must permanently delete all Licensed Material in every form and copy. X may ask for evidence of deletion within ten business days.
- **Personal or research exceptions.** None from these rules.
  - The self-serve plans are described as designed for hobbyists, prototyping, and apps with a limited number of end users (Agreement III.L; Policy, "Set yourself up for success").
  - The only research carve-out is for academic researchers distributing Post IDs or User IDs, with X's written approval (Policy, "Content redistribution").

## Code References

- `backend/src/catchup/models.py:37-46,60-67,70-114,201` — model config, extension tokens, Source, Item, DigestItem.
- `backend/src/catchup/crypto.py:11-26` — Fernet key encryption.
- `backend/src/catchup/api/settings.py:20-137` — model settings and test routes.
- `backend/src/catchup/api/sources.py:25-175,193` — preview, confirm, list.
- `backend/src/catchup/sources/discovery.py:14-167` — feed discovery.
- `backend/src/catchup/sources/feeds.py:288-294,325-327,362-364` — feed kind and identity keys.
- `backend/src/catchup/collection.py:55-165` — article text and source checks.
- `backend/src/catchup/digest/runner.py:38-61,127-139,168-440` — selection, start, run, detail.
- `backend/src/catchup/context/gather.py:22-175`, `context/links.py:8-35` — context and related links.
- `backend/src/catchup/main.py:33-63,113-139` — token lookup, allow-list, cross-site middleware.
- `backend/src/catchup/api/extension.py:28-221` — tokens, status, captures.
- `backend/src/catchup/net/safe_fetch.py:18-191`, `net/rate_limit.py:7-10`, `net/host_spacing.py:10` — fetching limits.
- `backend/src/catchup/config.py:30-78` — settings.
- `frontend/src/components/ui.tsx:43-54`, `Icon.tsx:1-12` — kind labels and icons.
- `frontend/src/pages/Sources.tsx`, `Home.tsx`, `Settings.tsx` — sources, home counts, settings.
- `extension/src/popup.ts:27-260`, `options.ts:1-49`, `extract/x.ts:2-76` — popup, options, X extractor.

## Current Specs

- **`source-management`:**
  - "Preview a source from a pasted URL" (`:8`): feeds, Apple Podcasts, HTML pages; three kinds; previewing saves nothing.
  - "Explain unsupported and duplicate sources" (`:62`): a fixed list of reasons; a rate limit is named as such.
  - "Confirm and save a source" (`:105`): up to 5 entries from 7 days are new.
  - "Honor rate limits when fetching" (`:157`).
  - "A built-in source for pages saved from the browser" (`:187`).
- **`content-collection`:**
  - "Check every source on each run" (`:8`): `new_items`, `no_new_items`, `failed`.
  - "Identify rate-limited checks" (`:111`).
  - "Space requests to the same host" (`:118`).
  - "Gather related context for website items" (`:129`): related links exclude x.com and twitter.com (`:138`); at most 10 replies and 4,000 characters (`:143`); a per-run fetch limit (`:145`).
  - "Gather context for pages saved from the browser" (`:186`).
- **`model-settings`:**
  - "Protect the stored API key" (`:34`): encrypted with the instance secret; never returned; at most the last four characters.
  - "Never send the stored key to a different provider address" (`:45`).
  - "Report provider errors meaningfully" (`:59`).
  - "Refuse write requests from other sites" (`:85`): a token is accepted only for the listed operations, and "MUST NOT allow any other request that changes data or starts work" (`:92`).
- **`browser-extension`:**
  - "Follow the current site from the browser" (`:23`): "On an X page, it MUST say that X accounts cannot be followed" (`:24`); scenario "X profile" (`:34-36`).
  - "Read X posts with the author's own replies" (`:76`).
  - "What the extension never does" (`:87`).
  - "Install the extension from the repository" (`:104`): README states X's scraping terms (`:109`).
- **`transcripts`:** "Recognize podcast and YouTube sources" (`:8`): three classified kinds, plus "Saved from browser" (`:14`).
- **`user-interface`:**
  - "Sources show their kind…" (`:119`): the four kind names.
  - "Settings explain risk and keep secrets out of view" (`:130`): the groups are Model provider, Digest, and YouTube; a saved key shows only its last four characters.
  - "Connect a browser in Settings" (`:238`).
- **`digest-generation`:**
  - "Include every pending item" (`:30`), with no item limit (`:31`).
  - "Summaries focus on substance" (`:118`): no handles.
  - "Report model token usage" (`:193`): prices are not shown.
  - "Use related context in summaries" (`:204`).
  - "Summarize pages saved from the browser" (`:238`): "X · Simon Willison".
- **`local-deployment`:** "Local-only access by default" (`:30`) and "Keep local secrets out of the image" (`:62`). Nothing about X.

## Related History

- **`docs/process/requirements-changes.md:15`** (2026-10-02): "X is not supported", because X needs a login or the paid API. The later options are a user-supplied X API key, or the browser extension.
- **`requirements-changes.md:42`** (2026-10-22): following X accounts (#41) will use the user's own X API key, which the extension and CatchUp ask for when the user follows an X account. The user decided this after the manual check of #58.
- **`docs/process/decision-log.md` D-024** (`:292-322`): the extension reads X posts with the author's own replies.
  - A logged-in collector was rejected under X's automation rules (`:310-313`).
  - "The X API for following accounts. Kept as a separate option (#41)" (`:314`).
- **`README.md`:**
  - the extension "never … follows an X account" (`:123-124`);
  - "X's terms prohibit scraping in any form … CatchUp does not follow X accounts" (`:147-149`);
  - following X accounts is not supported (`:303-304`).
- **`AGENTS.md:12`:** "self-hosted web application; user-owned model API; manual, incremental digest generation; public sources and accessible transcripts first".
- **`docs/handoff.md:55`:** "do not read the user's saved passwords, and do not upload session cookies for general-purpose login".
- **Issue #41.** It also asks that, when X posts are supported, the author's own replies in the thread and their notable interactions be read (user testing, 2026-10-19).
- **`openspec/changes/archive/2026-10-24-add-browser-extension/research.md:263-274`:** the earlier X terms and pricing facts (2026-10-20). They match the prices above.
