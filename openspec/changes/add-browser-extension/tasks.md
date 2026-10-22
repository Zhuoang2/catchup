# Tasks

Implementer notes:
- **Read first.** Read `proposal.md`, `design.md` (D1–D11), and the seven spec deltas under `specs/`. Line numbers in `design.md` are at main c4b7251, so re-check them before editing. If something looks wrong or contradictory, stop and report instead of redesigning.
- **Work test-first with the `tdd` skill** (D-016). For each task, write its checks as failing tests, watch them fail, then implement. The seams named in each task count as agreed.
- **Test rules:**
  - **Backend:**
    - Use `TestClient`, `respx`, and the autouse DNS block, with `FakeModel` for runs.
    - A request that must not happen gets a mocked route, and `route.call_count == 0`.
    - Write tokens in tests as clearly fake values created by the test. Do not hard-code token-like strings that the pre-commit secret check could flag.
  - **Frontend:** mock `fetch`, run `expectAccessible` on new states, and use no real timers.
  - **Extension:** vitest with jsdom, a fake `chrome` object (`storage.local`, `tabs.query`, `tabs.create`, `scripting.executeScript`, `runtime.openOptionsPage`), and a mocked `fetch`.
  - **Fixtures:** invented, and shaped like the real markup. Do not copy text from real sites.
- **Out of scope:**
  - Firefox and Safari;
  - Web Store publishing;
  - a service worker or content scripts;
  - following X accounts;
  - other people's X replies;
  - "generate now".
- **Commits.** Commit after each task group. Do not push, tag, or open a PR.

## 1. Connection tokens and the cross-site exception

- [x] 1.1 **Migration and models** (design D2, D4). Add `backend/src/catchup/migrations/versions/0006_captures.py` and the model changes:
  - the `extension_tokens` table;
  - `Item.site_name`;
  - `Item.captured_replies`.

  Tests first, in `backend/tests/test_db.py`:
  - the head is `0006_captures`;
  - an upgrade from `0005` keeps existing rows;
  - a downgrade deletes sources of kind `capture`, with their items, and drops the new columns and the table, with `recreate="never"` as in `0005` (see `0002_transcripts.py:47-48`).

  Update the existing assertions this changes, and name each in the report: the table set at `test_db.py:20-23`, and the head at `:47`, `:65`, and `:234`.

  Verify: the tests fail before, and pass after; `uv run pytest` passes.
- [x] 1.2 **Token routes** (D2), in a new `backend/src/catchup/api/extension.py`, registered in `main.py`. Tests first, in a new `backend/tests/test_extension_api.py`:
  - **Create:** `POST /api/settings/extension-tokens` with `{"name": "Chrome"}` returns the token once. The database holds only its SHA-256 hash.
  - **List:** `GET` lists `{id, name, created_at, last_used_at}`, with no token.
  - **Disconnect:** `DELETE` returns 204, and the token stops working.
  - **Names:** a name of 0, or more than 60, characters gets 422 `invalid_request`.

  Verify: the tests fail before, and pass after.
