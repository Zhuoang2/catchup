# Design

## Context

See `proposal.md` (Why) and `research.md` for the facts. The facts that shape the design:

- **Source kinds.** `sources.kind` is free text (`backend/src/catchup/models.py:87`). Every source except `capture` and `x` goes through `check_source` on each run (`digest/runner.py:263-265,303-310`). Only a `feed` source is ever reclassified (`collection.py:96-97`).
- **X is the precedent for recognizing a host before discovery.**
  - `x_username` runs before `discover` (`sources/x_accounts.py:28-41`, `api/sources.py:165-169`).
  - The source is saved under a stable address `x:user:<id>` (`api/sources.py:86`).
  - `is_x_host` (`net/x_hosts.py:4-7`) refuses X hosts in `safe_fetch` before DNS (`net/safe_fetch.py:91-92`), and in the related-link filter (`context/links.py:38`).
- **Podcasts are the precedent for transcripts that arrive later.** A pending episode is resolved again on each check while it waits (`collection.py:104-133`).
- **YouTube is the precedent for the caption wait.**
  - `select_pending` expires `caption_wait` after `caption_wait_hours` (default 24) into a Creator-updates reason (`runner.py:58-62`).
  - The reasons are `CREATOR_REASONS` (`runner.py:38`).
- **The private-address rule.**
  - `safe_fetch` checks every hop before the request (`_check_address`, `safe_fetch.py:82-94,165`).
  - It checks again when the connection is opened (`_PublicOnlyBackend.connect_tcp`, `:114-125`).
  - Tests mock DNS through `socket.getaddrinfo`, and connections through `socket.create_connection` (`tests/test_safe_fetch.py:46-60,263-273`).
  - `tests/conftest.py:8-21` blocks the network in every test.
- **What RSSHub returns.** These facts come from reading RSSHub's source at `lib/routes/bilibili/video.ts`, `cache.ts` and `lib/views/json.ts`, on 2026-11-22.
  - The route `/bilibili/user/video/:uid/:embed?` answers `?format=json` with JSON Feed 1.1 (`version: "https://jsonfeed.org/version/1.1"`).
  - The feed title is `<name> 的 bilibili 空间`, and `home_page_url` is `https://space.bilibili.com/<uid>`.
  - Each item has:
    - `id` (the video link), `url` `https://www.bilibili.com/video/<BV id>` (or `av<aid>` for old videos), `title`, `content_html` (an embedded player, the cover and the description), `date_published`, and `authors`;
    - `attachments`: first the video page (`mime_type: "text/html"`), then one per subtitle track: `{url: "data:text/plain;charset=utf-8,<percent-encoded SRT>", mime_type: "text/srt", title: "字幕 - <language>"}`.
  - Subtitles are attached only for JSON Feed, only when `BILIBILI_EXCLUDE_SUBTITLES` is not set, and never on Cloudflare Workers.
- **Converting the text.** `convert_transcript(body, "text/srt")` already reads SRT. `text/srt` is not one of its declared types, so it detects SRT from the text (`transcripts/convert.py:73-106`). It MUST NOT be given the data URL's own type `text/plain`, which keeps the timing lines.
- **The browser extension needs no extractor.** Its "Follow this site" already calls `/api/sources/preview` with the tab's address (`extension/src/popup.ts:262-290`).

## Goals / Non-Goals

**Goals:**
- Follow an uploader with the same preview, confirm, check, wait and Creator-updates flow as YouTube channels and podcasts, reusing their code paths.
- Make "CatchUp never requests a Bilibili host" a property of `safe_fetch`, not of each caller.
- Keep the private-address exception as narrow as one origin, for one kind of request, on the first hop only.

**Non-Goals:**
- Any request from CatchUp to Bilibili: signing, cookies, a headless browser, robots.txt.
- Settings fields for RSSHub or Bilibili. The opt-in is the operator's environment setting, and `api/settings.py` and `Settings.tsx` stay unchanged.
- Other RSSHub routes (collections, dynamics, live), RSSHub access keys, and choosing among subtitle tracks.
- Changing how a Bilibili feed from another generator, added as a plain website feed, is summarized. It is still a website feed. It only loses the ability to fetch Bilibili pages.
- A data migration. No column or table is added.

## Decisions

### D1. Read uploaders through a user-run RSSHub (Proposal 1)

The user chose this on 2026-11-22.

