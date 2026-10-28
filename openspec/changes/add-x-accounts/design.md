# Design

Full RePPIT change for issue #41.
- **Inputs.** The research is in `research.md` (main @ f1b76c0), the motivation in `proposal.md`, and the requirements in the spec deltas.
- **Chosen.** On 2026-10-24 the user chose Proposal 1: an app-only Bearer token, pasted once. They also chose:
  - to skip the creator's replies to other people's posts;
  - a read limit of 200 posts per run, with posts that do not fit waiting for the next run;
  - that the extension asks for the token in place.
- **Rejected alternatives:** Proposal 2 and the others are under D12. Claude adds decision D-025 to `docs/process/decision-log.md` with this plan.
- **Fresh-eyes check (D-023).** A sub-agent checked this plan against the code before Droid runs. It reported 15 issues. Claude verified them, and folded 14 into this design, the tasks, and two spec lines. The most important ones:
  - a deferred account must not get a new `last_check_at`, or it would be read last again;
  - the migration's downgrade needs `recreate="never"`;
  - the preview must not show `x:user:<id>`.

  The issue not taken: keeping the author's replies to commenters in their own thread, which matches the user's choice (D5).
- **Fix round 1 (2026-10-28).** Claude's review of Droid run 1 (`/code-review`, a spec sub-agent with 44 mutations, and probes) confirmed defects that this design caused or left open. On 2026-10-28 the user approved one fix round, task group 6. The decisions below are amended where marked "Fix round 1":
  - D5: Phase B left a stale gap after reading every page;
  - D2: partial `errors` sent with data, and suspension reported as not found;
  - D4, D1, D13: a cached preview could still be confirmed after the token was removed or all X data was deleted;
  - D1: Test answered 500 for a token that cannot be decrypted;
  - D3: other x.com hosts reached `discover()`;
  - D8: the token prompt's hint, and its rejected-token wording, which disagreed with the spec.

- **Fix round 2 (2026-10-28), the last round.** The review of fix round 1 found two small defects and one plan error, and the user approved one more small round, task group 7. Amended where marked "Fix round 2":
  - D5: fix round 1's "an empty page ends a phase" could skip posts for good; a page cap replaces it;
  - D3: a host with a trailing dot (`x.com.`) was not an X host, and feed confirm answered 500 for an address it could not parse.

- **Fix round 3 (2026-10-28).** The user asked for an independent review of the whole change after fix round 2. It found no high-severity defect, and seven smaller ones, all confirmed by Claude. The user approved one more round, task group 8, and chose to record the eighth item, author replies lost when the read limit splits a thread, as a known limit (D5). Amended where marked "Fix round 3":
  - D1: a token with a character outside printable ASCII was saved, then made every run fail, because `httpx` cannot encode it in a header;
  - D3: the rule against requesting x.com lived in three callers, and `safe_fetch` still followed redirects to x.com and fetched x.com entry links; one refusal in `safe_fetch` replaces the callers' guards (re-derived, D-023);
  - D2, D5: an answer that is not a timeline page (HTML, or only an unknown error) counted as the last page, and cleared a gap;
  - D4, D13: a confirm could store an account while "Delete all X data" ran;
  - D9: a failed run did not show the X reads already billed.

  A fresh sub-agent checked group 8 before Droid ran. Claude verified its 6 findings and folded them in: an address parse in `safe_fetch` that still raised `ValueError`, a redirect test that could not fail, a lock test that could hang the suite, guards without mutations, a stale comment, and the reason a new session is needed.

  A fresh sub-agent checked group 7 before Droid ran. Claude verified its 3 findings and folded them in: a Phase A test that passed on the current head and would fail after the fix, a missing budget, and a guard not marked as one.

  Before Droid runs, a fresh sub-agent checked group 6 against the code (D-023). Claude verified its 8 findings and folded all of them in: a mutation that a rewrite would make equivalent, two checks the test network block made vacuous, a missing guard on the extractor choice, links to other X hosts still fetched as context, the real red result of Test, an axe check that could not fail, and an unbounded loop on empty pages.

## Context

The facts from the research that shape the design. Line numbers are at main f1b76c0, so Droid re-checks them before editing.
- **Kinds are plain strings.** `Source.kind` is `String(16)`, with no constraint (`backend/src/catchup/models.py:78`). `feed_url` is unique (`:76`), and the captures source already uses a non-URL value, `catchup:captures` (`api/extension.py:109-123`).
- **Preview and confirm.**
  - Preview calls `discover()` (`api/sources.py:66-92`).
  - Confirm marks up to `FIRST_ADD_MAX` (5) entries from `FIRST_ADD_DAYS` (7) as `pending`, and the rest `baseline` (`:119-137`).
  - A successful discovery is cached for 600 s (`net/feed_cache.py:11-34`).
- **The run** (`digest/runner.py`):
  - `run_digest` checks non-`capture` sources in id order with `check_source` (`:184-186,208-213`), then runs `caption_pass` and `gather_context` (`:214-215`).
  - `select_pending` summarizes items with no transcript status only for kinds `feed` and `capture` (`:45`).
  - **The check-rewrite step** (`:239-260`) rewrites every check whose status is not `failed` to `new_items` or `no_new_items`, from what the run included.
  - **The run bar** waits until `source_checks.length` equals `sources_total`, so that it can show the context pass (`frontend/src/pages/Home.tsx:65-67,222`). So every counted source needs a check row in every run.
- **Rate limits.** A check is rate limited when its `http_status` is 429 (`net/rate_limit.py:7-10`). The Sources page and Home show this as "Rate limited · try later" (`Sources.tsx:90-94`, `Home.tsx:39-43`).
- **The context pass** admits kinds `feed`, `podcast`, and `capture` (`context/gather.py:28`). For `capture` it:
  - uses the item's own origin as the site (`:35-36`);
  - fetches no comments (`:42-43`);
  - turns `captured_replies` into the `A1` part, even after the budget is spent (`:44,79,156-163`).

  Related links drop `x.com` and `twitter.com` (`context/links.py:33-35`).