- [x] 1.3 **The token step in `cross_site_writes`** (D3), in `backend/src/catchup/main.py`, **before** the check for write methods (`:71`), so that it runs for `GET` too. Replace #59's comment at `:74`. Add `GET /api/extension/status`. Run the lookup and the `last_used_at` update in `run_in_threadpool`, with the update best-effort. Tests first, in `test_extension_api.py`. Every request carries `Origin: chrome-extension://abcdefghijklmnop` unless noted.
  1. A valid token on `POST /api/sources/preview` (with a respx feed) returns 200, and `last_used_at` is set.
  2. A valid token on `POST /api/sources` saves the source.
  3. A valid token with `Sec-Fetch-Site: cross-site` on `POST /api/sources/preview` passes.
  4. An unknown token on `POST /api/sources/preview` gets 401 `invalid_token`, and the feed route has `call_count == 0`.
  5. A disconnected token gets 401 `invalid_token`.
  6. A valid token on `PUT /api/settings/preferences` gets 403 `cross_site_request`, and the preferences are unchanged.
  7. A valid token on `POST /api/digest-runs` gets 403, and no run exists.
  8. `GET /api/extension/status` with a valid token returns `{name, waiting: 0}`. Without a token it gets 401 `invalid_token`.
  9. Requests without `Authorization` still behave as in `tests/test_cross_site.py`, which must pass unchanged.
  10. `Authorization: Basic …` with a foreign `Origin` on `PUT /api/settings/preferences` gets 403 `cross_site_request`, the same as with no header. With the instance's own `Origin`, it gets 200.
  11. A valid token on `POST` and on `GET /api/settings/extension-tokens` gets 403 `cross_site_request`, so a token cannot create or list tokens.
  12. A `last_used_at` write that raises `OperationalError` (patched) does not fail the request.

  Named mutations, each to be seen failing, then reverted:
  - "accept a valid token on every route" fails 6 and 7;
  - "skip the token lookup" fails 4 and 5;
  - "do not update `last_used_at`" fails 1.

  Verify: 1–8 fail before; all pass after; `uv run pytest` passes.

## 2. Saved pages: the API and the built-in source

- [x] 2.1 **`POST /api/captures`** (D4, D5), in `api/extension.py`. Move the image URL filter out of `_entry_images` into a shared helper in `backend/src/catchup/sources/feeds.py`, used by both. Tests first, in `test_extension_api.py`:
  - **The first capture** creates the built-in source: kind `capture`, title "Saved from browser", `feed_url` `catchup:captures`. It also creates a pending item with all D4 fields.
  - **Caps:** values over a cap are cut. Text over 16,000 characters is cut to 16,000. Replies over 10, or over 4,000 characters in all, are cut. More than 8 images, or more than 50 links, are cut.
  - **Filters:** `javascript:` links are dropped, and `data:` and avatar images are dropped by the shared filter.
  - **Normalization:** `HTTPS://Example.COM/a#x` gives `identity_key` `https://example.com/a`.
  - **Replace while pending:** a second capture of the same URL replaces the item. It clears `summary`, `summary_language`, `summary_images`, `context_status`, and the item's context rows.
  - **Add after delivery:** when the item is delivered, a second capture adds a new pending item, with `<url>#<time>` as its identity.
  - **Third save:** deliver, save, save again gives exactly one pending item for the address. A key containing `%` or `_` does not match other addresses, because the match uses `autoescape=True`.
  - **During a run:** while a run is active, saving an address that is waiting gets 409 `run_active`, and the waiting item is unchanged. Saving a new address is accepted.
  - **Two first captures at once:** an `IntegrityError` when creating the built-in source (simulate it) is caught, and the capture is stored under the existing source.
  - **No site name:** a blank `site_name` is stored as the URL's host.
  - **Bad bodies:** a non-http(s) `url`, or an empty `title` and `text`, gets 422.
  - **Feed parsing** is unchanged: `tests/test_discovery.py` passes unchanged.

  Verify: the tests fail before, and pass after.
- [x] 2.2 **Listing and removing** (D5), plus the source list. Tests first:
  - `GET /api/captures` lists only pending captures, newest first.
  - `DELETE /api/captures/{id}` returns 204 for a pending capture, and 404 for a delivered one or another source's item.
  - `GET /api/sources` includes the captures source, with `waiting_count`.
  - Deleting the captures source removes its waiting items, and earlier digests keep their snapshots.

  Verify: the tests fail before, and pass after.

## 3. Saved pages in the run

- [x] 3.1 **Checks, pending selection, and the site name** (D6), in `backend/src/catchup/digest/runner.py`. Tests first, in `backend/tests/test_digest_runner.py`:
  - **No check for the built-in source.** With one feed source and one waiting capture, the run records one check, and `sources_total` is 1. There is no `SourceCheck` row for the captures source, and its `last_check_at` stays null. A respx route cannot test this, because `safe_fetch` refuses `catchup:captures` before any request.
  - **Captures are summarized.** The capture is summarized, and appears in the digest with `source_name` equal to its `site_name` and `source_kind` `capture`.
  - **The site name reaches the model.** The grouping call receives the site name, and the image alt fallback uses it.
  - **Only captures waiting.** The run succeeds with zero checks, and includes the capture.

  Verify: the tests fail before, and pass after.