- **Alternative considered: Proposal 2, a native kind that calls Bilibili's web API.** It was rejected for four reasons:
  - CatchUp would itself make the automated requests that the user agreement's section 5.6(3) forbids.
  - The public repository would carry WBI signing and visitor-cookie code, the material Bilibili's lawyers acted against in January 2026.
  - Subtitles would need the user's session cookie stored in CatchUp, against `docs/handoff.md` §4.
  - Plain requests already meet HTTP 412 challenges.
- **Alternative considered: close #40 with a README note only.** It was not chosen.

The terms risk remains with the user's RSSHub (D-038). The README states it, and so does the preview.

### D2. One host rule, used everywhere

- **The rule.** A new `backend/src/catchup/net/bilibili_hosts.py` has `is_bilibili_host(host)`. It covers `bilibili.com`, `b23.tv`, `hdslb.com` and `bilivideo.com`, with any subdomain, ignoring case and a trailing dot, like `is_x_host`.
- **`safe_fetch`.** `_check_address` raises `FetchError("blocked_address", "Bilibili pages are never requested; uploaders are read through RSSHub.")` before DNS. This covers every caller and every redirect hop.
- **Related links.** `related_links` skips links to these hosts (`context/links.py:38`). The context pass then never plans a fetch it cannot make.

### D3. The RSSHub address

- **The setting.** `Settings.rsshub_url: str | None = None`, read from `CATCHUP_RSSHUB_URL` in `config.py`.
- **Validation.** A new `validate_rsshub_url` returns the URL without a trailing `/`, or `None` when the value is empty. It raises `ValueError("CATCHUP_RSSHUB_URL must be an HTTP or HTTPS address without a user name, query, or fragment.")` when the value is not one.
- **No Settings field.** Only the operator can then point CatchUp at a private address. This is the reason the address is an environment setting.

### D4. The private-address exception in `safe_fetch`

- **The parameter.** `safe_fetch` gets `private_origin: str | None = None`. Origins are compared after normalizing: lower-case scheme and host, and an explicit default port (80 for HTTP, 443 for HTTPS).
- **The rule.** Only on the first hop, and only when the URL's origin equals `private_origin`, `_check_address` skips `_public_answers`. The Bilibili and X host rules still apply.
- **At connect time.** `_client(private=(host, port))` builds `_PublicOnlyBackend` with that one host and port. For exactly that pair, its `connect_tcp` still resolves the host and connects to each answer's address in order, as it does for public hosts, but skips the public-address test. Resolution errors keep their current message. It does so only while the first hop is in flight, because a redirect hop is checked before any connection (`safe_fetch.py:165`).
- **Who passes it.** Only `sources/bilibili.py` passes `private_origin`. Discovery, collection, context, transcripts and captions never do.

### D5. Reading an uploader

New module `backend/src/catchup/sources/bilibili.py`:

- **`uploader_mid(url, rsshub_url) -> str | None`.**
  - It returns the mid for the forms in the spec.
  - It returns `None` when the host is neither a Bilibili host nor the configured RSSHub origin.
  - It raises `AppError("not_a_bilibili_uploader", "Paste the uploader's space address, such as https://space.bilibili.com/2267573.", 422)` for any other Bilibili address.
  - A path on the RSSHub origin that is not `/bilibili/user/video/<mid>` returns `None`. Discovery then refuses it as a private address, or reads it as a feed when RSSHub is public.
  - It never makes a request.
- **`fetch_uploader(mid, settings, *, spacer=None) -> FetchResponse`.**
  - Without `settings.rsshub_url`, it raises `FetchError("rsshub_not_configured", NOT_CONFIGURED_MESSAGE)`.
  - Otherwise it calls `safe_fetch(f"{rsshub_url}/bilibili/user/video/{mid}?format=json", private_origin=<origin of rsshub_url>, max_bytes=settings.max_feed_bytes, spacer=spacer)`.
  - A `FetchError` with code `fetch_failed` becomes `FetchError("rsshub_failed", "RSSHub could not read this uploader (HTTP <n>).", <n>)`, or `"RSSHub could not read this uploader."` without a status. Other codes, such as `blocked_address` and `rate_limited`, pass through.
- **`parse_uploader_feed(response, mid) -> Feed`.**
  - It needs a JSON object whose `version` starts with `https://jsonfeed.org/version/` and whose `items` is a list. Otherwise it raises `FeedParseError("RSSHub could not read this uploader.")`.
  - It returns `Feed(feed_url=f"bilibili:uploader:{mid}", site_url=f"https://space.bilibili.com/{mid}", title=<title>, entries=…, source_kind="bilibili")`.
  - The title is the feed title without the ending ` 的 bilibili 空间`, else the first item author's name, else `Bilibili uploader <mid>`.
