# Tasks

Implementer notes:
- **Read first.** Read `proposal.md`, `design.md` (D1–D13, and D2a once Claude has added it), and the eight spec deltas under `specs/`. Line numbers in `design.md` are at main f1b76c0, so re-check them before editing. If something looks wrong or contradictory, stop and report instead of redesigning.
- **Work test-first with the `tdd` skill** (D-016). For each task, write its checks as failing tests, watch them fail, then implement. The seams named in each task count as agreed.
- **Test rules:**
  - **Backend.** Use `TestClient`, `respx` for `https://api.x.com`, the autouse network block (`backend/tests/conftest.py:8-20`), and `FakeModel` for runs.
    - A request that must not happen gets a mocked route, and `route.call_count == 0`.
    - Fixtures are invented, and shaped like the probe's output (D2a). Do not copy real posts.
    - Write tokens in tests as clearly fake values created by the test, such as `"test-" + "x" * 40`. Do not hard-code token-like strings that the pre-commit secret check could flag.
    - Never sleep. The X client has no retries.
  - **Frontend.** Mock `fetch`, run `expectAccessible` on new states, and use no real timers.
  - **Extension.** Vitest with jsdom, the existing fake `chrome` object, and a mocked `fetch`.
- **Out of scope:** Sign in with X; protected accounts; lists, likes, and the home timeline; other people's replies; the creator's replies to other people's posts; watching for deletions; the extension contacting X; showing prices.
- **Guards.** A check marked "guard (already green)" passes before the change, because earlier code already enforces it. Write it, see it pass, and keep it. Every other check must be red first.
- **Commits.** Commit after each task group. Do not push, tag, or open a PR.

## 0. The field-name probe (Claude and the user, before Droid)

- [x] 0.1 **Probe the live API** (D11). Claude writes `scripts/x_probe.py`. The user runs it with their own token, in their own shell. Claude records the result in `design.md` as D2a:
  - the field and parameter names that work (`tweet.fields` or `post.fields`, `note_tweet` or `note_post`);
  - whether the lookup returns `most_recent_tweet_id`;
  - whether `GET /2/usage/tweets` answers with a Bearer token.

  Verify: D2a exists, and names each of these. Droid does not start before this box is checked.

## 1. The X token: storage, routes, and Settings

- [ ] 1.1 **Migration `0007_x_accounts` and models** (D1, D4, D5; Migration Plan). Add:
  - `x_credentials` (id, `token_encrypted`, `token_last4`, `updated_at`);
  - `x_accounts` (`source_id` primary key with an `ON DELETE CASCADE` foreign key, `user_id`, `username`, `newest_id`, `gap_since_id`, `gap_until_id`, `followed_at`);
  - `digest_runs.x_reads` and `digest_runs.x_waiting_accounts` (integers, server default `0`).

  The downgrade first deletes `sources` of kind `x`, and MUST use `batch_alter_table("digest_runs", recreate="never")` (design, Migration Plan).

  Tests first, in `backend/tests/test_db.py`:
  - upgrade from `0006` creates the tables and columns;
  - a downgrade after adding an X source, its `x_accounts` row, and one item removes them, and leaves a feed source, its items, and their digest items intact.

  Update the existing checks that this changes: the exact table set (`test_db.py:19-23`), and the expected head revision (`test_db.py:69`).

  Verify: the new tests fail before the migration and pass after; `migrate(make_engine(copy_dir))` (`db.py:17,32`) on a copy of a `0006` database upgrades it.