- [x] 3.2 **The context pass for saved pages** (D6), in `backend/src/catchup/context/gather.py`. Tests first, in `backend/tests/test_context_gather.py`:
  - **Linked pages are read.** A capture whose links include a public article gets an `L1` part.
  - **The saved page is never fetched.** The route for `item.link` has `call_count == 0`.
  - **The item's own site.** A link on the captured page's own site with a `/tag/` path is dropped, by the item's origin. A link on another site is kept.
  - **Author replies.** `captured_replies` become an `A1` part after the link parts, titled "Author replies (2)", with no comment-feed request.
  - **Replies beyond the budget.** When an earlier feed item spends the whole fetch budget, a later capture item still gets its `A1` part.
  - **Status.** A capture with replies and no links is `gathered`. A capture with no replies and no links is `none`.
  - **After a redirect.** A link that redirects to a `/tag/` page on the captured page's own site is dropped, because the plan's `site_url` (`gather.py:41`, `:97`) is the item's origin.
  - **End to end,** in `test_digest_runner.py`. Post a capture shaped like an X post, with `site_name` "X · Name", an article link, and 2 replies, then run with `FakeModel`. The digest item has `source_name` "X · Name", its `link` is the saved URL, and `context_links` contains the article. The saved URL's route has `call_count == 0`.
  - **Feed items are unchanged:** the existing gather tests pass unchanged.

  Verify: the tests fail before, and pass after.

## 4. The CatchUp frontend

- [x] 4.1 **The fourth kind on Sources and Home** (D7), in `frontend/src/components/ui.tsx`, `pages/Sources.tsx`, `pages/Home.tsx`, and `components/DigestArticle.tsx`. Tests first:
  - The captures row shows "Saved from browser" and "2 pages waiting", with no feed URL and no check chip, and its delete confirmation works.
  - Home's counts and rail leave the captures source out: one feed source plus captures reads "1 source".
  - `noSources` (`Home.tsx:216`) still counts the captures source: with only saved pages, Generate is enabled.
  - After a run with only captures, the result line (`Home.tsx:87`) shows no "· 0 sources".
  - A digest item of kind `capture` renders its icon, and its site name as the source.
  - axe passes.

  Verify: the tests fail before, and pass after; `npm test -- --run` and `npm run build` pass.
- [x] 4.2 **The Settings group** (D7), in `frontend/src/pages/Settings.tsx`, as section 4, "Browser extension". It goes **after and outside** the model-settings `<form>`, with its own form, message, and error state. Update the lede at `:126` for four sections. Tests first, in `Settings.test.tsx`:
  - **Connecting** with the default name "Chrome" shows the token once, in a read-only field that is `aria-describedby` the note.
  - **Connecting sends no `PUT /api/settings/model`**, and pressing Enter in the name field connects. It does not save the model form.
  - **Copy** writes the token to a mocked `navigator.clipboard.writeText`, and announces "Copied." in a status region.
  - **Copy fails:** with `navigator.clipboard` undefined, or `writeText` rejecting, the field is selected, and "Copy failed. Select the token and copy it." is announced.
  - **The list** shows name, connected date, and "Never" for a browser not used yet.
  - **Disconnect** removes the row.
  - **Reloading** shows no token.
  - axe passes.

  Verify: the tests fail before, and pass after.

## 5. The extension: package, options, and Follow this site

