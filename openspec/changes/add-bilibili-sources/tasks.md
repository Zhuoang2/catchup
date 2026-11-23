# Tasks

Implementer notes:
- **Read first.** Read `proposal.md`, all of `design.md` (Context, D1–D9, Decisions for the user, Risks, Testing), and every spec delta under `specs/`. If something looks wrong or contradictory, stop and report instead of redesigning.
- **Work test-first with the `tdd` skill** (D-016). In each group, first write the group's tests, run them, and watch each fail for the reason the task gives. Then change the code. The seams are named in each task, and they count as agreed. They are:
  - `socket.getaddrinfo` and `socket.create_connection`, replaced with `monkeypatch`. `tests/conftest.py` blocks the network in every test, so every test that fetches must set DNS;
  - respx routes, with `respx.mock(assert_all_mocked=True, assert_all_called=False)` in every test that has a route that must stay uncalled (each Bilibili route, and the redirect targets in group 1), and `respx.mock(assert_all_mocked=True)` elsewhere. With the default `assert_all_called=True`, a route that is never called fails the test when the `with` block ends ("RESPX: some routes were not called!");
  - the `resolve` and `failed_connections` fixtures in `backend/tests/test_safe_fetch.py`;
  - from `backend/tests/test_digest_runner.py`: `environment`, `seed`, `execute`, and `FakeModel`;
  - the `ready` fixture and `add_item` pattern of `backend/tests/test_creator_updates.py`;
  - `catchup.api.sources.utc_now`, replaced with `monkeypatch`;
  - in the frontend, the `fetchMock` and `respond` helpers of each test file;
  - in the extension, `connect`, `fetchMock`, `response`, and `initPopup` in `extension/src/test/popup.test.ts`.
- **Fixtures are invented.** Never copy a real Bilibili page, feed, or subtitle.
  - Write `backend/tests/fixtures/rsshub-uploader.json` as described in task 2.1.
  - The uploader id in every test is `2267573`, and the RSSHub address is `http://rsshub.test:1200`, resolving to `10.0.0.7`.
- **Test rules:**
  - **No real network.** No test may request a Bilibili host. Wherever a test serves RSSHub, also add a respx route for `re.compile(r"https?://([^/]*\.)?(bilibili\.com|b23\.tv|hdslb\.com|bilivideo\.com)(:\d+)?/.*")` whose side effect raises `AssertionError("Bilibili must never be requested")`, and assert that its `call_count` is 0.
  - **Change no existing test.** Add new tests to existing files where a task says so.
- **Mutations.** For each named mutation, apply it alone, run the named tests, record the result, and restore the code exactly by editing it back. Confirm the restore with `git diff`.
- **Environment:**
  - **Backend.** Run `uv run --offline pytest …` in `backend/`. Do not add or upgrade packages.
  - **Frontend and extension.** Use Node 22.17.1 with `export PATH="$HOME/.nvm/versions/node/v22.17.1/bin:$PATH"`. Then run `npm ci --offline --no-audit --no-fund` in `frontend/` and in `extension/`. It installs the locked packages from the local npm cache. If it fails, stop and report. Do not change `package.json` or `package-lock.json`.
- **Do not run** `docker build`, `docker compose`, `scripts/docker-smoke.sh`, any `docker pull`, or any Docker prune command. Do not touch port 8800. Claude Code runs Docker and the live check at review.
- **Out of scope:**
  - `api/settings.py` and `frontend/src/pages/Settings.tsx`;
  - `models.py` and migrations;
  - the context pass (`context/gather.py`) and the caption pass;
  - `sources/discovery.py`;
  - the extension's extractors;
  - other RSSHub routes and RSSHub access keys.
- **Do not edit:**
  - `proposal.md`, `design.md`, or the spec deltas;
  - `docs/process/decision-log.md` or `docs/process/requirements-changes.md`. Claude Code wrote D-038 and the requirements row with the plan.
- **OpenSpec.** Prefix every OpenSpec CLI call with `DO_NOT_TRACK=1`.
- **Commits.** Commit after each task group. Do not push, tag, or open a PR.

## 1. The Bilibili host rule, the RSSHub address, and its private-address exception (D2–D4)