- **Each entry.**
  - `identity_key` is `bilibili:video:<id>`, where `<id>` is the `BV…` or `av…` segment of the item's `url`. An item without one is skipped.
  - `link` is the item's `url`. `title` goes through `_entry_title`.
  - `published_at` comes from `date_published`, or `None` when it cannot be parsed.
  - `content_text` is `plain_text(content_html)`.
  - `transcript_text` is `convert_transcript(<decoded bytes>, "text/srt")` of the first attachment whose `mime_type` is `text/srt` and whose `url` starts with `data:`. The data is percent-decoded, or base64-decoded when the media part ends in `;base64`.
  - It has no links, images, comment pointers or audio.
- **Two new fields with defaults,** so every existing caller is unchanged: `FeedEntry.transcript_text: str | None = None`, and `Feed.source_kind: str | None = None`. `Feed.kind` returns `source_kind` when it is set.

### D6. Preview and confirm (`api/sources.py`)

- **Order.** `preview` calls `uploader_mid` first, then `x_username`, then `discover`.
- **`_bilibili_preview`.**
  - It fetches and parses the uploader, and checks for a duplicate by `bilibili:uploader:<mid>`.
  - It caches the response in `feed_cache` under that address, with `dataclasses.replace(response, url=feed_url)`.
  - It returns the same shape as the X preview, with `kind: "bilibili"`, `follows_site_feed_notice: false`, and `captions_enabled: false`.
- **Errors.**
  - `FetchError` goes through `_fetch_error`, so the code is `rsshub_not_configured`, `rsshub_failed`, `blocked_address`, or `rate_limited`.
  - `FeedParseError` becomes `AppError("rsshub_failed", "RSSHub could not read this uploader.", 422)`.
- **Confirm.**
  - A `feed_url` matching `bilibili:uploader:[0-9]{1,20}` takes the cached response, or fetches again, then goes through the existing confirm loop with the parsed `Feed`.
  - In the loop, a `bilibili` entry gets `transcript_status = "found"`, `content_text = entry.transcript_text` and `content_origin = "transcript"` when it has subtitles.
  - Otherwise it gets `transcript_status = "subtitle_wait"` and the feed text with `content_origin = "feed"`. That text is never summarized.
  - `article_text` is never called for it. `image_candidates` and `entry_links` are empty.
  - Any other `bilibili:` value is refused as `not_a_bilibili_uploader`.

### D7. Checks and the wait

- **`check_source`** (`collection.py:76`). For a `bilibili` source, it uses `fetch_uploader` and `parse_uploader_feed` in place of `safe_fetch` and `parse_feed`. The mid is taken from `feed_url`. The response stays bound before parsing, as the failure branch needs (`collection.py:87`).
- **New entries** are recorded as in D6.
- **Waiting items.** Like the podcast branch (`collection.py:104-133`), a pending item of the source in `subtitle_wait` is updated when its entry now has `transcript_text`. Its status becomes `found`, its content the subtitles, and its summary is cleared.
- **`select_pending`.** `subtitle_wait` joins the caption-wait branch. It waits `caption_wait_hours` from `discovered_at`, then expires to `no_subtitles`, which joins `CREATOR_REASONS`.
- **What does not change.**
  - The caption pass selects only `youtube` sources (`runner.py:74`), so it ignores Bilibili.
  - The context pass admits only `feed`, `podcast`, `capture` and `x` (`context/gather.py:115`), so Bilibili items get no linked pages without any change.

### D8. Frontend and extension

- **`components/ui.tsx`.**
  - `SourceKind` gains `'bilibili'`, with the name "Bilibili uploader".
  - `Reason` gains `'no_subtitles'`, with the text "No subtitles from RSSHub".
- **`components/Icon.tsx`.** It gains a `bilibili` shape: a generic screen with a play mark, not Bilibili's logo.
- **`pages/Sources.tsx`.**
  - The preview method line for `bilibili` reads "Subtitles read through your RSSHub; videos without subtitles are listed without summaries".
  - A risk line says that Bilibili's user agreement does not allow automated access, and that your RSSHub makes those requests.
  - The preview shows no Feed row for `bilibili`.
  - A row shows `site_url` for `bilibili`, as it does for `x`.
  - The rail gains "Bilibili uploaders — through an RSSHub you run".
- **`pages/Home.tsx`.** The source counts add "· N Bilibili uploader(s)" only when N > 0.
- **`extension/src/popup.ts`.** `kindLabels` gains `bilibili: 'Bilibili uploader'`. The preview shows `site_url` in place of `feed_url` for `bilibili`.