- **Delivery.** Items become `delivered` in the digest-saving loop (`runner.py:366,391`). After delivery, nothing reads `content_text`: only pending items reach the summarizer (`runner.py:227`), and checks match on `identity_key` and `link` (`collection.py:99-125`).
  - Digest items keep their own title, link, summary, and `context_links` (`runner.py:355-364`).
  - `item_contexts` rows are deleted with their item (`models.py:114,121`).
  - Deleting a source deletes its items, because foreign keys are on (`db.py:26`, `models.py:92`).
- **Model-key storage.** Fernet encryption, keyed from `CATCHUP_SECRET_KEY` (`crypto.py:11-26`). A single `model_config` row stores the key and its last four characters (`models.py:37-46`). Settings routes are under `/api/settings` (`api/settings.py:20-137`).
- **The extension token's allow-list** (`main.py:48-53`) lists method and path pairs. A request with a valid token that is not on the list gets 403. Routes see `request.state.extension_token_id` (`main.py:128-131`).
- **Tests block real network access.** `socket.getaddrinfo` and `socket.connect` raise, and `safe_fetch.sleep` is replaced (`backend/tests/conftest.py:8-20`). `respx` mocks `httpx` above the socket layer.
- **The X API, as of 2026-10-24** (research §11):
  - `GET /2/users/by/username/:username` and `GET /2/users/:id` look accounts up;
  - `GET /2/users/:id/tweets` returns newest first, with `since_id`, `until_id`, `start_time`, `max_results` (5–100), `pagination_token`, and `exclude=retweets,replies`;
  - `GET /2/usage/tweets` accepts only a Bearer token.
  - **Prices:** $0.005 per post read and $0.010 per user read, deduplicated per UTC day.
  - **Field names are unsettled:** guide pages use `tweet.fields` and `note_tweet`, the OpenAPI spec `post.fields` and `note_post`.

## Goals / Non-Goals

**Goals:**
- Follow public X accounts by address, through the official API, with the user's own token.
- Read each followed account's new posts on each run, with the author's thread replies.
- Keep cost predictable: one limit per run, no post lost to the limit, and reads shown after each run.
- Reuse the source, context, summary, and digest pipeline, with as few kind-specific branches as possible.
- Keep the token as protected as the model key. The extension's new power is the narrowest possible: saving a token when none exists.

**Non-Goals:**
- Sign in with X (OAuth), and the following-list picker: Proposal 2, D12.
- Protected accounts, lists, likes, bookmarks, the home timeline, and Spaces.
- Other people's replies, and the creator's replies to other people's posts (user decision).
- Watching for deleted or edited posts after delivery (D10).
- The extension calling the X API itself.
- Showing prices in the app.

## Decisions

### D1. The credential: an app-only Bearer token in its own table (capabilities `x-accounts`, `model-settings`)

- **Storage.** A new single-row table, `x_credentials` (id 1): `token_encrypted`, `token_last4`, `updated_at`. The token is encrypted with `encrypt_key` (`crypto.py:22-23`).
  - **Why its own table:** it mirrors `model_config`, and keeps `app_settings` to preferences.
- **Routes** (in `api/settings.py`):
  - `GET /api/settings/x`: `{token_set, token_last4}`.
  - `PUT /api/settings/x`: `{token}`, stripped. It must be non-empty, at most 1,000 characters, with no whitespace, or it gets 422 `invalid_x_token`. **Fix round 3:** it must also be printable ASCII (`[\x21-\x7e]{1,1000}`), because it is sent in an HTTP header; `httpx` raises `UnicodeEncodeError` for anything else, for example a zero-width space copied with the token. Test's `{token}` follows the same rule.
    - **From the extension:** when `request.state.extension_token_id` is set and a token is already saved, it answers 409 `x_token_exists`, and changes nothing.
    - **Without the instance secret** it answers `secret_not_configured`, as for the model key.
  - `DELETE /api/settings/x`: removes the row, and empties the X preview cache (D4, fix round 1); 204.
  - `POST /api/settings/x/test`: `{token?}`. It tests the given token, or the saved one, with `GET /2/usage/tweets?days=1`, so no post or account is read.
    - It answers `{ok: true}`, or `x_token_rejected` (401/403), `rate_limited` (with `retry_after`), or `fetch_failed` (with `http_status`).
    - With no token, it answers 422 `x_token_required`.
    - **Fix round 1.** When the saved token cannot be decrypted (the instance secret changed or is missing), it answers 400 `secret_invalid`, "Check the X token and instance secret.", and sends nothing. Preview already does this (`_x_token` in `api/sources.py`); both routes share one helper. Run 1 answered 500.
- **Sending.** The token is sent only to the fixed base URL `https://api.x.com`. There is no configurable X base URL, so the "never send the key to another address" rule holds by construction.
- **Allow-list.** `main.py:48-53` gains `PUT /api/settings/x`. `GET` and `DELETE` stay off the list, so the extension can neither read nor remove the token.

### D2. The X API client (`backend/src/catchup/sources/x_api.py`)

- **The HTTP client.** It uses `httpx.Client`, with base URL `https://api.x.com`, connect and read timeouts of 5 s and 15 s, a 5 MB body cap, `Authorization: Bearer <token>`, and CatchUp's `User-Agent`.
  - **Why not `safe_fetch`:** the host is fixed, so its address checks do not apply.
  - **No retries and no sleeping,** because a retry costs money and tests forbid real sleeps.