- [x] 1.1 Write these tests and watch them fail. The `safe_fetch` tests fail on the missing `private_origin` argument or on the missing host rule, and `test_lookalike_hosts_are_not_bilibili` on the missing module `catchup.net.bilibili_hosts`; import `is_bilibili_host` inside that test, so the rest of `test_safe_fetch.py` still collects. The link test fails on the kept links, and the config tests on the missing `rsshub_url` field.

  **In `backend/tests/test_safe_fetch.py`** (new tests only):
  - **`test_bilibili_hosts_are_refused_before_dns`,** parametrized over:
    - `https://www.bilibili.com/video/BV1xx411c7mD`;
    - `https://space.bilibili.com/2267573`;
    - `https://b23.tv/abc123`;
    - `https://i0.hdslb.com/bfs/cover.jpg`;
    - `https://upos-sz.bilivideo.com/video.mp4`;
    - `https://BILIBILI.COM./video/x`.

    Each raises `FetchError` with code `blocked_address` and the message "Bilibili pages are never requested; uploaders are read through RSSHub.". A `socket.getaddrinfo` stub that records host names records none.
  - **`test_lookalike_hosts_are_not_bilibili`.** `is_bilibili_host` is false for `notbilibili.com`, `bilibili.com.example`, `b23.tv.example` and `None`. It is true for `bilibili.com`, `www.bilibili.com.` and `B23.TV`.
  - **`test_redirect_to_bilibili_is_refused`** (the `resolve` fixture). `PUBLIC` answers 301 to `https://www.bilibili.com/video/BV1xx411c7mD`. The fetch raises `blocked_address`, and a respx route for that page has `call_count == 0`.
  - **`test_private_origin_allows_only_that_origin`.**
    - DNS maps `rsshub.test` to `10.0.0.7`.
    - `safe_fetch("http://rsshub.test:1200/bilibili/user/video/2267573?format=json", private_origin="http://rsshub.test:1200")` returns the respx route's 200 body.
    - The same URL without `private_origin` raises `blocked_address`.
  - **`test_private_origin_is_exact`,** parametrized with ids. DNS maps `rsshub.test` and `other.test` to `10.0.0.7`, and `private_origin` is `http://rsshub.test:1200` unless the case says otherwise.
    - `other-port`: `http://rsshub.test:1201/x` raises `blocked_address`.
    - `other-host`: `http://other.test:1200/x` raises `blocked_address`.
    - `other-scheme`: `https://rsshub.test:1200/x` raises `blocked_address`.
    - `default-port`: with `private_origin="http://rsshub.test"`, `http://RSSHUB.test:80/x` is fetched (200).
  - **`test_private_origin_does_not_follow_redirects`** (the `resolve` fixture), parametrized over two redirect targets from `http://rsshub.test:1200/a`. DNS maps `rsshub.test` to `10.0.0.7`, and also `10.0.0.5` to `10.0.0.5`: the `resolve` fixture returns no answer for a name it does not list, even an IP literal, and an empty answer gives `fetch_failed` ("The source host could not be resolved."), not `blocked_address`.
    - `http://rsshub.test:1200/b`, the same origin;
    - `http://10.0.0.5/feed`.

    Each raises `blocked_address`, and a respx route for the target has `call_count == 0`.
  - **`test_private_origin_connect_check_is_exact`** (the `failed_connections` fixture, no respx):
    - (a) DNS maps `rsshub.test` to `10.0.0.7`. `safe_fetch("http://rsshub.test:1200/x", private_origin="http://rsshub.test:1200")` raises `fetch_failed`, and `failed_connections == [("10.0.0.7", 1200)]`: the connection was tried, to the resolved address, as for public hosts.
    - (b) With the same `private_origin`, `public.example` first resolves to `8.8.8.8` and then to `127.0.0.1`, as in `test_connection_rejects_dns_rebinding`. `safe_fetch("http://public.example/feed", private_origin="http://rsshub.test:1200")` raises `blocked_address`, and `failed_connections == []`.

  **In `backend/tests/test_context_links.py`:**
  - **`test_related_links_skip_bilibili_hosts`.** For the links `https://www.bilibili.com/video/BV1xx411c7mD`, `https://b23.tv/abc123`, `https://space.bilibili.com/2267573`, `https://i0.hdslb.com/a.png` and `https://example.com/a`, `related_links(ITEM, SITE, links, 8)` returns only the `example.com` link.

  **In `backend/tests/test_config.py`:**
  - **`test_rsshub_address_is_normalized`,** parametrized over `CATCHUP_RSSHUB_URL` values and the expected `Settings.from_env().rsshub_url`:
    - unset → `None`;
    - `""` → `None`;
    - `"http://rsshub:1200"` → the same;
    - `"http://rsshub:1200/"` → `"http://rsshub:1200"`;
    - `"https://rss.example/hub/"` → `"https://rss.example/hub"`.
  - **`test_rsshub_address_rejects_invalid_values`,** parametrized over `ftp://rsshub:1200`, `rsshub:1200`, `http://`, `http://user:pw@rsshub:1200`, `http://rsshub:1200/?key=1` and `http://rsshub:1200/#top`. `Settings.from_env()` raises `ValueError` whose message contains `CATCHUP_RSSHUB_URL`.
