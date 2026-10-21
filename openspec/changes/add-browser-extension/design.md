# Design

Full RePPIT change for issue #58. The research is in `research.md` (main @ f956842), the motivation in `proposal.md`, and the requirements in the spec deltas.

- **Chosen:** Proposal 1, "Click to capture". The user chose it on 2026-10-20, and set the details on 2026-10-21:
  - Chrome and Edge first;
  - a popup;
  - connecting by copying a token;
  - X supported, with the author's own replies only.
- **Default by Claude:** saved pages wait for the next manual digest run. The popup has "Open CatchUp", and no "generate now".
- **Prerequisite, merged:** #59 (`refuse-cross-site-writes`, main c4b7251, D-022). Its middleware `cross_site_writes` in `backend/src/catchup/main.py` marks where this change adds the token exception.
- **Rejected alternatives:** Proposal 2 and the others, under Alternatives below. Claude adds decision D-024 to `docs/process/decision-log.md` with this plan.
- **Fresh-eyes check (D-023).** A sub-agent checked this plan against the code before Droid runs. Its 12 findings are folded in: self-contained extractors, jsdom limits, the Settings form, the token step's placement, the waiting-item lookup, replies beyond the budget, Home's counts, Vite's paths, the copy fallback, and small additions.

## Context

The facts from the research that shape the design. Line numbers are at main c4b7251; Droid re-checks them before editing.
- **No intake route.** No route accepts content from a client. Items are created only by `confirm` (`api/sources.py:147`) and `check_source` (`collection.py:136`).
- **One feed per source.** A source has a unique, non-null `feed_url` (`models.py:66`), and a kind: `feed`, `podcast`, or `youtube`.
- **Runs check every source.**
  - `run_digest` checks every source (`digest/runner.py:184`).
  - `run_detail` counts every source in `sources_total` (`runner.py:430`), and the run bar waits for that many checks (`frontend/src/pages/Home.tsx:65, 221`).
- **Pending selection.** `select_pending` summarizes a null-status item only on a `feed` source (`runner.py:45`). The source name comes from `Source.title`, at `runner.py:46` (summary and grouping) and in the snapshot query at `runner.py:317`.
- **The context pass.**
  - It reads only feed and podcast items (`context/gather.py:28`).
  - It filters links against `source.site_url` (`gather.py:36`).
  - It fetches `item.link` for author replies (`gather.py:119`).
  - It numbers the `A1` part after the link parts (`position + 1`).
- **The cross-site rule.** `cross_site_writes` refuses writes whose `Origin` does not match `Host`, or whose `Sec-Fetch-Site` is `cross-site` or `same-site`. An extension's own requests would therefore be refused without an exception.
- **The frontend:**
  - `SourceKind` is `'feed' | 'podcast' | 'youtube'` (`frontend/src/components/ui.tsx:43-46`).
  - Home's rail counts sources by kind (`Home.tsx:304-307`).
  - Settings has three numbered sections (`pages/Settings.tsx:128, 159, 177`).
- **Not in the image.** `.dockerignore` lists only `backend/` and `frontend/`, so a new `extension/` folder stays out of the image.
- **Chrome MV3** (external, research §10):
  - With `activeTab` and `scripting`, the extension can run a script in the current tab after a user gesture. Whether opening the popup grants `activeTab` is not stated, so it is verified live.
  - Extension pages with host permissions request other origins without CORS.
  - The `Origin` an extension sends is not documented, so it is verified live.

## Goals / Non-Goals

**Goals:**
- Follow the current site in one click.
- Save the page being read, including an X post with the author's replies, for the next digest.
- Keep the user's accounts safe: read only on a click, only the rendered page, and only from the user's own CatchUp.

**Non-Goals:**
- Firefox, Safari, and Chrome Web Store publishing.
- Following X accounts. The X API option is #41.
- Background reading, scheduled capture, or a "generate now" button.
- Reading other people's X replies (F8's "notable interactions").
- Images stored by CatchUp. They load from their sites, as in #49.

## Decisions

### D1. The extension package
- **A separate package** in a new folder `extension/`, with its own `package.json`, TypeScript, and Vite.
  - **Build output:** `extension/dist/`, a folder that can be loaded unpacked.
    - `manifest.json` lives in `extension/public/`, so Vite copies it to the root of `dist/`.
    - `popup.html` and `options.html` sit at the root of `extension/`, so they build to the root of `dist/`. Vite mirrors source paths, so `src/popup/index.html` would land at `dist/src/popup/index.html`.
    - A small build plugin emits `frontend/public/icon-192.png` as the PNG icon. Chrome does not use SVG for manifest icons.
    - A build check reads `dist/manifest.json`, and fails when a path it names is missing from `dist/`.
  - **Tests:** vitest with jsdom.