- **The client object.** `XClient(token)`, a context manager around one `httpx.Client`. The run creates one with `closing(...)`, once per run; the preview, confirm, and test routes create their own. Its methods:
  - `lookup_user(username)` and `lookup_user_by_id(user_id)`, with user fields `id`, `name`, `username`, `protected`, `most_recent_tweet_id`;
  - `user_posts(user_id, *, since_id, until_id, start_time, max_results, pagination_token, exclude)`;
  - `usage()`.
  - Posts are requested with fields `created_at`, `conversation_id`, `in_reply_to_user_id`, `referenced_tweets`, `entities`, `note_tweet`, `attachments`, and `author_id`. Media come through the `attachments.media_keys` expansion, with `media_key`, `type`, `url`, `alt_text`, and `preview_image_url`.
  - **Not requested:** the `referenced_tweets.id` expansion, because whether expanded posts are billed is not documented.
- **What it returns.** Plain dataclasses, so the rest of the code does not see the API's field names:
  - `XUser(id, name, username, protected, most_recent_post_id)`;
  - `XPost(id, text, created_at, conversation_id, in_reply_to_user_id, is_retweet, is_reply, urls, photos)`;
  - `XPage(posts, next_token, result_count)`.
- **The post's text:**
  - the `note_tweet` text when present, otherwise `text`;
  - each `entities.urls[].url` (`t.co`) replaced by its `unwound_url`, or else its `expanded_url`. An entry with no `url` replaces nothing (fix round 1: run 1 replaced the empty string, which inserts the destination between every character);
  - `urls` keeps those destinations.