- [x] 1.2 Make them pass:
  - add `backend/src/catchup/net/bilibili_hosts.py` with `is_bilibili_host`, as D2 says;
  - use it in `_check_address` (`net/safe_fetch.py`), before DNS and after the X rule, and in `related_links` (`context/links.py`);
  - add `private_origin` to `safe_fetch`, `_check_address` and `_client`/`_PublicOnlyBackend`, as D4 says;
  - add `rsshub_url` and `validate_rsshub_url` to `config.py`, as D3 says.

  Then run, and watch pass:
  - `uv run --offline pytest tests/test_safe_fetch.py tests/test_context_links.py tests/test_config.py`;
  - the full `uv run --offline pytest`.
- [x] 1.3 Run these mutations one at a time:

  | Mutation | Change | Expected failing test |
  | --- | --- | --- |
  | H1 | `is_bilibili_host` matches only the bare domains, not subdomains | `test_bilibili_hosts_are_refused_before_dns` (the `www.`, `space.`, `i0.` and `upos-sz.` cases) |
  | H2 | the Bilibili rule removed from `_check_address` | `test_bilibili_hosts_are_refused_before_dns`, `test_redirect_to_bilibili_is_refused` |
  | H3 | the Bilibili rule removed from `related_links` | `test_related_links_skip_bilibili_hosts` |
  | E1 | the exception applied on every hop, not only the first | `test_private_origin_does_not_follow_redirects` (the same-origin case) |
  | E2 | origins compared by scheme and host only, without the port | `test_private_origin_is_exact[other-port]` |
  | E3 | the connect-time check skipped for every host whenever `private_origin` is given | `test_private_origin_connect_check_is_exact` (case b) |

## 2. Reading an uploader from RSSHub (D5)