- **The manifest** (MV3):
  - `name` "CatchUp";
  - `permissions`: `activeTab`, `scripting`, and `storage`;
  - `host_permissions`: `http://127.0.0.1/*` and `http://localhost/*`. A match pattern without a port matches any port, so this covers :8000 and :8800;
  - `action.default_popup`, `options_ui`, and `icons`.

  There is no `content_scripts` key, no `background` service worker, and no `externally_connectable`. A test pins the permission lists exactly.
- **Why no service worker.** The popup is an extension page. It can run `chrome.scripting.executeScript` on the active tab, and can call CatchUp directly, without CORS, through its host permissions. A service worker would add a messaging layer, and lifetime limits, without any need.
- **Settings.** The server address (default `http://127.0.0.1:8000`) and the token are kept in `chrome.storage.local`. The options page accepts only `http://127.0.0.1:<port>` or `http://localhost:<port>`, because other addresses fall outside the host permissions.

### D2. Connection tokens (capabilities `browser-extension`, `user-interface`)
- **The token.** "cu_" followed by 32 random bytes, encoded base64url, created by `secrets.token_urlsafe`.
- **Storage.** A new table `extension_tokens`, with columns `id`, `name` (1–60 characters), `token_hash` (SHA-256 hex, unique), `created_at`, and `last_used_at` (nullable).
- **The routes:**
  - `POST /api/settings/extension-tokens` with `{name}` returns `{id, name, created_at, token}`. This is the only response that contains the token.
  - `GET /api/settings/extension-tokens` returns `[{id, name, created_at, last_used_at}]`.
  - `DELETE /api/settings/extension-tokens/{id}` returns 204.
- **Token routes are for CatchUp's own pages.** A request to them that carries a token gets 403 `cross_site_request`, so that a stolen token cannot create more tokens.

### D3. The exception in the cross-site rule (capability `model-settings`)
- **Where.** In `cross_site_writes`, **before** its check for write methods (`main.py:71`), so that it runs for every method, `GET` included. Replace the comment #59 left at `:74`. When a request has `Authorization: Bearer <token>`:
  1. **Look up the hash.** An unknown or disconnected token gets 401 `{"error": {"code": "invalid_token", "message": "This browser is not connected to CatchUp. Connect it in Settings."}}`, for any method.
  2. **A valid token on an extension route passes**, whatever its `Origin` and `Sec-Fetch-Site`. `last_used_at` is updated, and `request.state.extension_token_id` is set. The extension routes are:
     - `POST /api/sources/preview`;
     - `POST /api/sources`;
     - `POST`, `GET`, and `DELETE` under `/api/captures`;
     - `GET /api/extension/status`.
  3. **A valid token on any other route** gets 403 `cross_site_request`.
- **Requests without a Bearer token** behave exactly as in D-022. Other `Authorization` schemes, such as Basic auth added by a reverse proxy, pass through as if there were no header.
- **No blocking.** The token lookup and the `last_used_at` update are synchronous SQLite calls, so they run in `run_in_threadpool`. The `last_used_at` write is best-effort: an `OperationalError`, such as a lock held during a run, is logged and ignored.
- **Token routes with a token.** A request to `/api/settings/extension-tokens` that carries a valid token gets 403 `cross_site_request`, for every method, `GET` included (D2).
- **The capture and status routes require a token.** A dependency on those routes checks `request.state.extension_token_id`, and returns 401 `invalid_token` when it is missing. CatchUp's own pages do not call them.
- **Why the token, and not the `Origin`.** The extension's `Origin` is not documented, and any extension can send one. A web page cannot send `Authorization` cross-origin without a preflight, which fails, because the server answers no CORS preflight. So the token is what proves it is this extension.

### D4. Saved pages: data and migration `0006_captures` (capabilities `source-management`, `transcripts`)
- **The migration:**
  - the `extension_tokens` table (D2);
  - `items.site_name`: String(200), nullable;
  - `items.captured_replies`: JSON, nullable, a list of reply texts;
  - **downgrade:** delete sources of kind `capture` (their items cascade, because foreign keys are on during migrations, `db.py:26`), then drop the columns and the table, with `recreate="never"` as in `0005`. `0002_transcripts.py:47-48` explains why rebuilding `items` with foreign keys on is unsafe.
- **The built-in source.** Created on the first capture:
  - `kind` `capture`, `title` "Saved from browser";
  - `feed_url` and `input_url` set to the reserved value `catchup:captures`, and `site_url` empty.