- [ ] 1.2 **Settings routes for the token** (D1), in `backend/src/catchup/api/settings.py`. Tests first, in a new `backend/tests/test_x_settings_api.py`:
  - `GET /api/settings/x` with nothing saved gives `{token_set: false, token_last4: null}`;
  - `PUT` stores the token encrypted: the database column does not contain the token, and `GET` gives its last four characters only;
  - no response body or log record contains the token (use `caplog`);
  - `PUT` without `CATCHUP_SECRET_KEY` gives `secret_not_configured`, and stores nothing;
  - an empty token, one with whitespace, or one over 1,000 characters gives 422 `invalid_x_token`;
  - `DELETE` removes it;
  - `POST /api/settings/x/test`:
    - calls only `GET https://api.x.com/2/usage/tweets` (respx), with `Authorization: Bearer <token>`;
    - answers `{ok: true}` on 200;
    - answers `x_token_rejected` on 401;
    - answers `rate_limited`, with `retry_after` from `x-rate-limit-reset`, on 429;
    - answers 422 `x_token_required` with no token.

  Verify: the tests fail before the routes exist, and pass after.
- [ ] 1.3 **The extension may save the first token only** (D1, D8), in `backend/src/catchup/main.py` (`_extension_operation`) and the `PUT` route. Tests first, in `backend/tests/test_extension_api.py`, with a connected token and an extension `Origin`:
  - `PUT /api/settings/x` with no X token saved stores it;
  - with an X token saved, it gives 409 `x_token_exists`, and the saved token is unchanged;
  - guard (already green): `GET` and `DELETE /api/settings/x`, and `POST /api/settings/x/test`, give 403 `cross_site_request`, because the middleware refuses them before routing (`main.py:125`);
  - guard (already green after 1.2): CatchUp's own pages (same `Origin`) can still replace the token with `PUT`.

  Verify: the tests fail before the change. Then the named mutation "allow `PUT /api/settings/x` for tokens even when one is saved" fails the 409 test, and is reverted.
- [ ] 1.4 **Settings "X accounts" group** (D9), in `frontend/src/pages/Settings.tsx`. Add section 5, after "Browser extension" and outside the model form, with:
  - the password field and "Saved token ending in …";
  - Save, Test, and Remove;
  - the billing and spending-limit note, linking to `https://github.com/Zhuoang2/catchup#x-accounts`.

  Update both ledes (D9). Add `GET /api/settings/x` to the shared fetch mock, which throws on any other URL (`Settings.test.tsx:14-24`). Tests first, in `frontend/src/pages/Settings.test.tsx`:
  - with a token saved, the group reads "Saved token ending in" with its last four characters, and the input is empty;
  - Save sends `PUT /api/settings/x` and clears the field;
  - Test shows success, or the rejected-token message;
  - Remove sends `DELETE`;
  - guard (already green): saving the model form does not send any X request;
  - the returning lede reads exactly "Your model, digest language, YouTube options, browser extension, and X accounts.";
  - the first-run lede reads exactly "Three quick steps, plus optional X accounts and a browser extension. Your key stays on this computer, encrypted.";
  - `expectAccessible` passes for the empty, saved, and error states.

  Update the existing lede test. Verify: the tests fail before the change, and pass after; `npm run build` passes.

## 2. Following an account: the client, addresses, preview, and confirm

- [ ] 2.1 **The X API client** (D2), in `backend/src/catchup/sources/x_api.py`. Tests first, in a new `backend/tests/test_x_api.py`, against respx routes with probe-shaped fixtures:
  - **Lookups.** `lookup_user` and `lookup_user_by_id` parse `id`, `name`, `username`, `protected`, and the most recent post id.
  - **`user_posts`:**
    - sends the given `since_id`, `until_id`, `start_time`, `max_results`, `pagination_token`, and `exclude`;
    - asks for the D2 post fields and the media expansion;
    - does not ask for `referenced_tweets.id`;
    - returns `XPage` with `next_token` and `result_count`.
  - **A post's text:**
    - `note_tweet.text` when present, else `note_post.text`, otherwise `text` (D2a);
    - every `t.co` URL replaced by `unwound_url`, else `expanded_url`;
    - `urls` holds those destinations.
  - **Post kinds and photos:** replies and retweets are flagged; photos come with `alt_text`.
  - **Error mapping:**
    - 401 and 403 → `x_token_rejected`;
    - an HTTP 200 answer with no `data`, and an `errors` entry whose `type` ends in `resource-not-found` (D2a) → `x_account_not_found`;
    - a "suspended" entry → `x_account_suspended`;
    - an authorization entry naming the account → `x_account_protected`;
    - 429 → `rate_limited`, with `retry_after` from `x-rate-limit-reset`, a message starting with `RATE_LIMIT_PREFIX`, and `http_status` 429;
    - 500 → `fetch_failed` with 500;
    - a transport error → `fetch_failed` with no status.
  - **Limits:** a body over 5 MB is refused; one request per call, with no retry.

  Verify: the tests fail before the module exists, and pass after.