- [x] 2.1 Write the fixture and these tests, and watch them fail at import: `catchup.sources.bilibili` does not exist.

  **The fixture `backend/tests/fixtures/rsshub-uploader.json`** is a JSON Feed with:
  - `version` `https://jsonfeed.org/version/1.1`, `title` `Sample Uploader 的 bilibili 空间`, and `home_page_url` `https://space.bilibili.com/2267573`.
  - Four items, in this order:
    1. **A video with subtitles.**
       - `url` and `id` are `https://www.bilibili.com/video/BV1aa411c7aA`, the `title` is `Video with subtitles`, and `date_published` is `2026-11-21T10:00:00.000Z`.
       - `content_html` is `<iframe src="https://player.bilibili.com/player.html?bvid=BV1aa411c7aA"></iframe><img src="https://i0.hdslb.com/cover-a.jpg"><br>Description A`.
       - `authors` is `[{"name": "Sample Uploader"}]`.
       - It has three `attachments`:
         - `{"url": "https://www.bilibili.com/blackboard/html5player.html?bvid=BV1aa411c7aA", "mime_type": "text/html"}`;
         - `{"url": "data:text/plain;charset=utf-8," + quote(SRT_A, safe=""), "mime_type": "text/srt", "title": "字幕 - 中文"}`, where `SRT_A` is `"1\n00:00:01,000 --> 00:00:04,000\nHello\n\n2\n00:00:04,000 --> 00:00:06,000\nworld\n"`;
         - a second `text/srt` `data:` attachment whose text says `Second track`.
    2. **A video without subtitles.** `url` `https://www.bilibili.com/video/BV1bb411c7bB`, `title` `Video without subtitles`, `content_html` `Description B`, `date_published` `2026-11-20T10:00:00.000Z`. Its only attachment is the `text/html` video page.
    3. **An old video.** `url` `https://www.bilibili.com/video/av170001`, `title` `Old video`, `content_html` `Description C`, `date_published` `2020-01-01T00:00:00.000Z`, and no attachments.
    4. **Not a video.** `url` `https://space.bilibili.com/2267573/article`, `title` `Not a video`, `content_html` `x`.

  **In a new file `backend/tests/test_bilibili.py`:**
  - **`test_uploader_addresses`,** parametrized with ids. With `rsshub_url="http://rsshub.test:1200"`, `uploader_mid(url, rsshub_url)` returns `"2267573"` for:
    - `space`: `https://space.bilibili.com/2267573`;
    - `section-query`: `https://space.bilibili.com/2267573/video?tid=0`;
    - `upload`: `https://space.bilibili.com/2267573/upload/video`;
    - `fragment`: `http://space.bilibili.com/2267573#top`;
    - `case-dot`: `HTTPS://SPACE.BILIBILI.COM./2267573`;
    - `mobile`: `https://m.bilibili.com/space/2267573`;
    - `route`: `http://rsshub.test:1200/bilibili/user/video/2267573?format=json`;
    - `route-embed`: `http://rsshub.test:1200/bilibili/user/video/2267573/disableEmbed`.

    It returns `None` for:
    - `other-site`: `https://example.com/feed`;
    - `other-route`: `http://rsshub.test:1200/github/repos/example`;
    - `route-unconfigured`: the `route` address with `rsshub_url=None`.
  - **`test_other_bilibili_addresses_are_refused`,** parametrized with ids:
    - `video`: `https://www.bilibili.com/video/BV1xx411c7mD`;
    - `short-link`: `https://b23.tv/abc123`;
    - `non-numeric`: `https://space.bilibili.com/abc`;
    - `too-long`: `https://space.bilibili.com/` followed by 21 digits;
    - `home`: `https://www.bilibili.com/`;
    - `image`: `https://i0.hdslb.com/a.jpg`.

    Each raises `AppError` with code `not_a_bilibili_uploader`, status 422, and the message "Paste the uploader's space address, such as https://space.bilibili.com/2267573.".
  - **`test_parse_uploader_feed`.** `parse_uploader_feed(FetchResponse(<route URL>, <fixture bytes>, "application/feed+json", 200), "2267573")` returns a `Feed` with:
    - `feed_url` `bilibili:uploader:2267573`, `site_url` `https://space.bilibili.com/2267573`, `title` `Sample Uploader`, and `kind` `bilibili`;
    - three entries, with identity keys `bilibili:video:BV1aa411c7aA`, `bilibili:video:BV1bb411c7bB` and `bilibili:video:av170001`. The item that is not a video is skipped;
    - each entry's `link` equal to its item's `url`, and `published_at` 2026-11-21 10:00 UTC for the first;
    - `content_text` of the first equal to `Description A`;
    - no `links`, `images`, comment pointers, or audio on any entry.
  - **`test_uploader_title`,** parametrized over the feed title and the first item's authors, giving the source title:
    - `Sample Uploader 的 bilibili 空间` → `Sample Uploader`;
    - `Plain Title` → `Plain Title`;
    - an empty title with author `Sample Uploader` → `Sample Uploader`;
    - an empty title and no authors → `Bilibili uploader 2267573`.
  - **`test_subtitles_from_data_attachment`.**
    - The first entry's `transcript_text` is `"Hello\n\nworld"`. It uses only the first `text/srt` attachment, so it does not contain `Second track`.
    - The second entry's `transcript_text` is `None`.
    - In a feed whose only attachment is `data:text/plain;base64,` plus the base64 of `SRT_A`, with `mime_type` `text/srt`, `transcript_text` is also `"Hello\n\nworld"`.
  - **`test_web_attachments_are_never_requested`,** parametrized over the attachment address `https://www.bilibili.com/sub.srt` and `https://subs.example/sub.srt`. DNS maps `subs.example` to `8.8.8.8`. A respx route for `https://subs.example/sub.srt` answers 200 with `SRT_A`, and the Bilibili route is added too. In a feed whose only subtitle attachment is `{"url": <address>, "mime_type": "text/srt"}`, `transcript_text` is `None`, and both routes have `call_count == 0`. (A Bilibili address alone cannot catch P2: `safe_fetch` refuses it before any request, so its route is never called either way.)
  - **`test_invalid_rsshub_answers`,** parametrized over:
    - an HTML page;
    - `{}`;
    - `{"version": "https://jsonfeed.org/version/1.1", "items": "busy"}`;
    - `{"version": "1.0", "items": []}`;
    - bytes that are not JSON.

    Each raises `FeedParseError("RSSHub could not read this uploader.")`.
  - **`test_fetch_uploader`,** parametrized with ids. DNS maps `rsshub.test` to `10.0.0.7`.
    - `not-configured`: settings without `rsshub_url` raise `FetchError` with code `rsshub_not_configured` and the message "Following Bilibili uploaders needs an RSSHub address (CATCHUP_RSSHUB_URL). See the README.". No request is made.
    - `ok`: the request goes to exactly `http://rsshub.test:1200/bilibili/user/video/2267573?format=json`, with a User-Agent that starts with `CatchUp/`.
    - `prefix`: `rsshub_url="http://rsshub.test:1200/hub"` requests `http://rsshub.test:1200/hub/bilibili/user/video/2267573?format=json`.
    - `http-error`: an answer of 503 raises `FetchError` with code `rsshub_failed`, `status_code` 503, and the message "RSSHub could not read this uploader (HTTP 503).".
    - `redirect-to-bilibili`: a 302 to `https://www.bilibili.com/` raises code `blocked_address`.