- [x] 5.1 **The package** (D1), in a new folder `extension/`:
  - **Files:**
    - `package.json`, with its lock file;
    - `tsconfig.json`;
    - `vite.config.ts`, with `popup.html` and `options.html` at the root of `extension/` as its inputs, so that they build to the root of `dist/`;
    - `public/manifest.json`, which Vite copies to `dist/`;
    - a small plugin that emits `frontend/public/icon-192.png` as the PNG icon. Do not use the SVG as a manifest icon.
  - **Options validation.** The options page accepts only `http://127.0.0.1:<port>` or `http://localhost:<port>` as the server address, and explains why otherwise.
  - **The options page:**
    - It has the server address (default `http://127.0.0.1:8000`) and the token, stored in `chrome.storage.local`.
    - "Test connection" calls `GET /api/extension/status`, and shows the browser's name or the error.

  Tests first:
  - **The manifest:** `permissions` is exactly `activeTab`, `scripting`, `storage`; `host_permissions` is exactly `http://127.0.0.1/*`, `http://localhost/*`; there is no `background`, `content_scripts`, or `externally_connectable` key.
  - **Options:** they save and load, and "Test connection" sends `Authorization: Bearer <token>` to the configured address only.
  - **The not-connected popup:** with no token, it shows the connect text and the options link, and `fetch` is not called.
  - **The options page** refuses `http://192.168.1.5:8000` and `https://example.com`, with a message.
  - **A build check** (a script or test run after `npm run build`) reads `dist/manifest.json`, and fails when the popup, the options page, or an icon it names is missing from `dist/`.

  Verify: `npm test -- --run` and `npm run build` pass in `extension/`, and `dist/manifest.json` exists.
- [x] 5.2 **Follow this site** (D8). Tests first, in the popup tests:
  - **Preview, then confirm.** Preview posts the active tab's URL with the token, and renders title, kind, feed URL, notice, and entries. "Confirm" posts `/api/sources`, and "Cancel" sends nothing.
  - **Errors:** `duplicate` shows the server's message; `no_feed` and the `fetch_failed` statuses show the same texts as `frontend/src/pages/Sources.tsx`; a 401 shows the not-connected state.
  - **X tabs:** on `https://x.com/someone`, it shows the cannot-follow message, with no request. That it offers "Add this page" instead is tested in 6.2, once that button exists.
  - **The rest of the popup:** the waiting count comes from `/api/extension/status`, and "Open CatchUp" opens the server address with `chrome.tabs.create`.
  - axe passes on the popup states.

  Verify: the tests fail before, and pass after.

## 6. The extension: Add this page

- [x] 6.1 **The generic extractor** (D9), in `extension/src/extract/generic.ts`, as **one self-contained function**: every helper and cap inside its body, with no imports and no module-level constants. Chrome serializes it, and drops everything outside it. Build the text with a `TreeWalker`, use `currentSrc || src` for images, and never edit the DOM. Tests first, on invented fixtures in `extension/src/extract/fixtures/`:
  - an article page with canonical URL, `og:` metadata, an author meta, `article:published_time`, two images, and a nav and footer whose text is left out;
  - a page with no metadata, which falls back to `document.title`, the host, and `body`;
  - **the caps:** 16,000 characters, 8 images, and 50 links;
  - links and images that are not http(s) are dropped;
  - **paragraphs stay apart:** two `<p>` elements give two lines, not run-together words;
  - **serialization:** each case also passes when the function is first round-tripped through `new Function('return (' + fn.toString() + ')()')`. Mutation: move a helper to module scope; the round-trip case must fail;
  - **the page is unchanged:** `document.body.outerHTML` is the same after extraction.

  Verify: the tests fail before, and pass after.
- [x] 6.2 **The popup's add-page flow** (D8). Tests first:
  - **Saving.** "Add this page" calls `chrome.scripting.executeScript` on the active tab with the generic extractor. Then it posts the checked result to `/api/captures`, and shows "Saved. It will be in your next digest." with the new waiting count.
  - **Unreadable pages.** When `executeScript` rejects, as on `chrome://` pages, or returns an empty array or no `result`, it shows "This page can't be read by extensions.", with no request.
  - **One save at a time.** "Add" is disabled while a save is in progress. A 409 `run_active` shows its message.
  - **X profile pages.** On `https://x.com/someone`, the follow message offers "Add this page", and the button works.
  - **Checking the result.** A result with wrong types, or with values over a cap, is checked or cut before it is sent.
  - **Remove.** "Remove" calls `DELETE /api/captures/{id}`, and updates the count.

  Verify: the tests fail before, and pass after.