- [ ] 2.2 **Recognizing X addresses** (D3), in `backend/src/catchup/sources/x_accounts.py`. Tests first, in a new `backend/tests/test_x_accounts.py`, as a parameterized table:
  - `https://x.com/simonw`, `https://www.x.com/simonw/`, `https://mobile.x.com/simonw/media`, `https://twitter.com/simonw/status/123`, and `http://x.com/Simon_W` give their usernames;
  - `https://x.com/home`, `https://x.com/i/lists/1`, `https://x.com/search?q=a`, and `https://twitter.com/HOME` raise `not_an_x_account`;
  - on an X host, a missing segment (`https://x.com/`) or a 16-character segment raises `not_an_x_account`;
  - other hosts, such as `https://example.com/simonw` and `https://notx.com/simonw`, return `None`.

  Verify: the tests fail before the module exists, and pass after.
- [ ] 2.3 **Preview and confirm for X accounts** (D4), in `backend/src/catchup/api/sources.py`, with an `XPreviewCache` on `app.state`. Tests first, in `backend/tests/test_sources_api.py`, or a new `test_x_sources_api.py`.

  **Preview:**
  - An X address with no token gives 422 `x_token_required`. The x.com page and `api.x.com` routes have `call_count == 0`, and `discover()` is not called.
  - With a token, it shows the D4 shape:
    - `feed_url` `x:user:<id>`;
    - `kind` `x`;
    - the display name as `title`;
    - up to 5 entries, whose titles come from the post text;
    - a self-reply that comes back despite `exclude=replies` (D2a) is left out of the entries.

    It makes exactly one lookup request and one posts request, with `max_results=5` and `exclude` of retweets and replies.
  - A protected account gives 422 `x_account_protected`; an unknown one, `x_account_not_found`.
  - An already followed account gives 422 `duplicate`, with `existing_source`. So does a followed account under a new username, because the id matches.
  - `not_an_x_account` for `https://x.com/home`.
  - Previewing saves nothing.

  **Confirm:**
  - Within 600 s of preview, it makes no X request, and creates the source (kind `x`, title, `site_url`) and the `x_accounts` row. `newest_id` is the lookup's most recent post id.
  - With an empty cache, it repeats the lookup by id and the five-post read.
  - Of 5 previewed posts, the 2 from the last 7 days become `pending` items with the D6 fields. No other post is stored.
  - An account that has never posted gets `newest_id` `None`.
  - A `SourceCheck` with `run_id=None` is written.

  Verify: the tests fail before the change, and pass after.
- [ ] 2.4 **The Sources page for X accounts** (D9), in `frontend/src/pages/Sources.tsx`, `components/ui.tsx`, and `components/Icon.tsx`. Tests first, in `frontend/src/pages/Sources.test.tsx`:
  - an X preview shows the "X account" badge, the method "Posts read through the X API with your token", `@username`, and the profile address, and never shows `x:user:`;
  - an X source row shows its profile address in place of the feed URL;
  - on `x_token_required`, an inline password field, a link to README's X section, and "Save and preview" appear. Saving sends `PUT /api/settings/x`, then the same preview again, and the preview appears. The result is announced;
  - each X error code shows its message: `x_token_rejected` names Settings; `x_account_protected`, `x_account_not_found`, `x_account_suspended`, and `not_an_x_account`;
  - a source row with `last_check_status` `deferred` reads "Waits for the next run";
  - `expectAccessible` passes for the prompt and the X preview.

  Verify: the tests fail before the change, and pass after; `npm run build` passes.