- [x] 2.2 Make them pass:
  - write `backend/src/catchup/sources/bilibili.py` with `uploader_mid`, `fetch_uploader`, `parse_uploader_feed` and the message constants, as D5 says;
  - add `FeedEntry.transcript_text` and `Feed.source_kind` to `sources/feeds.py`, with defaults, and have `Feed.kind` return `source_kind` when it is set.

  Read subtitles with `convert_transcript(<decoded bytes>, "text/srt")`, never with the `data:` URL's own type. Then run, and watch pass:
  - `uv run --offline pytest tests/test_bilibili.py tests/test_feeds.py tests/test_feed_transcripts.py`;
  - the full `uv run --offline pytest`.
- [x] 2.3 Run these mutations one at a time:

  | Mutation | Change | Expected failing test |
  | --- | --- | --- |
  | R1 | the `m.bilibili.com/space/<mid>` form removed | `test_uploader_addresses[mobile]` |
  | R2 | `www.bilibili.com/video/…` accepted as an uploader whose id is the last path segment | `test_other_bilibili_addresses_are_refused[video]` |
  | P1 | subtitles read with the `data:` URL's type `text/plain` | `test_subtitles_from_data_attachment` |
  | P2 | any `text/srt` attachment used, fetching non-`data:` addresses through `safe_fetch` | `test_web_attachments_are_never_requested` |
  | P3 | the ` 的 bilibili 空间` ending kept | `test_uploader_title`, `test_parse_uploader_feed` |

## 3. Preview and follow an uploader (D6)

- [x] 3.1 Write these tests and watch them fail. Today a pasted Bilibili or RSSHub-route address goes to discovery, which refuses it with `blocked_address` (the Bilibili host rule of group 1, or the private-address rule for `rsshub.test`), and confirming `bilibili:uploader:…` fetches it with `safe_fetch`, which refuses it as `invalid_url`.

  **In a new file `backend/tests/test_bilibili_sources_api.py`:**
  - **The setup.**
    - A module-level helper `rsshub_dns(monkeypatch, hosts=None)` patches `socket.getaddrinfo` with a stub that maps `rsshub.test` to `10.0.0.7`, appends every host name it is asked for to `hosts` when given, and raises `AssertionError` for any Bilibili host. A `client` fixture calls it, sets `CATCHUP_RSSHUB_URL=http://rsshub.test:1200` with `monkeypatch.setenv`, and then calls `create_app()`.
    - It fixes `catchup.api.sources.utc_now` at `NOW = datetime(2026, 11, 22, 12, tzinfo=timezone.utc)`.
    - A helper `serve_uploader(router, body)` routes the RSSHub URL of task 2.1, and adds the Bilibili route from the implementer notes.
  - **`test_preview_uploader`.**
    - With a feed of 7 videos, published one day apart, `POST /api/sources/preview` with `https://space.bilibili.com/2267573` answers 200.
    - The body is `{"feed_url": "bilibili:uploader:2267573", "site_url": "https://space.bilibili.com/2267573", "title": "Sample Uploader", "follows_site_feed_notice": false, "kind": "bilibili", "captions_enabled": false, "entries": [...]}`, with the 5 most recent videos, newest first.
    - RSSHub is requested once.
  - **`test_preview_through_the_rsshub_route_address`.** Pasting `http://rsshub.test:1200/bilibili/user/video/2267573?format=json` gives the same `feed_url` and `title`.
  - **`test_preview_refuses_other_bilibili_addresses`.** `https://www.bilibili.com/video/BV1xx411c7mD` answers 422 with code `not_a_bilibili_uploader`, and RSSHub is not requested.
  - **`test_preview_without_rsshub`.** A second client created without `CATCHUP_RSSHUB_URL` answers the space address with 422, code `rsshub_not_configured`, and the not-configured message.
  - **`test_preview_rsshub_failures`,** parametrized over:
    - RSSHub answering 503 → 422, code `rsshub_failed`, message "RSSHub could not read this uploader (HTTP 503).";
    - RSSHub answering a 200 HTML page → 422, code `rsshub_failed`, message "RSSHub could not read this uploader.".
  - **`test_confirm_uploader`.** Preview, then `POST /api/sources` with `{"feed_url": "bilibili:uploader:2267573"}`, using the fixture:
    - It answers 201 with `kind` `bilibili`, `site_url` `https://space.bilibili.com/2267573`, and `feed_url` `bilibili:uploader:2267573`. RSSHub is requested only once in all.
    - The source row has the title `Sample Uploader` and the input URL `bilibili:uploader:2267573`.
    - The item `bilibili:video:BV1aa411c7aA` is `pending`, with `transcript_status` `found`, `content_origin` `transcript`, and `content_text` `"Hello\n\nworld"`.
    - The item `bilibili:video:BV1bb411c7bB` is `pending`, with `transcript_status` `subtitle_wait`, `content_origin` `feed`, and `content_text` `Description B`.
    - The item `bilibili:video:av170001` is `baseline`.
    - Every item has `image_candidates == []` and `entry_links == []`.
  - **`test_confirm_without_a_cached_preview_fetches_again`.** Confirming without a preview requests RSSHub once, and saves the same items.
  - **`test_duplicate_uploader_in_any_address_form`.** After confirming:
    - previewing `https://m.bilibili.com/space/2267573` answers 422 with code `duplicate`;
    - confirming `bilibili:uploader:2267573` again answers 409.
  - **`test_confirm_refuses_a_malformed_bilibili_address`.** `{"feed_url": "bilibili:uploader:abc"}` answers 422 with code `not_a_bilibili_uploader`.
  - **`test_bilibili_entries_never_request_their_video_page`.** In a feed whose items have no subtitles, descriptions shorter than `short_text_chars`, and a `date_published` within the first-add window before `NOW` (so they are saved as `pending`; `article_text` is only called for pending items), confirming requests nothing but RSSHub. The Bilibili route has `call_count == 0`, and `catchup.api.sources.article_text`, replaced with a function that raises `AssertionError`, is never called.