### D9. Deployment and README

- **The override file.** A new `compose.rsshub.yaml`, with exactly this content:

  ```yaml
  services:
    catchup:
      environment:
        CATCHUP_RSSHUB_URL: http://rsshub:1200
    rsshub:
      image: diygod/rsshub:latest
      env_file:
        - path: .env.rsshub
          required: false
      restart: unless-stopped
  ```

- **The image.** `diygod/rsshub:latest`, from Docker Hub. On 2026-11-22 its compressed size was 129,744,697 bytes (amd64) and 133,125,571 bytes (arm64). `diygod/rsshub:chromium-bundled`, which adds the browser fallback, was 506,763,465 bytes (amd64) and 390,997,025 bytes (arm64). The README names both.
- **Keeping `.env.rsshub` local.** `.gitignore` already ignores it (`.env.*`, `.gitignore:10`), and `.dockerignore` is an allow-list.
- **`.env.example`** gains `# CATCHUP_RSSHUB_URL=http://rsshub:1200`.
- **README.**
  - A `## Bilibili uploaders` section after `## X accounts`, with what the spec's "State Bilibili's terms" requirement lists, and one line in `## Supported sources`.
  - Start commands use `docker compose up -d --wait`, or `--build --wait` for source builds, as `tests/test_install_docs.py:239-249` requires.
  - The section tells the user to edit the existing `COMPOSE_FILE` line in `.env`, not to add a second one. For a source build the value is `compose.yaml:compose.build.yaml:compose.rsshub.yaml`.

## Decisions for the user (at plan approval)

`tasks.md` follows the recommended option of each. The user chose the recommendation for U1–U7 on 2026-11-22.

- **U1. How RSSHub is started.**
  - Recommended: the optional `compose.rsshub.yaml` override (D9). It sets up the network and `CATCHUP_RSSHUB_URL` for the user, and leaves `compose.yaml` unchanged.
  - Alternative: the README only, with a `docker run` example. That needs host networking (`host.docker.internal`), which differs between macOS and Linux.
- **U2. Public RSSHub instances.**
  - Recommended: allowed, since any address the operator sets is accepted. The README recommends running your own, and warns that a public instance receives the uploader ids, publishes no terms, and may not return subtitles (it may run on Cloudflare Workers).
  - Alternative: refuse public addresses. CatchUp cannot tell the user's own server on a public host from a shared instance, so this would block legitimate setups.
- **U3. Subtitles in this change.**
  - Recommended: yes. CatchUp reads RSSHub's subtitle attachments (D5).
    - The README explains that RSSHub returns them only with the user's own logged-in cookie (`BILIBILI_COOKIE_<uid>` in `.env.rsshub`), and the risk to that account.
    - CatchUp never asks for or stores the cookie.
  - Alternative: no subtitle reading. Every video then goes to Creator updates, and the feature only lists titles.
- **U4. The new reason and the wait.**
  - Recommended: the reason `no_subtitles`, shown as "No subtitles from RSSHub". The wait reuses `CATCHUP_CAPTION_WAIT_HOURS` (24 hours), because Bilibili's automatic subtitles can appear after upload, like YouTube's captions.
  - Alternative: a separate wait setting. That is one more setting with no evidence it needs a different value.
- **U5. Pasting the RSSHub route address.**
  - Recommended: accept `<CATCHUP_RSSHUB_URL>/bilibili/user/video/<mid>` as that uploader. Otherwise discovery refuses it as a private address, with a confusing message.
  - Alternative: accept space addresses only.