- **One capture becomes one item:**
  - `identity_key`: the saved URL, normalized: scheme and host lowercased, the fragment removed;
  - `link`: the saved URL;
  - `title`: up to 300 characters;
  - `content_text`: the main text, up to 16,000 characters;
  - `content_origin`: `capture`;
  - `state`: `pending`;
  - `published_at`: an ISO time, or null when it cannot be parsed;
  - `entry_author`: up to 200 characters;
  - `site_name`;
  - `entry_links`: up to 50, http(s) only, each `{url, text}`;
  - `image_candidates`: up to 8, through the same URL filters as `_entry_images` (http(s) only, avatars, exact duplicates). The filter is moved into a shared helper in `sources/feeds.py`, and feed parsing keeps its behavior;
  - `captured_replies`: up to 10 replies and 4,000 characters in all, the same caps as author replies today (`context/comments.py:17-24`).
- **Saving the same address again:**
  - **Finding the waiting item.** The waiting item is the pending item in the captures source whose `identity_key` equals the key, or starts with the key followed by `#`. The `#` is matched literally, with `autoescape=True`. So after a delivery, the item added later, `url#t2`, is found and replaced, and there is never more than one waiting item per address.
  - **While an item is waiting:** its fields are replaced, and `summary`, `summary_language`, `summary_images`, `context_status`, and its context rows are cleared.
  - **While a run is active:** a save that would replace a waiting item gets 409 `run_active`, with the message "A digest is being made. Save this page again when it finishes." The run may already have chosen that item. A save of a new address is accepted, and waits for the next run.
  - **When no item is waiting:** a new item is added. Its `identity_key` is the key, unless an item with that key exists already, delivered; then it is `<key>#<capture time in ISO>`.
- **Two first captures at once.** Both may try to create the built-in source, and its unique `feed_url` makes the second fail. The `IntegrityError` is caught, and the source is looked up again.
- **A blank `site_name`** is treated as missing, and defaults to the URL's host.

### D5. The capture API (capability `browser-extension`)
- **`POST /api/captures`**, with a token. The body is `{url, title, site_name?, author?, published_at?, text, replies?: [string], links?: [{url, text}], images?: [{url, alt}]}`.
  - **Validation:**
    - `url` must be http(s);
    - `title` or `text` must be non-empty;
    - values over a cap are cut, not refused;
    - a bad body gets 422 `invalid_request`.
  - **The response:** 201 `{id, url, title, site_name, waiting}`, where `waiting` is the number of pending captures.
- **`GET /api/captures`**, with a token: the pending captures, newest first, as `{id, url, title, site_name, saved_at}`.
- **`DELETE /api/captures/{id}`**, with a token: 204 for a pending capture, or 404 for anything else.
- **`GET /api/extension/status`**, with a token: `{name, waiting}`.
- **`GET /api/sources`** adds `waiting_count` to the captures source's row.