- **Errors.** `XApiError(code, message, http_status, retry_after)`.
  - **Fix round 1: `errors` decide the outcome only when the body has no `data`.** X sends `errors` next to `data` for parts of an answer it could not fill, such as a missing media item. Such an answer is a success, and its data is used. Run 1 mapped any `errors` entry, so one partial error discarded a page that X had already billed.
  - Without `data`, the entries are checked in this order:
    1. **Suspended first.** An entry whose `detail` or `title` mentions suspension → `x_account_suspended`. X reports a suspended account as HTTP 200 with type `resource-not-found` and the detail "User has been suspended", or sometimes as 403 (developer forum threads [141550](https://devcommunity.x.com/t/users-by-username-returns-200-status-for-suspended-accounts/141550) and [174127](https://devcommunity.x.com/t/403-forbidden-63-user-has-been-suspended/174127); the API reference does not say). So this check must come before the not-found check. Run 1 reported suspended accounts as not found.
    2. A type ending in `resource-not-found` → `x_account_not_found`.
    3. An authorization entry for an account (a protected account) → `x_account_protected`, even when the HTTP status is 401 or 403. The probe cannot show this case, so the mapping follows the documented error types, and a test pins it.
  - **Fix round 3.** A 2xx answer whose body is not a JSON object, or that has no `data` and only `errors` entries no rule above matches, is `fetch_failed`, with its HTTP status. A timeline answer is a page only when it has a `meta` object with an integer `result_count`; otherwise `fetch_failed`. Run 2 returned such answers as an empty page with no `next_token`, which ended a phase as complete and cleared its gap.
  - Then the HTTP status:
  - 401 or 403 → `x_token_rejected`;
  - 404 → `x_account_not_found`;
  - 429 → `rate_limited`, with `retry_after` = `x-rate-limit-reset` minus now, at least 1;
  - any other status or transport failure → `fetch_failed`, with `http_status` when there is one.
  - The message for `rate_limited` starts with `RATE_LIMIT_PREFIX` (`safe_fetch.py:22`), so stored checks read as rate limited.
- **Field names.** Fixed by the probe (D11) before Droid runs. The probe's result is recorded here as D2a, and the fixtures follow it.

### D2a. What the probe showed (2026-10-27)

The user ran `scripts/x_probe.py` against one public account, with their own token. Its output, which holds no token, is in the gitignored `work/x-probe.txt`.
- **Both spellings work, and the response keys follow the request.**
  - `tweet.fields` returns `referenced_tweets` and `edit_history_tweet_ids`.
  - `post.fields` returns `referenced_posts` and `edit_history_post_ids`.
  - **The client uses `tweet.fields`.** It reads a long post's text from `note_tweet`, falling back to `note_post`. The sample held no long post, so a fixture invents one in the `note_tweet` shape of the data dictionary.
- **The lookup** returns `id`, `name`, `username`, `protected`, and `most_recent_tweet_id`.
- **`exclude=replies` did not exclude a self-reply.** A post came back with `exclude=retweets,replies` although its `in_reply_to_user_id` was the author's own id, and it had a `referenced_tweets` entry of type `replied_to`. So the preview drops replies itself: any post with a `replied_to` reference, or with `in_reply_to_user_id` set.
- **Reply fields.** A reply carries `in_reply_to_user_id`, `conversation_id` (the root post's id), and `referenced_tweets` `[{type: "replied_to", id}]`. An original has `conversation_id` equal to its own `id`.
- **An unknown username answers HTTP 200,** not 404. The body has no `data`, and `errors: [{title: "Not Found Error", resource_type: "user", type: ".../2/problems/resource-not-found", ...}]`.
  - The client maps errors by the last path segment of `type` (`resource-not-found`).
  - It maps them neither by the HTTP status, nor by the full URL, whose host was `api.x.com`.
- **Timeline pages.** `meta` has `newest_id`, `oldest_id`, `result_count`, and `next_token`. Ids are 19-digit strings. `created_at` looks like `2026-10-28T04:18:22.000Z`.
- **URLs.** Each `entities.urls` item had `url` (t.co), `expanded_url`, `unwound_url`, `display_url`, `status`, `start`, and `end`. None had a `title`.
- **Media.** `includes.media` had `media_key`, `type` `photo`, and `url`. There was no `alt_text`, which appears only when set, so alt text defaults to `""`.
- **Rate-limit headers.** Every answer had `x-rate-limit-limit`, `-remaining`, and `-reset`, a Unix time. The limits were 300 for lookups, 10,000 for the timeline, and 50 for usage.
- **`GET /2/usage/tweets?days=1`** answers 200 with a Bearer token, and `data` holds `project_usage`, `project_cap`, and `cap_reset_day`. Test uses it.

### D3. Recognizing X account addresses (`backend/src/catchup/sources/x_accounts.py`)

- **The function.** `x_username(url) -> str | None`:
  - the host must be `x.com` or `twitter.com`, optionally with `www.` or `mobile.`;
  - the first path segment must match `^[A-Za-z0-9_]{1,15}$`, and must not be reserved.
- **Reserved first segments** are compared without case: `home`, `explore`, `search`, `i`, `settings`, `notifications`, `messages`, `compose`, `login`, `logout`, `signup`, `tos`, `privacy`, `hashtag`, `intent`, `share`, `account`, and `jobs`.
  - A reserved X address, a missing segment, or a segment that does not match raises `AppError("not_an_x_account", …, 422)`.
  - **Fix round 1: every other host under `x.com` or `twitter.com`** (the host equals the domain or ends with `.` plus the domain), such as `help.x.com` or `developer.x.com`, also raises `not_an_x_account`. The spec says the system MUST NOT request any page on x.com or twitter.com; run 1 sent those hosts to `discover()`. The cost: X's own blogs cannot be followed as feeds. Look-alike hosts such as `notx.com` or `x.com.example.org` are not X hosts. One helper decides whether a host is under `x.com` or `twitter.com`. **Fix round 2:** it compares the host in lower case, without one trailing dot, so `x.com.` (the same host, fully qualified) counts; the popup's copy does the same, and every popup check uses that normalized host. So `https://x.com./simonw` is the account `simonw`, and `https://help.x.com./en` is refused. The same helper makes feed confirm refuse an X-host `feed_url`, and makes `related_links` (`context/links.py:34-35`) drop links to every X host, not only `x.com` and `twitter.com`, so a post's link to `developer.x.com` is not fetched as context. **Fix round 2:** feed confirm answers 422 `invalid_url`, "Enter a valid public HTTP or HTTPS URL.", as `safe_fetch` does, when the address cannot be parsed; round 1's host check raised `ValueError` there, a 500.
  - A non-X address returns `None`, and the feed path runs as today.
- **Where it runs.** Preview calls it before `discover()`, so an X address never reaches `safe_fetch`.
- **Fix round 3: one refusal, in `safe_fetch`.** Fix rounds 1 and 2 kept the rule "never request a page on x.com or twitter.com" in its callers: preview, feed confirm, and `related_links`, and then had to patch those guards (an unparsable address, a trailing dot). `safe_fetch` itself still followed a redirect to x.com, and fetched an x.com entry link (`collection.py:60`, for example from a feed that turns X posts into RSS). Re-derived from the invariant:
  - `is_x_host` moves to a module with no CatchUp imports, `backend/src/catchup/net/x_hosts.py`, because `safe_fetch` cannot import `sources/x_accounts.py` (that module imports `x_api.py`, which imports `safe_fetch`). `x_accounts.py` imports it from there.
  - `_check_address` (`net/safe_fetch.py`), which runs for the first address and for every redirect hop, refuses an X host before resolving it: `FetchError("blocked_address", "X pages are read only through the X API.")`.
  - Feed confirm's own X-host check, and its `ValueError` mapping from fix round 2, are removed. `safe_fetch` answers `blocked_address` for an X host, and `invalid_url` for an address it cannot parse: its loop parsed the current address outside any `try` (`net/safe_fetch.py:118`), so `http://[abc/feed` raised `ValueError` in preview and confirm, which this round also fixes.
  - What stays: preview calls `x_username` to route an account address to the X API, and to answer `not_an_x_account`; `related_links` still drops X links, so they do not use the context budget, but it is no longer what keeps x.com from being requested.
- **The extension.** It keeps a copy of the rules, with a comment naming this module, as it already does for the error wording (`extension/src/popup.ts:27`). With fix round 1, the copy treats every host under `x.com` or `twitter.com` as an X page, so `https://help.x.com/en` offers only "Add this page". The X extractor is still used only on post pages of the six account hosts.

### D4. Preview and confirm (capability `x-accounts`; `api/sources.py`)

- **Preview** of an X address:
  1. **Token.** With no token saved, 422 `x_token_required`.
  2. **Lookup.** A protected account gets 422 `x_account_protected`.
  3. **Duplicates.** An account already followed (`feed_url == "x:user:<id>"`) gets 422 `duplicate`, with `existing_source`, as for feeds.
  4. **Posts.** One `user_posts(id, max_results=5, exclude=["retweets","replies"])`. Replies that still come back are dropped (D2a), so the preview may show fewer than 5.
- **The preview response** has the same shape as a feed preview, so the Sources page and the popup render it unchanged:
  - `feed_url: "x:user:<id>"`;
  - `site_url: "https://x.com/<username>"`;
  - `title: <name>`;
  - `follows_site_feed_notice: false`, `kind: "x"`, `captions_enabled: false`;
  - `entries`: up to 5, each with a title from the start of the post's text (the `_entry_title` rule, `sources/feeds.py:241-255`), its link, and `published_at`;
  - plus `username`.
- **The preview cache.** An `XPreviewCache`, like `FeedCache` (600 s, 50 entries), keyed by `feed_url`, holds the `XUser` and the posts. `create_app` sets `app.state.x_preview_cache = XPreviewCache()`, next to the feed cache (`main.py:103`).
- **Fix round 1: the cache never outlives the token or the X data.** Removing the token (D1) and Delete all X data (D13) empty it. Confirm also requires a saved token that decrypts, like preview, before it uses the cache; this covers a preview still running while the token is removed. Run 1 let a preview read before either action be confirmed for up to 10 minutes afterwards, which stored its posts again.
- **Confirm** with a `feed_url` starting `x:user:`:
  - It first requires a saved token (`x_token_required`, or `secret_invalid`), as preview does.
  - It takes the cached preview, or, if there is none, repeats the preview with `lookup_user_by_id` and one five-post read.
  - It creates the `Source` (kind `x`, title, `site_url`, `feed_url`, `input_url`), and an `x_accounts` row with:
    - `source_id` (primary key, foreign key with cascade), `user_id`, `username`;
    - `newest_id` = the lookup's most recent post id, or the newest previewed post's id, or `None` when the account has never posted;
    - `gap_since_id` and `gap_until_id`, both `None`;
    - `followed_at`.
  - Of the previewed posts, up to `FIRST_ADD_MAX` from `FIRST_ADD_DAYS` become `pending` items (D6). No baseline items are stored: `newest_id` already marks where reading starts.
  - It writes a `SourceCheck` with `run_id=None`, as for feeds (`api/sources.py:158-162`).
  - A concurrent duplicate is caught as `IntegrityError`, as for feeds.
  - **Fix round 3: confirm and Delete all X data exclude each other.** The re-preview on a cache miss runs first, outside any lock, because it calls X. Then, holding `_start_lock` (`runner.py:33`), which delete-all holds, confirm opens a new session from `session_factory`, checks again that a token is saved, checks for a duplicate, writes, and commits. A new session matters: the request's session already loaded the token row in `_x_token`, and its identity map would return that row again without asking the database, so it would still see a deleted token.

### D5. Reading on each run, with the read limit (capabilities `x-accounts`, `content-collection`)

- **Order.** `run_digest` checks X sources after the other sources, ordered by `Source.last_check_at` with `.nulls_first()`, then by `Source.id`. It shares one `XReadBudget(remaining=settings.x_reads_per_run)`.
  - **A `deferred` check MUST NOT change `Source.last_check_at`.** `check_source` always sets it to now (`collection.py:90,161`); copying that would make a deferred account the most recently checked one, so it would be read last again in the next run. Confirm leaves `last_check_at` NULL for X sources, so a new account is read first.
  - The token is decrypted once per run.
  - **With no token,** or when decryption fails, each X source gets a `failed` check, "X token needed" or "Check the X token and instance secret". Other sources are unaffected.
- **`check_x_account(session, source, account, run_id, client, budget)`:**
  - **With fewer than 5 reads left,** which is the API's smallest page, it records `deferred`, and reads nothing.
  - **Phase A, the gap.** When `gap_until_id` is set:
    - it reads with `since_id=gap_since_id` (or `start_time=followed_at` when that is `None`) and `until_id=gap_until_id`;
    - it requests pages of `min(100, remaining)` while `next_token` is present and at least 5 reads remain;
    - when the gap is fully read, both gap ids are cleared;
    - when the budget runs out first, `gap_until_id` becomes the oldest post id read, and Phase B is skipped.
  - **Phase B, new posts.** Only when no gap remains, it reads with `since_id=newest_id` (or `start_time=followed_at` when `newest_id` is `None`), in pages the same way.
    - `newest_id` becomes the largest post id read.
    - When the budget runs out with `next_token` present, the gap is set to the old `newest_id` (since) and the oldest post id read (until).
    - When Phase B reaches a page with no `next_token`, no gap is set.
  - **Fix round 2: a page cap, not an empty-page stop.** Fix round 1 treated a page with no posts as the last page, even with a `next_token`. X's timeline guide says a `next_token` can come with `result_count: 0`, so the posts after such a page would be skipped for good: Phase A cleared the gap, and Phase B had already moved `newest_id`. Instead:
    - an empty page with a `next_token` does not end a phase;
    - a phase makes at most 40 requests (`MAX_PAGES`). The timeline returns at most the 3,200 most recent posts, which is 32 pages of 100, so 40 leaves room for empty pages, and bounds the loop, because empty pages cost no budget;
    - reaching the cap is an early stop, like running out of budget: the gap rules below apply. When the phase read no post at all, nothing changes: Phase A keeps its gap, and Phase B sets no gap and keeps `newest_id`, so the next run reads from the same place.
  - **Fix round 1: the invariant.** After a check, the gap ids name exactly the posts that were skipped and are not yet read. So the gap changes only where a phase ends:
    - Phase A that reads to its last page clears the gap; Phase A that stops early sets `gap_until_id` to the oldest id it read;
    - Phase B sets the gap only when it stops early with `next_token` present, to the old `newest_id` and the oldest id read in Phase B.

    Run 1 set the gap after every Phase B page that had a `next_token`, and did not clear it on the last page. So an account with more than one page of new posts kept a stale gap after it was read in full: the next run read those posts again, paid for them again, and counted the account as waiting.
  - **Known limit (fix round 1, recorded, not fixed).** When Phase A reads to its last page with fewer than 5 reads left, Phase B waits for the next run. The account gets `no_new_items` or `new_items`, its `last_check_at` is set, and it is not counted as waiting. No post is lost: `newest_id` is unchanged, so the next run that reads it starts from there.
  - **Known limit (fix round 3, the user's choice on 2026-10-28, recorded, not fixed).** Posts are read newest first, so the author's replies in a thread come before its root post. When the read limit or the page cap stops a read between them, the replies read in this run are dropped, because their root is not in the batch, and a later run that reads the root does not get them back. They are billed. The root post itself is not lost. README says so.
  - **Ids** are compared as integers, and stored as strings.
- **Costs.** Each page subtracts its `result_count` from the budget. The run adds it to `DigestRun.x_reads`.
- **Threads.** The posts read for one account in one run, from both phases, form one batch:
  - **Originals** (not replies, not retweets) become items.
  - **A reply is kept** when its `conversation_id` equals the id of an original in the same batch. This includes the author's replies to commenters inside their own thread, which is what the user chose ("his replies in his own threads") and what #41 asks for ("notable interactions with replies"). It is attached to that original's `captured_replies`, oldest first, up to 10 replies and 4,000 characters, the caps of `api/extension.py:163-168`.
  - **Other replies are dropped.**
  - **Retweets** are excluded by the request, and dropped if any arrive.
- **The check's outcome:**
  - `new_items` when items were added, otherwise `no_new_items`;
  - `deferred` only when no request was made, because fewer than 5 reads were left. An account that answered with 0 posts is `no_new_items`. `deferred` takes precedence over `new_items`: a deferred account whose earlier pending items are in the run stays `deferred`;
  - `failed` on an `XApiError`.

  `entries_seen` is the number of posts returned. `http_status` and the message come from the error, so a 429 reads as rate limited.
- **Transactions.** Each account is one transaction. On an error, its new items and id changes are rolled back. The reads already made are still counted in `x_reads`, because X bills them.
- **Run counters.** `DigestRun.x_waiting_accounts` counts accounts that end the run `deferred`, or with a gap. Both counters are committed right after the X checks, before `caption_pass`, so a run that fails later keeps its read count. `run_detail` returns `x_reads` and `x_waiting_accounts` (`runner.py:413-440`).
- **The check-rewrite step** (`runner.py:244-258`) skips checks whose status is `deferred`, as well as `failed`, in both its select (`:245`) and its update guard (`:250`). Otherwise it would turn a deferred check into `no_new_items`.
  - Readers of the new status: the rewrite step; `Source.last_check_status` (`Sources.tsx:91-94`); the Home check list (`Home.tsx:38-43`).
  - The "needs attention" filter (`Home.tsx:82`) does not list `deferred`. The waiting count is shown in the run result instead.
- **Settings.** `CATCHUP_X_READS_PER_RUN`, default 200, in `config.py`, parsed by a new helper that accepts 0 and rejects negative or non-integer values. The existing `positive_env` rejects 0 (`config.py:15-22`). A value of 0 defers every X account.

### D6. X posts as items (capabilities `x-accounts`, `digest-generation`, `content-collection`)

- **Item fields:**
  - `identity_key` is the post id;
  - `link` is `https://x.com/<username>/status/<id>`;
  - `title` comes from the `_entry_title("", text)` rule;
  - `published_at` is `created_at`;
  - `content_text` is the post's text (D2), cut to 16,000 characters;
  - `content_origin` is `"x"`;
  - `site_name` is `"X · <name>"`;
  - `entry_author` is `"<name> @<username>"`;
  - `entry_links` are the `urls`, as `{url, text: ""}`, with `x.com` and `twitter.com` links kept (the context pass drops them);
  - `image_candidates` are the photos, as `{url, alt}`, through `filter_image_urls` (`sources/feeds.py:115-140`);
  - `captured_replies` are the kept replies;
  - `state` is `pending`.
- **Duplicates.** An existing `identity_key` for the source is skipped, so a re-read gap adds nothing twice.
- **The pipeline:**
  - `select_pending` admits kind `x` (`runner.py:45`);
  - `gather_context` admits kind `x`, and treats it like `capture`: the item's origin as the site, no comments, and `captured_replies` as `A1` (`gather.py:28,35-36,42-44`). Its own address is never fetched (`links.py:29-30`).
  - The summary and digest use `item.site_name` (`runner.py:46,319`).
  - `DigestItem.source_kind` is `x`.

### D7. Clearing delivered X posts (capability `x-accounts`)

- **Where.** In the delivery loop (`runner.py:366`), for items of kind `x`, after the `DigestItem` is added: `content_text = ""`, `captured_replies = None`, and `item.contexts.clear()`, which deletes their rows (`models.py:114`).
- **Who reads these fields after delivery:**
  - nothing reads `content_text` after delivery (Context);
  - `captured_replies` is read only by the context pass, for pending items;
  - digest items keep `context_links` without text.
  - The next run still dedupes on `identity_key`.
- **The trace.** One post through this run and the next:
  1. it is read, made `pending`, summarized, and delivered;
  2. its text is cleared;
  3. the next run's Phase B starts after `newest_id`, so the post is not requested again.

  If it lies inside a gap that is re-read, its `identity_key` already exists, so it is skipped.
- **Deleting an account source** deletes its items, and its `x_accounts` row, by cascade.

### D8. The extension (capabilities `browser-extension`, `model-settings`)

- **Address detection.** A copy of D3's rules decides whether the tab is an X account address, a profile or a post. Every host under `x.com` or `twitter.com` counts as an X page (D3, fix round 1).
  - Profile and post pages show "Follow this account" and "Add this page". Other X pages show only Add.
  - The "X accounts cannot be followed" line (`popup.ts:153`) is removed everywhere.
- **The preview.** For kind `x`, the popup shows `@username` and `site_url` in place of the feed URL (`popup.ts:236`).
- **Follow** reuses `previewSite` and Confirm (`popup.ts:220-260`), with `POST /sources/preview {url}`.
- **The token prompt.** On `x_token_required`, the popup shows a labelled password field, "X API token", with Save and a one-line hint on where to get one: "Copy the Bearer token of your X App from console.x.com." (fix round 1: run 1 had no hint).
  - Save sends `PUT /settings/x {token}`, then previews again.
  - On `x_token_exists`, it shows "Replace the X token in CatchUp Settings.", with Open CatchUp.
  - **Fix round 1.** On `x_token_rejected`, it shows the Sources page's wording, "X rejected the token. Replace the X token in CatchUp Settings.", with Open CatchUp. The spec requires the same error messages as the Sources page; this design's earlier wording contradicted it.
  - The token is never stored in `chrome.storage`.
- **The `api()` helper** (`popup.ts:95-121`) gains a `PUT` method.
- **Labels and wording.** `kindLabels` gains `x: 'X account'` (`popup.ts:228-233`). The error wording copy (`popup.ts:27-47`) gains the X codes.
- **Permissions.** The manifest is unchanged: no access to x.com or api.x.com. `src/test/manifest.test.ts` keeps enforcing this.

### D9. The CatchUp frontend (capability `user-interface`)

- **Settings.**
  - **A new section 5, "X accounts,"** after "Browser extension" and outside the model form, like `Settings.tsx:247-275`. It has:
    - the token password field, with "Saved token ending in …";
    - Save, Test, and Remove;
    - a note that reads are billed to the user's X developer account, and that a spending limit can be set in the X console, linking to README's X section.
  - **The first-run lede** becomes "Three quick steps, plus optional X accounts and a browser extension. Your key stays on this computer, encrypted." The returning lede becomes "Your model, digest language, YouTube options, browser extension, and X accounts."
- **Sources:**
  - `kindNames.x = 'X account'`, with a new `x` icon (`ui.tsx:43-54`, `Icon.tsx`);
  - for kind `x`, the preview shows `@username` and `site_url` in place of the feed URL (`Sources.tsx:67`), and the source row shows `site_url` (`Sources.tsx:224`), never `x:user:<id>`;
  - `describeError` gains the X codes;
  - **the inline token prompt:** on `x_token_required`, a password field, a link to README's X section, and "Save and preview";
  - the status label `deferred` → "Waits for the next run".
- **Home:**
  - the check label `deferred` → "Waits for the next run";
  - the held notes gain "N X posts read", and "N X accounts have posts waiting for the next run". **Fix round 3:** a failed run shows the same two lines, because its reads were billed and its counters are stored (D5);
  - the rail adds the X account count;
  - `DigestArticle` shows the `x` kind icon.

### D10. Policy, and README

- **README's X section** replaces "CatchUp does not follow X accounts" (`README.md:147-149,303-304`). It gives:
  - the console steps to create an App and copy its Bearer token;
  - the prices, dated 2026-10-24;
  - the advice to set a spending limit in the X console;
  - `CATCHUP_X_READS_PER_RUN`.
- **Quotes from X's Developer Policy:**
  - "You must keep all API keys or other access credentials private";
  - no use of "access credentials owned by others";
  - no requesting "developer application information … to you directly".

  README states the reading: the token belongs to the instance's owner, and stays on their computer; CatchUp's authors never receive it.
- **Deleted posts.** The 24-hour rule is stated. CatchUp clears post text after delivery, and does not watch for later deletions. CatchUp cannot delete a single digest (`api/digests.py` has only `GET` routes), so the way to comply with a request, or with the end of the user's access, is "Delete all X data" (D13).
- **Models.** Post text is sent to the user's chosen model provider, as for all content. X does not address whether that is a "third party".
- **The extension's README note on scraping** (`README.md:147`) stays for saved pages.

### D11. The field-name probe (before Droid runs)

- **The script.** Claude writes `scripts/x_probe.py`. It reads the token from the environment variable `X_BEARER_TOKEN` and takes a username. Then:
  - it calls the username lookup, the user-posts timeline (5 posts, with both the `tweet.fields` and `post.fields` spellings), and `GET /2/usage/tweets?days=1`;
  - it prints each response's status, rate-limit headers, and JSON keys, with long strings cut to 40 characters;
  - it never prints the token, or any request header.
- **The user's part.** They run it in their own shell with their own token. Then they paste the output, or save it under `work/`. Claude never sees or handles the token.
- **Afterwards.** Claude records the field names, the long-post field, and whether the usage endpoint answers, as D2a in this file. Then Droid starts. The test fixtures are invented, and shaped like the probe's output.

### D13. Delete all X data (capabilities `x-accounts`, `user-interface`)

- **Why.** X's Developer Agreement (last updated 2026-04-27) counts copies and derivative works as X Content, and requires that all of it be deleted permanently when the agreement ends. Its Developer Policy requires deleting stored content that was deleted on X within 24 hours of a request. Digest summaries, item titles, and topic overviews are derived from posts, so they count. CatchUp has no way to delete a digest today.
- **The route.** `POST /api/settings/x/delete-all`. It is not on the extension's allow-list, so a token gets 403. It checks `active_run` and deletes while holding `_start_lock`, as `start_run` does (`runner.py:33,128`), so a run cannot start in between; during a run it answers 409 `run_active` with "A digest is being made. Try again when it finishes." In one transaction, with `PRAGMA secure_delete=ON` on its connection, it:
  1. finds every `DigestItem` with `source_kind == "x"`, whether or not its `item_id` is still set (it is `NULL` when the source was deleted earlier, `models.py:197`), and the topics that hold them;
  2. deletes those digest items;
  3. for each of those topics: deletes it when it has no items left; otherwise sets `overview = ""`, and sets `title` to "其他" when the digest's `language` is `zh-Hans`, otherwise "Other", the rule of `digest/group.py:47`, because the model wrote both from the X items too;
  4. for each affected digest: deletes it when it has no items left, and sets `digest_id = None` on its `DigestRun`; otherwise sets `item_count` to its remaining items, and lowers `source_count` by the number of distinct X sources among the removed items (by `Item.source_id`, or by `source_name` when `item_id` is `NULL`);
  5. deletes every `Source` of kind `x`, which cascades to its items, their contexts, and `x_accounts`;
  6. deletes the `x_credentials` row.

  After the commit it runs `PRAGMA wal_checkpoint(TRUNCATE)`, so the deleted text does not linger in the write-ahead log. Still holding the lock, it empties the X preview cache (D4, fix round 1). It answers `{digest_items, digests, accounts}`, the counts removed.
- **Not deleted:** pages saved from x.com with the extension's "Add this page" (kind `capture`). They were not obtained through the X API, and the user chose to keep them (2026-10-26); the confirmation says so.
- **Readers of what it changes:**
  - `Digest.item_count` and `source_count` are read by `api/digests.py:34,95`, `run_detail` (`runner.py:430`), and shown as "N items · M sources" (`History.tsx:62`, `DigestArticle.tsx:59`);
  - `DigestRun.digest_id` is read by `run_detail`, which already tolerates a missing digest (`runner.py:418`). Home loads only the active run (`Home.tsx:146-150`), and deletion is refused during a run;
  - an empty overview already renders as nothing (`components/ui.tsx:20`);
  - a digest left with only Creator updates shows "Nothing could be summarized this time" (`DigestArticle.tsx:61-63`). This is accepted.
- **Unchanged.** Items and digest items of other kinds. `SourceCheck` rows go with their sources (`models.py:136`), and run error messages are fixed wording (`runner.py:398-410`).
- **The UI.** Settings' "X accounts" group gets "Delete all X data", with an inline confirmation, like source deletion (`Sources.tsx`): "Delete all X data? This removes your X token, followed X accounts, and their items in saved digests. Pages saved from X with the extension stay." Afterwards, it announces the counts. A 409 shows the route's message, and nothing changes.

### D12. Alternatives considered

- **Proposal 2: Sign in with X (OAuth 2.0 with PKCE), through the user's own public-client App, and a following-list picker.**
  - **For:** X's policy suggests it, and no long-lived secret is copied around.
  - **Against:**
    - whether X accepts a loopback callback is unverified;
    - there are more moving parts (`state`, refresh tokens, expiry);
    - the picker costs $0.010 per account listed;
    - more work before the Alpha (2026-11-05).
  - It can follow later.
- **The extension calls the X API itself, with the key kept in the browser.** Rejected:
  - posts would be read only when the user clicks;
  - the extension would need access to `api.x.com`, against "What the extension never does".
- **Scraping x.com, or a logged-in collector.** Rejected under X's terms and automation rules (D-024).
- **Dropping posts beyond the limit.** Rejected by the user: posts wait.
- **Deleting digest items when one X account is deleted.** Not chosen by the user (2026-10-26); "Delete all X data" covers the terms' cases in one step.
- **Storing baseline posts at confirm,** as feeds do. Unneeded: `newest_id` marks where reading starts, and avoids paying for old posts.
- **Recent search for the author's replies** (`conversation_id:` with `from:`). Not needed: the timeline already returns the author's replies, and search would cost extra reads.

## Risks / Trade-offs

- **[The API's field names differ from the docs]** → the probe (D11), before Droid runs. The client hides field names behind dataclasses (D2).
- **[`most_recent_tweet_id` is missing or stale]** → fall back to the newest previewed post's id, or `start_time=followed_at`. The probe shows whether the field is returned.
- **[A reply is billed but dropped]** → the user accepted this cost. Every returned post counts toward the limit, so the limit still caps the spend.
- **[Prices or terms change]** → README dates its prices. The X console's spending limit is the hard ceiling.
- **[The usage endpoint is unavailable for the token's plan]** → Test reports the HTTP status, and following still works. The probe shows the answer.
- **[An error after some pages wastes those reads]** → each account is one transaction. The reads are still counted, and the next run re-reads. X deduplicates repeats within the same UTC day.
- **[A post deleted on X after delivery]** → its text is already cleared. The digest's summary and title remain; README says how to delete a digest.
- **[A protected account's timeline error is undocumented in detail]** → map an authorization `errors` entry naming the account to `x_account_protected`, before the generic 401/403 rule. Wrong guesses show as "X rejected the token" for one account, while other accounts still read, which tells the user it is not the token.
- **[A credits-exhausted answer is undocumented]** → it maps to `fetch_failed` with its HTTP status, and the source shows it.
- **[The extension's token gains a settings write]** → only `PUT /api/settings/x`, refused when a token exists. Tests prove that the extension cannot read, replace, or remove the token.

## Migration Plan

- **Migration `0007_x_accounts`:**
  - creates `x_credentials` and `x_accounts`;
  - adds `digest_runs.x_reads` and `digest_runs.x_waiting_accounts` (integers, server default `0`).
  - **Downgrade:** deletes `sources` rows of kind `x` (their items cascade), drops the two tables, and drops the two columns. It MUST use `batch_alter_table("digest_runs", recreate="never")`: with the default, SQLite recreates `digest_runs`, and dropping it fails, because `digests` and `source_checks` reference it (a probe showed `FOREIGN KEY constraint failed`).
- **Rollout:**
  1. Build the image.
  2. Run `scripts/docker-smoke.sh`.
  3. Back up the 8800 volume.
  4. Rebuild the container.
  5. The user pastes their token in Settings, and follows one or two accounts.
- **Rollback:** restore the volume backup. The downgrade also works, and loses X sources.

## Testing

- **Backend:** pytest with respx mocking `https://api.x.com`, fixtures shaped by the probe, `FakeModel` for runs, and no real sleeps. Seams:
  - the address recognizer;
  - the client's parsing and error mapping;
  - the settings routes and allow-list;
  - preview and confirm, with the cache;
  - `check_x_account`, with the budget and gaps;
  - the run's ordering, deferral, rewrite step, and counters;
  - `select_pending` and `gather_context` for kind `x`;
  - clearing at delivery;
  - migration up and down.
- **Frontend:** vitest with mocked `fetch`, and `expectAccessible` on each new state: the Settings X group, the Sources inline prompt and X errors, and the Home notes and labels.
- **Extension:** vitest with a fake `chrome`. Seams: X address detection, Follow on profile and post pages, the token prompt and its errors, and the manifest unchanged.
- **Live:**
  - Claude runs the Docker smoke script.
  - The user follows real accounts on the rebuilt 8800 instance with their own token, and Claude checks the stored items, the reads count, and a cleared delivered post.