- [x] 3.2 Make them pass in `backend/src/catchup/api/sources.py`, as D6 says:
  - recognize uploaders before `x_username`;
  - `_bilibili_preview`, with the response cached under `bilibili:uploader:<mid>`;
  - the confirm branch, sharing the existing confirm loop, with the transcript rule for `bilibili` entries.

  Then run, and watch pass:
  - `uv run --offline pytest tests/test_bilibili_sources_api.py tests/test_sources_api.py tests/test_x_sources_api.py`;
  - the full `uv run --offline pytest`.
- [x] 3.3 Run this mutation:

  | Mutation | Change | Expected failing test |
  | --- | --- | --- |
  | C3 | `bilibili` entries without subtitles go through `article_text` like website entries | `test_bilibili_entries_never_request_their_video_page` |

## 4. Checks, the subtitle wait, and Creator updates (D7)

- [x] 4.1 Write these tests and watch them fail. `check_source` fetches `bilibili:uploader:…` through `safe_fetch` and fails as an invalid URL. `subtitle_wait` never expires.

  **In a new file `backend/tests/test_bilibili_collection.py`,** with the DNS stub and `serve_uploader` of task 3.1:
  - **The setup.** An `environment` from `test_digest_runner`, `seed(environment, count=0, sources=0)`, and `environment.app.state.settings = replace(environment.app.state.settings, rsshub_url="http://rsshub.test:1200")`. A Bilibili source is added directly: `kind="bilibili"`, `feed_url="bilibili:uploader:2267573"`, `site_url="https://space.bilibili.com/2267573"`.
  - **`test_check_records_new_videos`.** `check_source(session, source, run_id, settings)` with the fixture records:
    - `BV1aa411c7aA` as `found`, from the subtitles;
    - `BV1bb411c7bB` as `subtitle_wait`;
    - `av170001` as pending too: checks treat every unseen entry as new, as for website feeds.

    The check's status is `new_items`, its `http_status` is 200, and the source's kind stays `bilibili`.
  - **`test_subtitles_that_appear_later_are_used`.**
    - A first check with a feed whose only item is `BV1bb411c7bB` without subtitles stores it as `subtitle_wait`.
    - Its `summary` is then set to `"Old"`.
    - A second check, where the same item now has the `SRT_A` attachment, makes it `found`, with `content_text` `"Hello\n\nworld"`, `content_origin` `transcript`, and `summary` `None`.
  - **`test_check_without_rsshub_fails`.** With `rsshub_url=None`, the check is `failed`, with the not-configured message as its `error`.
  - **`test_check_with_rsshub_errors_fails`,** parametrized over:
    - 503 → `failed`, `http_status` 503, error "RSSHub could not read this uploader (HTTP 503).";
    - a 200 HTML page → `failed`, `http_status` 200, error "RSSHub could not read this uploader.".
  - **`test_whole_run_never_requests_bilibili`.**
    - Add a pending item `bilibili:video:BV1bb411c7bB` in `subtitle_wait`, discovered 25 hours before now.
    - Serve the fixture, and record every host passed to `socket.getaddrinfo`. The recorded list is empty in this test: respx never opens a connection, and the RSSHub request skips the DNS check (D4). Do not assert that it is non-empty.
    - `execute(environment)` with the default `FakeModel` saves a digest in which:
      - `Video with subtitles` is summarized: the summary call's user message contains `Hello` and not `Description A`;
      - `Video without subtitles` is listed in Creator updates with the reason `no_subtitles`.
    - No recorded host is a Bilibili host, and the Bilibili route has `call_count == 0`.

  **In `backend/tests/test_creator_updates.py`** (new tests only, with its `ready` fixture and a Bilibili variant of `add_item`):
  - **`test_subtitle_wait_ends_in_creator_updates`.**
    - Two pending `bilibili` items in `subtitle_wait` are discovered 25 hours and 23 hours before `NOW`.
    - The run lists the first under its uploader in Creator updates with the reason `no_subtitles`, and its `waiting_count` is 1.
    - No model call includes either item.