## 7. The extension: X posts

- [x] 7.1 **The X extractor** (D9), in `extension/src/extract/x.ts`, selected by the popup for `x.com` and `twitter.com` at `/<user>/status/<id>`. It is one self-contained function, like 6.1, and returns `null` when no matching post is found. Tests first, on invented fixtures shaped like X's markup (`article[data-testid="tweet"]`, `tweetText`, `User-Name`, `time[datetime]`, `tweetPhoto`):
  - **The author's replies only.** A post with two replies by its author, and two by others, gives the post's text, author, time, and images, plus exactly the author's two replies, in order.
  - **Links:**
    - a `t.co` link whose text is a full URL is recorded with that URL;
    - one whose text ends with "…" is left out;
    - a plain link is recorded.
  - **site_name** is "X · <name>", and **title** is "<name> on X".
  - **No post article:** the extractor returns `null`. The popup then runs the generic extractor in a second `executeScript` call, and saves its result.
  - **The popup** uses the X extractor on a status URL, and the generic one elsewhere.
  - **Serialization:** the same `new Function` round trip as in 6.1 passes.

  Verify: the tests fail before, and pass after.

## 8. Docs, CI, and checks

- [x] 8.1 **CI and README.**
  - **CI:** add an `extension` job to `.github/workflows/ci.yml` that runs `npm ci`, `npm test -- --run`, and `npm run build` in `extension/`.
  - **README:** add an extension section:
    - building, and loading unpacked in Chrome (Developer mode, which Chrome 134 and later needs to keep it enabled) and in Edge;
    - connecting, in Settings → Browser extension;
    - what it reads, and when;
    - what it never does;
    - that X's terms prohibit scraping in any form, so saving X pages is at the user's own risk.

  Verify: the CI file parses, and the README names the permissions and the X note.
- [x] 8.2 **Final checks and docs.**
  - **Builds:** `npm run build` in `frontend/` first, then `uv run pytest --cov=catchup --cov-report=term` in `backend/`, `npm test -- --run` in `frontend/`, and `npm test -- --run` and `npm run build` in `extension/`.
  - **The image:** `docker build -t catchup:extension-local .`, then `scripts/docker-smoke.sh catchup:extension-local`.
  - **Validation:** `openspec validate add-browser-extension --strict`.
  - **The report:** write `docs/process/test-report-add-browser-extension.md`, with the red-first result for each group, the mutation results, and the commands' real results. Name the manual checks that were not performed:
    - loading the extension in a real Chrome;
    - which `Origin` the server sees;
    - whether a popup click grants `activeTab`;
    - saving a real X post, which the user must do in their own logged-in browser.
  - **The coverage summary** (`docs/process/coverage-summary.md`): add this change's line.
  - **The AI usage log** (`docs/process/ai-usage-log.md`): add your entry after the latest entry, with a faithful excerpt of the prompt you actually received, and the tool and model. Leave out the session id.

  Verify: every command passes, and the report has the actual numbers.

## 9. Fix round 1 (review findings)

Read design D12. Each item below is a real defect (a), a plan error (b), or a test that cannot fail. Use `diagnosing-bugs` for 9.1, 9.3 and 9.4, and `tdd` for the rest. Every check is red first, either as a failing test before the fix, or as a named temporary mutation, applied and then reverted, where the behavior is already right. Commit after each task.

- [x] 9.1 **Replies beyond the budget** (`backend/src/catchup/context/gather.py`). Test first, in `backend/tests/test_context_gather.py`, with items in this order: a feed item whose links spend the budget, a feed item with no replies, a capture with no replies, then a capture with replies. The last capture gets its `A1` part, and is `gathered`.

  Verify: the test fails on the current code (`break`), and passes with `continue`.