## 3. Reading posts on each run

- [ ] 3.1 **Reading one account** (D5, D6), as `check_x_account` in `backend/src/catchup/collection.py` or a new `backend/src/catchup/sources/x_check.py`. Tests first, in a new `backend/tests/test_x_check.py`, each calling the function with a seeded source and `x_accounts` row:
  - **The request:** `since_id=newest_id`, `exclude` with retweets only, and `max_results=min(100, remaining)`. `newest_id` becomes the largest id read.
  - **An original post** becomes a `pending` item with the D6 fields: link, title, `site_name` "X · <name>", text with link destinations, `entry_links`, `image_candidates` with alt text, `content_origin` `x`.
  - **Threads:**
    - two replies in the conversation of an original read in the same batch become its `captured_replies`, oldest first, capped at 10 replies and 4,000 characters;
    - a reply in another conversation is dropped;
    - a reply to the author's own post from an earlier run is dropped.
  - **The author's reply to a commenter** inside the author's own thread (its `conversation_id` matches an original in the batch, and its `in_reply_to_user_id` is another person) is kept, as the user chose.
  - **A retweet** that arrives anyway is dropped.
  - **Duplicates:** a post whose `identity_key` exists is not added again.
  - **Outcomes:** `new_items` with a count when items were added, otherwise `no_new_items`, including an account that answered with 0 posts. `entries_seen` equals the posts returned.
  - **An account that has never posted** (`newest_id` `None`) is read with `start_time=followed_at`, and no `since_id`.
  - **Errors:** an `XApiError` after one page rolls back that account's items and id changes, and records `failed` with the error's message and `http_status`. A 429 check is rate limited by `is_rate_limited`.

  Verify: the tests fail before the function exists, and pass after.
- [ ] 3.2 **The read limit and gaps** (D5). Tests first, in `backend/tests/test_x_check.py`, with a shared `XReadBudget`:
  - with fewer than 5 reads left, the account is `deferred`, no request is made (`call_count == 0`), and `Source.last_check_at` is unchanged;
  - with 50 reads left, and an account whose first page has 50 posts and a `next_token`:
    - the 50 are kept;
    - `newest_id` becomes the largest id;
    - the gap is set to the old `newest_id` and the oldest id read;
    - no second page is requested;
  - **the next call** with that gap reads `since_id=gap_since_id` and `until_id=gap_until_id` first. Only after the gap is fully read does it read new posts, with `since_id=newest_id`. When the gap read stops early, `gap_until_id` moves down to the oldest id read, and no new posts are read;
  - a gap read that ends with no `next_token` clears both gap ids;
  - the budget decreases by each page's `result_count`, including dropped replies.

  Verify: the tests fail before the change, and pass after. Then the named mutation "set `newest_id` but no gap when the budget runs out" fails the gap test, and is reverted.
- [ ] 3.3 **X accounts in the run** (D5, D6), in `backend/src/catchup/digest/runner.py`, `context/gather.py`, and `config.py` (`CATCHUP_X_READS_PER_RUN`, default 200, with a parser that accepts 0). Tests first, in `backend/tests/test_config.py` (default 200; `0` accepted; `-1` and `abc` rejected) and `backend/tests/test_digest_runner.py`, with `FakeModel`:
  - **Ordering:** X sources are checked after the other sources, with never-checked sources first, then the least recently checked, then by id.
  - **Two runs:** with a limit of 5, and accounts A and B each answering exactly 5 posts and no `next_token`, run 1 reads A and defers B; run 2 reads B before A.
  - **Deferral:**
    - with a limit of 5, and two X accounts, where the first answers exactly 5 posts and no `next_token`, the first is read and the second is `deferred`;
    - `run_detail` gives `x_reads` 5 and `x_waiting_accounts` 1;
    - `source_checks` has one row per counted source, so its length equals `sources_total`.
  - **The rewrite step** leaves a `deferred` check `deferred`, also when the run includes that source's items held from confirm, and the source's `last_check_status` is `deferred`. Named mutation: remove the `deferred` exclusion from both the select and the update guard (`runner.py:245,250`); the test fails, and it is reverted.
  - **Without a token:** each X source is `failed` with "X token needed", a feed source is still checked, and `api.x.com` has `call_count == 0`.
  - **Summaries:** an X item reaches the summary under "X · <name>" (`select_pending`). Its digest item has `source_kind` `x`, and links to the post.
  - **Context:**
    - an X item with a link to `https://blog.example/post` gets that page as context;
    - its own address and `x.com` links are not requested;
    - its `captured_replies` become an `A1` part, even with `replace(settings, context_fetches_per_run=0)` (the environment parser rejects 0, `config.py:15-22`).
  - **Counters survive a later failure:** when the run fails after the X checks (for example, the model raises), `x_reads` is still stored.

  Verify: the tests fail before the change, and pass after.