- [x] 4.2 Make them pass:
  - the `bilibili` branch of `check_source` (`collection.py`), with new entries recorded as in D6, and waiting items resolved again;
  - `subtitle_wait` and `no_subtitles` in `select_pending` and `CREATOR_REASONS` (`digest/runner.py`).

  Then run, and watch pass:
  - `uv run --offline pytest tests/test_bilibili_collection.py tests/test_creator_updates.py tests/test_collection.py tests/test_podcast_collection.py tests/test_caption_pass.py tests/test_digest_runner.py`;
  - the full `uv run --offline pytest`.
- [x] 4.3 Run these mutations one at a time:

  | Mutation | Change | Expected failing test |
  | --- | --- | --- |
  | C1 | pending `subtitle_wait` items are not resolved again | `test_subtitles_that_appear_later_are_used` |
  | C2 | `subtitle_wait` never expires | `test_subtitle_wait_ends_in_creator_updates`, `test_whole_run_never_requests_bilibili` |

## 5. The Sources page, Home, and the extension popup (D8)

- [x] 5.1 Write these tests and watch them fail. The kind, the reason and the text are missing, and the rows show `feed_url`.

  **In `frontend/src/components/ui.test.tsx`:**
  - **`names the Bilibili kind and the no-subtitles reason`.** It renders `<KindBadge kind="bilibili"/>` and `<ReasonLabel reason="no_subtitles"/>`, and finds "Bilibili uploader" and "No subtitles from RSSHub". It passes `expectAccessible`.

  **In `frontend/src/pages/Sources.test.tsx`:**
  - **`previews a Bilibili uploader with its space address and the terms note`.** The preview answer is `{feed_url: 'bilibili:uploader:2267573', site_url: 'https://space.bilibili.com/2267573', title: 'Sample Uploader', follows_site_feed_notice: false, kind: 'bilibili', captions_enabled: false, entries: [...]}`. The preview shows:
    - "Bilibili uploader";
    - "Subtitles read through your RSSHub; videos without subtitles are listed without summaries";
    - the text "Bilibili's user agreement does not allow automated access";
    - a link to `https://space.bilibili.com/2267573`;
    - no text `bilibili:uploader:2267573`, and no "Feed" term.

    It passes `expectAccessible`.
  - **`shows a Bilibili uploader by its space address`.** A saved source with `kind: 'bilibili'` shows "Bilibili uploader" and `https://space.bilibili.com/2267573`, and not `bilibili:uploader:2267573`.
  - **`lists Bilibili uploaders among what you can add`.** The rail shows "Bilibili uploaders — through an RSSHub you run".

  **In `frontend/src/pages/Home.test.tsx`:**
  - **`counts Bilibili uploaders only when there are some`.**
    - With the sources of the existing rail test plus one `{ kind: 'bilibili' }`, the rail's counts end with "1 Bilibili uploader".
    - Without it, the rail contains no "Bilibili".

  **In `extension/src/test/popup.test.ts`:**
  - **`labels a bilibili preview as Bilibili uploader and shows its space address`.** On a tab at `https://space.bilibili.com/2267573`, with the Bilibili preview above, "Follow this site" shows "Bilibili uploader" and `https://space.bilibili.com/2267573`, and not `bilibili:uploader:2267573`. Confirm sends `{feed_url: 'bilibili:uploader:2267573'}`. It passes axe, as the neighboring tests do.
- [x] 5.2 Make them pass, as D8 says. The files are:
  - `frontend/src/components/ui.tsx`;
  - `frontend/src/components/Icon.tsx`: a generic screen with a play mark, not Bilibili's logo;
  - `frontend/src/pages/Sources.tsx`;
  - `frontend/src/pages/Home.tsx`;
  - `extension/src/popup.ts`.

  Then run, and watch pass:
  - `npm test -- --run` and `npm run build` in `frontend/`;
  - `npm test -- --run` and `npm run build` in `extension/`.