- [x] 9.2 **Exact address matching** (`backend/src/catchup/api/extension.py`). Tests first, in `backend/tests/test_extension_api.py`:
  - deliver `https://example.com/a`, save it again (so that `…/a#<time>` waits), then save `https://example.com/A`. Two different items wait, and the `/a` item is unchanged;
  - replace the `%`/`_` test with one that can fail: a waiting `https://example.com/axb#<time>`, and a new save of `https://example.com/a_b`, must add a new item.

  Verify: the case test fails on the current code, and passes with a `substr` comparison. The `%`/`_` test passes on the current code, because `autoescape=True` is there; its red step is the named mutation "remove `autoescape=True`", applied before the `substr` change, and then reverted.
- [x] 9.3 **The server's capture and token rules** (`backend/src/catchup/main.py`, `api/extension.py`). Tests first:
  - `Authorization: Bearer some-proxy-token` without the `cu_` prefix, with the instance's own `Origin`, on `PUT /api/settings/preferences`, gets 200. With a foreign `Origin`, it gets 403 `cross_site_request`.
  - A valid token on `DELETE /api/sources/1` gets 403, and the source still exists.
  - `POST /api/captures` and `DELETE /api/captures/{id}` without a token get 401 `invalid_token`, with no effect. Send these without an `Origin` header, as a tool would, so that the route answers and not the cross-site rule.
  - A capture with an empty title, and text whose first 81 characters contain no space, gets exactly the first 80 characters of its text as its title.
  - Link texts and image alts over 500 characters are cut to 500.

  Verify: the new behavior checks fail before the fix. The rule checks that already pass (DELETE on sources; the token on the capture routes) fail under named mutations: widen the DELETE branch to `/api/`, and remove `require_connection` from each capture route.
- [x] 9.4 **Readability for generic pages** (D12), in `extension/`.
  - Add `@mozilla/readability` `0.6.0` with `npm install --save-exact`, so that `package-lock.json` is updated for CI's `npm ci`.
  - The build copies `node_modules/@mozilla/readability/Readability.js` to `dist/readability.js`, and its `LICENSE.md` to `dist/readability-LICENSE.md`, in the existing plugin in `vite.config.ts`.
  - **The build check** (`scripts/check-build.mjs` and `src/test/build.test.ts`) also requires these two files. It also requires every `/assets/…` file that `popup.html` and `options.html` link (the hashed CSS and JS). Update `build.test.ts`'s dummy files to match.
  - Add `extension/src/extract/readable.ts`, with `extractReadable`, which is self-contained and uses the global `Readability`.
  - Fix the generic extractor's exclusion (only between the node and the root), for text, links and images.

  Tests first, on a new invented fixture shaped like the problem page: no `<article>`, a post body, a "Recent articles" sidebar, a sponsor block with `class="sponsor"` **outside** the post body, and a footer year list.
  - **Readability:** load it into the jsdom window with `window.eval` of the file's source, and remove it with `delete` afterwards. `extractReadable` returns the post's text, and only the post's links, with no sidebar, sponsor, or year text or links. The original document is unchanged.
  - **Short results:** on a page of navigation and lists only, the parsed text is under 200 characters, so it returns `null`.
  - **Serialization:** it passes the `new Function` round trip, with `Readability` loaded.
  - **Missing library:** without `Readability`, it returns `null`.
  - **The generic extractor:**
    - on `<body><form><main><p>Main text</p></main></form></body>`, it returns "Main text";
    - on a root with a `nav` inside, it skips that nav's text, links, and images;
    - the root element itself is never treated as excluded, even when it is a `<form role="main">`.
  - **The popup:**
    - On a non-X page, and on an X profile page, it injects `readability.js` (`{files}`), then `extractReadable` (`{func}`). It falls back to the generic extractor when that returns `null`, or when the `files` injection rejects.
    - On an X post, it keeps the X extractor first.
    - Update the existing tests that expect the first call to be `extractGeneric` (`popup.test.ts:136-139` and `:199-201`). Make the `executeScript` mock answer by `details.files` or `details.func.name`, instead of one `mockResolvedValue`.

  Verify: the fixture tests fail before the change, and the full extension suite and build pass.