- [ ] 3.4 **Clearing delivered X posts** (D7), in `backend/src/catchup/digest/runner.py`. Tests first, in `backend/tests/test_digest_runner.py`:
  - after a run delivers an X item with replies and a linked-page context, the item's `content_text` is `""`, `captured_replies` is `None`, and it has no `item_contexts` rows;
  - its digest item still has the summary, title, link, `source_name`, and `context_links`;
  - a feed item delivered in the same run keeps its text;
  - guard (already green after 1.1): deleting the X source deletes its items and its `x_accounts` row.

  Verify: the tests fail before the change. Then the named mutation "clear text for every delivered item" fails the feed-item check, and is reverted.
- [ ] 3.5 **Home for X accounts** (D9), in `frontend/src/pages/Home.tsx` and `components/DigestArticle.tsx`. Tests first, in `frontend/src/pages/Home.test.tsx` and `DigestArticle.test.tsx`:
  - a check with status `deferred` reads "Waits for the next run", and is not listed under "Needs attention" after the run;
  - a finished run with `x_reads` 37 and `x_waiting_accounts` 2 shows "37 X posts read" and "2 X accounts have posts waiting for the next run";
  - singular forms: "1 X post read" and "1 X account has posts waiting for the next run";
  - `x_reads` 0 and `x_waiting_accounts` 0 shows neither line; `x_reads` 0 and `x_waiting_accounts` 2 shows only the waiting line;
  - the rail counts X accounts;
  - a digest item of kind `x` shows the X icon.

  Verify: the tests fail before the change, and pass after; `npm run build` passes.

- [ ] 3.6 **Delete all X data** (D13), in `backend/src/catchup/api/settings.py` and `frontend/src/pages/Settings.tsx`. Tests first, in `backend/tests/test_x_settings_api.py`, with digests built by a run or seeded directly:
  - **Mixed topic.** A digest with one X item and one feed item, from two sources, in one topic: after `POST /api/settings/x/delete-all`, the digest has only the feed item, `item_count` 1, `source_count` 1, and the topic's `overview` `""` and title "Other" ("其他" for a `zh-Hans` digest).
  - **An orphaned X digest item,** whose source was deleted earlier (`item_id` `NULL`), is also removed.
  - **A page saved from x.com with the extension** (kind `capture`) and its digest item remain.
  - **Digest with only X items:** the digest and its topics are removed, and its run's `digest_id` is `None`; `GET /api/digests` no longer lists it.
  - **Sources and the token.** X sources, their items, their contexts, `x_accounts`, and the token are removed. A feed source, its items, and a podcast digest item remain.
  - **The answer:** the removed counts.
  - **During a run:** 409 `run_active`, with "A digest is being made. Try again when it finishes.", and nothing is deleted. The check holds `_start_lock` (`runner.py:33`).
  - **From the extension:** guard (already green after 1.3): a connection token gets 403.

  Frontend tests, in `Settings.test.tsx` and `DigestArticle.test.tsx`:
  - "Delete all X data" asks for confirmation in place, with the D13 wording;
  - confirming sends the request, and announces the counts;
  - Cancel sends nothing;
  - a 409 shows "A digest is being made. Try again when it finishes.", and the group is unchanged;
  - guard (already green): a topic with an empty overview renders no overview paragraph (`components/ui.tsx:20`);
  - `expectAccessible` passes for the confirmation.

  Verify: the tests fail before the change, and pass after. Then the named mutation "delete every topic that held an X item" fails the mixed-topic test, and is reverted.