### D6. Saved pages in the run (capabilities `content-collection`, `digest-generation`)
- **Checks.** `run_digest` leaves sources of kind `capture` out of the sources it checks (`runner.py:184`), and `run_detail` leaves them out of `sources_total` (`:430`).
- **Pending selection.** `select_pending` also summarizes a null-status item on a `capture` source (`runner.py:45`).
- **The site name.** When `item.site_name` is set, it replaces `Source.title`, at `runner.py:46` and in the snapshot query at `:317`. Grouping, the image alt fallback (#49), and `DigestItem.source_name` therefore show it. `DigestItem.source_kind` is `capture`.
- **The context pass** (`context/gather.py`):
  - **Which items:** it also admits pending `capture` items (`:28`).
  - **Links:** related links are filtered against the item's own origin (`scheme://host`), not `source.site_url` (`:36`).
  - **The same origin after redirects.** The `site_url` stored in the pass's plan (`:41`), and used again after redirects (`:97`), is also the item's origin for capture items.
  - **Author replies:** it never fetches `item.link` or a comment feed. When `item.captured_replies` is non-empty, it stores an `A1` part with those texts after the link parts, as it does for blogs. The title is "Author replies (n)", and the URL is `item.link`.
  - **Replies do not depend on the budget.** The pass stops its loop when the run's fetch budget is spent (`:71-73`). Capture items' `A1` parts need no fetch, so they are written for every pending capture item, even after the budget is spent.
  - **The status:** a capture item with an `A1` part and no links is `gathered`; today's branch at `:159-160` would set `none`. Clearing a cached summary works as today.
- **Prompts are unchanged.** Captured text is item content, which the prompt already treats as data.

### D7. The CatchUp frontend (capability `user-interface`)
- **The kind.** `SourceKind` gains `'capture'`; `kindNames.capture` is "Saved from browser"; and `KindIcon` gets an icon for it, chosen from the existing icon set or added in the same style.
- **Sources.** The captures row shows "N pages waiting" (from `waiting_count`) in place of the feed URL and check chip. Delete works as for other sources.
- **Home.**
  - The visible source counts (`Home.tsx:248, 265, 304-307`) leave out the `capture` source, so "3 sources" means feeds the run checks.
  - `noSources` (`:216`) still counts it, so that a user with only saved pages can still generate a digest.
  - The run result line (`:87`) leaves out "· 0 sources" when `sources_total` is 0.
- **Settings.** A fourth section, "Browser extension". It renders **after and outside** the model-settings `<form>` (`Settings.tsx:127-188`), with its own form, message, and error state, because `Button` sets no `type` and would otherwise submit the model form. The lede (`:126`) is updated for four sections. The section has:
  - a name field (default "Chrome") and "Connect a browser";
  - then the token once, in a read-only field with "Copy" and the note "Paste this into the CatchUp extension's options. It is shown only once." The field is `aria-describedby` the note, and the copy result is announced in a status region. When `navigator.clipboard` is missing or fails, as on a page that is not a secure context, the field is selected and "Copy failed. Select the token and copy it." is announced;
  - the list of connected browsers, with name, connected date, last used ("Never" when null), and "Disconnect".

### D8. The popup
- **States:**
  - **Not connected** (no token, or a 401 from `/api/extension/status`): the text "Connect this browser in CatchUp → Settings → Browser extension", and a link to the options page. No other request is sent.
  - **Connected:**
    - the tab's title and host;
    - the number of pages waiting;
    - "Follow this site", "Add this page to my next digest", and "Open CatchUp" (which opens the server address in a new tab).
- **Follow this site:**
  - It posts the tab URL to `/api/sources/preview`, and shows the title, kind, feed URL, follow-site notice, and up to 5 entries, with "Confirm" and "Cancel". "Confirm" posts `/api/sources`.
  - Error codes map to the Sources page's messages. The extension copies the mapping table, with a comment that names `frontend/src/pages/Sources.tsx` as the source.
  - On an `x.com` or `twitter.com` tab, it shows the "cannot be followed" message, and no request is sent.
- **Add this page:**
  1. `chrome.scripting.executeScript` runs the extractor (D9) in the tab. The page is unreadable when the call rejects (`chrome://`, the Web Store, `file:`, or a PDF viewer), or returns an empty array or no `result`. The popup then shows "This page can't be read by extensions."
     - On an X post, the popup runs the X extractor first. When it returns `null`, the popup runs the generic extractor in a second `executeScript` call.
  2. The popup checks the result's types and caps, then posts `/api/captures`.
  3. It shows "Saved. It will be in your next digest.", with "Remove", which calls `DELETE /api/captures/{id}`, and the new waiting count. "Add" is disabled while a save is in progress, and a 409 `run_active` shows its message.
- **Accessibility.** The popup uses buttons and a status region with `aria-live`, and passes an axe check in its tests.

### D9. Extractors (capability `browser-extension`)
- **How they run.** Each is a function run with `executeScript`. It returns plain data, and never calls the network.
- **Self-contained.** Chrome serializes the function it is given, so helpers, constants, and imports outside its body are lost in the tab. Each extractor is therefore one function, with every helper and cap inside its body. Its tests also run it after a round trip through `new Function('return (' + fn.toString() + ')()')`, against the fixture, so a dependency on module scope fails.
- **The page is never changed.** The extractors only read the DOM. A test checks that `document.body.outerHTML` is the same after extraction.
- **The generic extractor:**
  - **url:** `link[rel=canonical]`, then `og:url`, then `location.href`, keeping only http(s) values;
  - **title:** `og:title`, then `document.title`;
  - **site_name:** `og:site_name`, then the host;
  - **author:** `meta[name=author]`, then `article:author`;
  - **published_at:** `article:published_time`, then the first `time[datetime]` in the main root;
  - **The main root:** `article`, then `main`, then `[role=main]`, then `body`;
    - **its text** comes from a `TreeWalker` over the root's text nodes. It skips text inside `nav`, `aside`, `footer`, `script`, `style`, `noscript`, and `form`, and joins the text of block elements with line breaks and other text with spaces. Whitespace is collapsed, and the text is cut to 16,000 characters. `innerText` is not used, because jsdom does not implement it, and the page is not edited;
    - **its images** are `img` elements with an http(s) `currentSrc || src`, at most 8, with their `alt`;
    - its links are anchors with an http(s) `href`, at most 50, with their text.
- **The X extractor**, on `x.com` or `twitter.com` at `/<user>/status/<id>`, on `article[data-testid="tweet"]` elements:
  - **The post** is the first article whose status link matches the URL's id. From it:
    - the text from `[data-testid="tweetText"]`;
    - the author's name and `@handle` from `[data-testid="User-Name"]`;
    - the time from `time[datetime]`;
    - images from `[data-testid="tweetPhoto"] img`.
  - **Replies:** the following articles whose handle equals the post's handle. Their `tweetText`, in page order, become `replies`. Other articles are ignored.
  - **Links:** an anchor's `href`, unless it is on `t.co`. For a `t.co` link, the anchor's text is used when it is a full http(s) URL without a trailing "…". Otherwise the link is left out, because `t.co/robots.txt` disallows all agents.
  - **site_name:** "X · <name>"; **title:** "<name> on X".
  - **The fallback:** when no matching post article is found, the X extractor returns `null`, and the popup runs the generic extractor (D8).
- **Fixtures.** Both extractors are tested on invented HTML fixtures shaped like the real markup. Real pages are not copied.

### D10. Tests and CI
- **Backend** (pytest):
  - tokens and the D3 matrix;
  - captures validation and caps, replacement, and adding again after delivery;
  - the captures source in collection and runs, and `sources_total`;
  - the context pass for captures (`item.link` has `call_count == 0`; links use the item's origin; the `A1` from captured replies);
  - the end-to-end run;
  - the migration up and down.
- **Frontend** (vitest + axe): the Settings group, the Sources row, and the Home counts.
- **Extension** (vitest + jsdom):
  - the extractors on fixtures;
  - the popup logic, with a fake `chrome` API (`storage`, `tabs`, `scripting`) and a mocked `fetch`;
  - the API client's error mapping;
  - the manifest's permission lists.
- **CI.** A new `extension` job in `.github/workflows/ci.yml` runs `npm ci`, `npm test -- --run`, and `npm run build` in `extension/`.

### D11. Alternatives considered
- **Proposal 2: the extension as a logged-in collector for followed accounts.** On each run it would open followed pages in background tabs, scroll, and read new posts. Rejected:
  - X's automation rules list scripting the website among practices that may lead to suspension, and its terms prohibit scraping;
  - it needs host permissions for every followed site;
  - it depends on the browser being open, and is fragile.
- **The X API**, for following X accounts. A separate change (#41): pay-per-use, $0.005 per post read.
- **A side panel.** The user chose the popup.
- **A pairing code.** The user chose copying a token.
- **A background service worker.** Unnecessary (D1).
- **Firefox and Safari.** Later. Firefox needs `background.scripts` and signing; Safari needs an Xcode wrapper.
- **Recognizing the extension by its `Origin`.** Rejected (D3): the value is undocumented, and any extension can send it.

## Risks / Trade-offs

- **[X's terms]** They prohibit scraping "in any form". → The extension reads only on a click, only what is on screen, and never automates anything. The README states the risk.
- **[X's markup changes]** → Fixtures, the fallback to the generic extractor, and a manual check by the user.
- **[A leaked token]** → It is stored in `chrome.storage.local`, and allows only the extension routes. "Disconnect" revokes it.
- **[`activeTab` from the popup]** → Verified in the manual check. If the grant does not come from opening the popup, the button click is the gesture, because `executeScript` runs on that click.
- **[Long pages]** → The caps. The main-root heuristic can pick up boilerplate on some sites; the summary prompt already asks for the substance.
- **[A capture source in old code]** → On downgrade, migration `0006` deletes it, so that an older build does not try to fetch `catchup:captures`.

## Migration Plan

- **Migration `0006`** adds a table and nullable columns, so existing data is unaffected. Rollback: downgrade (D4).
- **Rollout:** the user loads the extension unpacked. The Docker image is unchanged, apart from the backend and frontend code.
- **Testing notes:**
  - automated tests (D10);
  - the Docker smoke script;
  - Claude's live check at review: load the unpacked build in the in-app browser if possible, otherwise test the API with the same headers; check the `Origin` the server sees; follow a blog; save a public article; run a digest with a stub model;
  - **the user's manual check on X**, in their own logged-in Chrome, because Claude does not sign in to X: save a post with the author's replies, run a digest, and check that only the author's replies appear.

## Open Questions

None that block implementation. Publishing to the Chrome Web Store, Firefox, and Safari are later decisions.