- [x] 9.5 **X: the author's handle** (`extension/src/extract/x.ts`). First update the fixture `extension/src/extract/fixtures/x-post.html`: in every `User-Name`, add a display-name link and an `@handle` link to `/<handle>`, and, on non-focal articles, a time link to `/<handle>/status/<id>`. Keep the existing tests passing, with links inside `User-Name` left out of `links`. Then, tests first:
  - a reply whose display name is "Fan of @alice", but whose links go to `/mallory`, is not saved as an author reply;
  - an article above the post, written by the author, is not saved as a reply. This already passes (`x.ts:30` loops over the articles after the post); its red step is the named mutation "take replies from every article except the post" (`articles.filter(a => a !== article)`).

  Verify: the first test fails before the fix, and the second fails under its mutation.
- [x] 9.6 **Popup fixes and styling** (D12). Tests first, in the popup tests:
  - a rejected `fetch`, or a non-JSON 502, **after the popup has connected**, shows "Could not connect to CatchUp." in these actions, which today show other text:
    - "Add this page" (today: "This page can't be read by extensions.");
    - "Follow this site" and "Confirm" (today: the raw "Failed to fetch");
    - "Remove" (today: the raw error).

    The first status check already shows the right text, so it does not count as a red step;
  - the preview shows "Website feed" for `feed`;
  - the count shows "1 page waiting" and "2 pages waiting".

  Then add `popup.css` and `options.css` (D12), linked from both HTML files, with light and dark tokens. Re-run axe on every popup and options state.

  Verify: the tests fail before the fix, and pass after; axe passes; the build check sees the CSS emitted.
- [x] 9.7 **Frontend and backend tests that cannot fail.** Make each one able to fail, and show it with its named mutation:
  - **Home's `noSources`** (`frontend/src/pages/Home.test.tsx`): with only the captures source and **no** run, Generate is enabled. Mutation: exclude captures from `noSources`.
  - **Home's hero and rail counts.** Use two renders: with a digest, the hero's `.hero-meta` reads exactly "1 source · Manage sources"; with no digest, the rail's `.rail-big` reads exactly "1". Mutations: count captures in the hero; count captures in the rail.
  - **The item's own site** (`backend/tests/test_context_gather.py`). Use a saved page on `https://blog.example/post`, with links to `https://blog.example/tag/x` and `https://other.example/a`. Mock `https://blog.example/robots.txt` and `/tag/x` with 200 pages, because `fetch()` swallows respx's unmocked-request error. Assert that the tag route has `call_count == 0`, and that `other.example/a` is stored. Mutation: use `source.site_url`.
  - **The downgrade** (`backend/tests/test_db.py`): before the downgrade, add an `item_contexts` row and a `digest_items` row for a feed item. Afterwards, the digest item's `item_id` is still that feed item's id, and the feed item's context row is kept. Mutation: remove `recreate="never"`. Both assertions fail under it: the contexts are deleted, and `item_id` becomes null.
  - **The first-run lede** in `frontend/src/pages/Settings.tsx`. Add a test, since none asserts it today: with no saved key, the lede reads exactly "Three quick steps, and an optional browser extension. Your key stays on this computer, encrypted."

  Verify: each mutation fails its check, and is reverted.
- [x] 9.8 **Docs and checks.**
  - **README:**
    - complete the "never does" list: cookies, saved passwords, site storage, background reading, and scrolling, clicking, or opening pages;
    - add a notice for Mozilla Readability (Apache-2.0);
    - add the known limit from D12.
  - **`docs/process/test-report-add-browser-extension.md`:** add a "Fix round 1" section, with each check's red result and the mutation table.
  - **The checks:** run them all — `npm run build` in `frontend/` first, backend coverage, `npm test -- --run` in `frontend/`, the extension's tests and build, `docker build` and `scripts/docker-smoke.sh`, and `openspec validate add-browser-extension --strict`.
  - **The coverage summary and the AI usage log:** add the fix-round line, and your entry, with a faithful excerpt of the prompt you received. Leave out the session id.

  Verify: every command passes, and the report has the actual numbers.