## 4. The extension

- [ ] 4.1 **"Follow this account" on X pages** (D8), in `extension/src/popup.ts`, with the D3 rules copied into it. Tests first, in `extension/src/test/popup.test.ts`:
  - on `https://x.com/simonw`, the popup shows "Follow this account" and "Add this page", and no "cannot be followed" line;
  - choosing it sends `POST /api/sources/preview` with the tab URL, and shows the preview with "X account", `@username`, and the profile address, never `x:user:`;
  - Confirm sends `POST /api/sources` with `feed_url` `x:user:<id>`;
  - on `https://x.com/simonw/status/1`, both "Follow this account" and "Add this page" appear, and Add still uses the X extractor;
  - on `https://x.com/home`, only Add appears, with no "cannot be followed" line;
  - the manifest test still passes unchanged.

  Update the existing X popup tests (`popup.test.ts:185-193,311`) to the new behavior. Verify: the tests fail before the change, and pass after.
- [ ] 4.2 **The token prompt** (D8). Tests first, in `extension/src/test/popup.test.ts`:
  - a preview answering `x_token_required` shows a labelled password field "X API token" and Save;
  - Save sends `PUT /api/settings/x`, with the Bearer connection token and `{token}`, then repeats the preview, and shows it;
  - `chrome.storage.local.set` is never called with the X token;
  - `x_token_exists` and `x_token_rejected` show "Replace the X token in CatchUp Settings", with Open CatchUp;
  - each X error code shows the same wording as the Sources page;
  - the axe check used in `popup.test.ts` passes for the prompt and the error.

  Verify: the tests fail before the change, and pass after; `npm run build` in `extension/` passes, including its build check.

## 5. Docs and checks

- [ ] 5.1 **README** (D10). Rewrite the X statements (`README.md:117-124,147-149,303-304`) into an "X accounts" section, with the anchor `x-accounts`:
  - creating an App and copying its Bearer token in console.x.com;
  - pasting it in Settings, on the Sources page, or in the extension;
  - prices, dated 2026-10-24;
  - setting a spending limit in the X console;
  - `CATCHUP_X_READS_PER_RUN`, and what "Waits for the next run" means;
  - the three Developer Policy quotes, and the owner-held-token reading;
  - the 24-hour deletion rule, what CatchUp clears after delivery, and what "Delete all X data" removes, and that it is how to comply when access ends or on request;
  - post text going to the user's model provider.

  Keep the saved-pages scraping note. Extend `extension/src/test/docs.test.ts` to require a `## X accounts` heading, "spending limit", and "CATCHUP_X_READS_PER_RUN", and the absence of "CatchUp does not follow X accounts".

  Verify: the README test fails before the edit, and passes after.
- [ ] 5.2 **The test report and checks.**
  - **Report.** Write `docs/process/test-report-add-x-accounts.md`, with each task's observed red result, the named mutations, and the final numbers.
  - **Checks, in this order:**
    1. `npm run build` in `frontend/`;
    2. `uv run pytest --cov=catchup --cov-report=term` in `backend/`;
    3. `npm test -- --run` in `frontend/`;
    4. `npm test -- --run` and `npm run build` in `extension/`;
    5. `docker build -t catchup:x-accounts-local .` and `scripts/docker-smoke.sh catchup:x-accounts-local`;
    6. `openspec validate add-x-accounts --strict`.
  - **Logs.** Add the coverage-summary line and your AI usage log entry, with a faithful excerpt of the prompt you received. Leave out the session id.

  Verify: every command passes, and the report has the actual numbers.