- **U6. A Settings group for Bilibili.**
  - Recommended: none. The setting lives in the environment, the preview states the risk where the user acts, and `Settings.tsx` and `api/settings.py` stay untouched (#12 changes both).
  - Alternative: a read-only "Bilibili" group showing whether RSSHub is set, and the risk note.
- **U7. Images.**
  - Recommended: no image candidates for Bilibili videos. A digest then never makes the reader's browser load Bilibili's image servers, and the cover image adds little to a subtitle summary.
  - Alternative: the cover image as a candidate.

## Risks / Trade-offs

- **[The terms risk moves to the user's RSSHub; it does not go away]** → The README and the preview say so. D-038 records it. CatchUp's own traffic never reaches Bilibili, and tests pin that.
- **[RSSHub's browser fallback can be slower than `safe_fetch`'s 30 s deadline]** → The check fails with a timeout. The next run usually gets RSSHub's cached answer. The README suggests the `chromium-bundled` image only when lists fail.
- **[A wrong or hostile `CATCHUP_RSSHUB_URL` can read a private service]**
  - Only the operator can set it.
  - The exception covers one origin, the first hop, and only uploader requests.
  - The answer must parse as JSON Feed, and only titles, links, dates, plain description text and subtitle text are kept.
- **[Blocking Bilibili hosts changes other sources]** → A website feed whose short entry links to a Bilibili page now keeps its feed text instead of reading that page. This is intended: the spec forbids requesting Bilibili for any source.
- **[RSSHub changes its output]** → The parser needs only JSON Feed's standard fields, plus the `text/srt` `data:` attachments. Changes to the attachment format show as videos waiting, then "no subtitles from RSSHub", not as failures.
- **[Several subtitle tracks]** → The first is used, in RSSHub's order, which follows Bilibili's list. Choosing a language is out of scope.
- **[The merge with #12]** → Neither change adds a migration that the other needs. Both touch `README.md`, `digest/runner.py`, and the three process logs. #12 changes `Settings.tsx` and `api/settings.py`, which this change does not touch.

## Testing

Test-first (D-016). The seams are named in `tasks.md`. All tests are offline:
- RSSHub is a respx route at `http://rsshub.test:1200`, which resolves to `10.0.0.7` through a patched `socket.getaddrinfo`;
- the JSON Feed fixtures are invented, under `backend/tests/fixtures/rsshub-*.json`;
- every Bilibili host has a respx route whose side effect is `AssertionError`.

Named mutations:

| Mutation | Change | Expected failing test |
| --- | --- | --- |
| H1 | `is_bilibili_host` without subdomains | `test_bilibili_hosts_are_refused_before_dns[www.bilibili.com]` |
| H2 | `_check_address` without the Bilibili rule | `test_bilibili_hosts_are_refused_before_dns`, `test_redirect_to_bilibili_is_refused` |
| H3 | `related_links` without the Bilibili rule | `test_related_links_skip_bilibili_hosts` |
| E1 | the exception applied to redirect hops | `test_private_origin_does_not_follow_redirects` |
| E2 | origins compared without the port | `test_private_origin_is_exact[other-port]` |
| E3 | connect-time check skipped for every host | `test_private_origin_connect_check_is_exact` |
| R1 | the `m.bilibili.com/space/<mid>` form removed | `test_uploader_addresses[mobile]` |
| R2 | video pages accepted as uploaders | `test_other_bilibili_addresses_are_refused[video]` |
| P1 | the first `text/srt` attachment read with its `data:` type `text/plain` | `test_subtitles_from_data_attachment` |
| P2 | `https:` attachments read as subtitles | `test_web_attachments_are_never_requested` |
| P3 | the title suffix kept | `test_uploader_title` |
| C1 | waiting items not re-resolved | `test_subtitles_that_appear_later_are_used` |
| C2 | `subtitle_wait` never expires | `test_subtitle_wait_ends_in_creator_updates` |
| C3 | Bilibili entries get `article_text` | `test_bilibili_entries_never_request_their_video_page` |
| U1 | the row shows `feed_url` for `bilibili` | `shows a Bilibili uploader by its space address` |
| X1 | the popup shows `feed_url` for `bilibili` | `labels a bilibili preview as Bilibili uploader and shows its space address` |

## Migration Plan

- No database migration and no new dependency.
- An instance without `CATCHUP_RSSHUB_URL` behaves as before, except that it never fetches Bilibili pages for any source.
- Rollback: reverting the change leaves saved `bilibili` sources in the database. Older code checks them with `safe_fetch("bilibili:uploader:…")`, which fails as an invalid URL. Deleting them in Sources removes them.

## Live check at review (needs the user's approval, asked separately)

Claude runs it on a fresh volume and a port other than 8800, after Droid has finished:
1. **Download the image.** Pull `diygod/rsshub:latest` (about 130 MB compressed).
2. **Start both services** with `compose.rsshub.yaml`.
3. **Follow one public uploader** in the browser. Its RSSHub then requests Bilibili from this machine, which is the terms risk described above. No Bilibili cookie is used, so every video should wait for subtitles.
4. **Run a digest with a stub model,** and check:
   - the preview, the Sources row, Home, and the extension popup on the uploader's space page;
   - that the run reports the uploader's videos as waiting for subtitles.

   That no request goes to a Bilibili host, and the Creator-updates reason after the wait, are pinned by the offline tests.