- [x] 5.3 Run these mutations one at a time:

  | Mutation | Change | Expected failing test |
  | --- | --- | --- |
  | U1 | the Sources row shows `feed_url` for `bilibili` | `shows a Bilibili uploader by its space address` |
  | X1 | the popup shows `feed_url` for `bilibili` | `labels a bilibili preview as Bilibili uploader and shows its space address` |

## 6. The Compose override, `.env.example`, and the README (D9)

- [ ] 6.1 Write these tests and watch them fail: `compose.rsshub.yaml`, the `.env.example` line and the README section are missing. (The `.gitignore` and `.dockerignore` checks already pass.)

  **In a new file `backend/tests/test_rsshub_docs.py`.** Use the `read_file`, `readme_section` and `collapse_whitespace` helpers of `tests/test_install_docs.py`, imported from it.
  - **`test_rsshub_override_is_exact_and_optional`.**
    - `compose.rsshub.yaml` equals the YAML block in D9 with the two-space list indentation removed (so `services:` starts at column 1), byte for byte, with one final newline. Write the expected text into the test as a literal string.
    - `compose.yaml` does not contain `rsshub`.
  - **`test_rsshub_settings_stay_local`.**
    - `.gitignore` has the line `.env.*`.
    - The first line of `.dockerignore` is `*`, and no `.dockerignore` line names `.env`.
    - `.env.example` has the line `# CATCHUP_RSSHUB_URL=http://rsshub:1200`.
  - **`test_readme_explains_bilibili_uploaders`.** After `collapse_whitespace`, the README's `Bilibili uploaders` section contains each of these:
    - `CATCHUP_RSSHUB_URL`;
    - `compose.yaml:compose.rsshub.yaml`;
    - `compose.yaml:compose.build.yaml:compose.rsshub.yaml`;
    - `diygod/rsshub:latest`;
    - `diygod/rsshub:chromium-bundled`;
    - `CatchUp never contacts Bilibili`;
    - `section 5.6(3)`;
    - `BILIBILI_COOKIE_`;
    - `.env.rsshub`;
    - `public RSSHub instance`;
    - `No subtitles from RSSHub`.

    Every line of the section's `sh` code blocks that contains `docker compose up -d` also contains `--wait` (`test_every_docker_compose_start_waits_for_health` reads only `## Run with Docker`, so it does not check this section). The README's `Supported sources` section mentions `Bilibili uploaders`.
- [ ] 6.2 Make them pass:
  - write `compose.rsshub.yaml`;
  - add the line to `.env.example`;
  - add the README section after `## X accounts`, with what the `bilibili-uploaders` spec's "State Bilibili's terms" requirement lists, and the line in `## Supported sources`.

  Every start command in the new section waits for health (`docker compose up -d --wait`, or `docker compose up -d --build --wait`). The section covers both installs. For the published image, `.env` has no `COMPOSE_FILE` line yet: the section tells the reader to download `compose.rsshub.yaml` next to `compose.yaml` (as `### Published image` downloads `compose.yaml` with `curl -fsSLo`), and to add the line `COMPOSE_FILE=compose.yaml:compose.rsshub.yaml` to `.env`. For a source build, it tells the reader to change the existing line `COMPOSE_FILE=compose.yaml:compose.build.yaml` to `COMPOSE_FILE=compose.yaml:compose.build.yaml:compose.rsshub.yaml`, not to add a second one.

  Then run, and watch pass:
  - `uv run --offline pytest tests/test_rsshub_docs.py tests/test_install_docs.py tests/test_readme_context.py`;
  - the full `uv run --offline pytest`;
  - `npm test -- --run` in `extension/` (`src/test/docs.test.ts` reads `README.md`).
- [ ] 6.3 Run this mutation:

  | Mutation | Change | Expected failing test |
  | --- | --- | --- |
  | D1 | `section 5.6(3)` removed from the README section | `test_readme_explains_bilibili_uploaders` |

## 7. Final checks and the report

- [ ] 7.1 Run, and record the output and counts:
  - `uv run --offline pytest` in `backend/`;
  - `npm test -- --run` and `npm run build` in `frontend/`;
  - `npm test -- --run` and `npm run build` in `extension/`;
  - `DO_NOT_TRACK=1 openspec validate add-bilibili-sources --strict`;
  - `git diff --check` against the plan commit.

  All must pass. Do not run Docker.
- [ ] 7.2 Write `docs/process/test-report-add-bilibili-sources.md`. Record:
  - each group's red and green results;
  - every mutation with its result;
  - the commands of 7.1 with their counts;
  - that Claude Code runs Docker smoke and the live check with a local RSSHub at review.
- [ ] 7.3 Add a Droid entry to `docs/process/ai-usage-log.md`: the prompt (a faithful excerpt), the tool and model, the outcome, what failed, and how it was resolved. Leave the session line for Claude Code to fill in.
