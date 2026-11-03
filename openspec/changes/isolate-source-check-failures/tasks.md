# Tasks

Implementer notes:
- **Read first:** `proposal.md`, `design.md` (D1–D6), and `specs/content-collection/spec.md`. Line numbers are at main `8faaed6`; re-check them. If something looks wrong, stop and report instead of redesigning.
- **Test-first with the `tdd` skill** (D-016). Each check must fail on the current branch head first, except checks marked "guard (already green)", which must instead fail under their named mutation. Run each named mutation, record its result, and revert it.
- **Tests:** backend pytest with `respx`, the autouse network block (`backend/tests/conftest.py`), and `FakeModel` for runs. Fixtures are invented. No test may hang or sleep for real; give any mocked route that could be called more often than expected a `side_effect` that fails on the extra call.
- **OpenSpec CLI:** always `DO_NOT_TRACK=1 openspec …`.
- **Commits:** commit after each task group. Do not push, tag, or open a PR.

## 1. Addresses that cannot be parsed

- [x] 1.1 **The helper** (D1): add `backend/src/catchup/net/urls.py` with `join_url(base, href)` and `split_url(url)`, returning `None` when `urljoin`/`urlsplit` raise `ValueError`. Tests first, in a new `backend/tests/test_urls.py`: `join_url("https://blog.example/post", "https://[object Object]")` and `join_url("https://blog.example/", "http://[x")` give `None`; `split_url("http://[x")` gives `None`; ordinary relative and absolute joins match `urljoin`. Verify: the tests fail before the module exists, and pass after.
- [x] 1.2 **Feeds and saved pages** (D1), in `backend/src/catchup/sources/feeds.py` (`filter_image_urls`, the entry HTML link collector near `:224`). Tests first, in a new `backend/tests/test_feeds.py` (the existing image and `parse_feed` tests are in `backend/tests/test_discovery.py:132-190`; follow their fixtures):
  - `filter_image_urls` with `base="https://blog.example/post"` and candidates `https://[object Object]`, `http://[x`, and one good image keeps only the good one (with the default `base=""`, `urljoin` does not parse, and the check would already pass);
  - `parse_feed` on an invented RSS feed with two entries, where entry 1 has `<img src="https://[object Object]">` in its HTML, a `<media:content url="http://[x" medium="image"/>` (without `medium="image"` or an image `type` it is never a candidate, `feeds.py:99`), and a link `<a href="http://&#91;x">bad</a>` (feedparser's sanitizer turns a literal `href="http://[x"` into `href=""`; the character reference survives it, and the link collector decodes it), and entry 2 is ordinary: both entries are parsed, entry 1 keeps its text, its good links, and its good images, and the bad addresses are absent. Note: an `<a href="">` that feedparser empties becomes a link to the entry itself, before and after the fix; do not assert it away;
  - `POST /api/captures` (in `backend/tests/test_extension_api.py`) with an image whose URL is `https://[object Object]` saves the page without that image, instead of answering 500;
  - **through a run** (in `backend/tests/test_digest_runner.py`, with `FakeModel`): source 1's feed has that entry 1, and source 2 is healthy; the run succeeds, both sources are checked, and entry 1 is in the digest.

  Verify: the tests fail on the current head (`ValueError`), and pass after. Then the named mutation "call `urljoin` directly in `filter_image_urls` again" fails the `filter_image_urls` test, and is reverted.
- [x] 1.3 **Discovery and linked pages** (D1), in `backend/src/catchup/sources/discovery.py` (declared-feed loop near `:118`) and `backend/src/catchup/context/links.py` (`related_links`). Tests first:
  - in `backend/tests/test_discovery.py`: a page declaring two feeds, `<link rel="alternate" type="application/rss+xml" href="http://[x">` and a good one, previews the good one (the bad `href` is skipped, and no 500);
  - in `backend/tests/test_context_links.py`: `related_links` with an item link `http://[x`, or a site URL `https://[object Object]/`, and one good link returns the good link; a link `http://[x` among the links is skipped (guard, already green: `links.py:24-48` already catches it; mutation: remove that `try`).
  - In the discovery test, the bad `href` must come before the good one; otherwise discovery returns the good feed first, and the test passes on the current head.

  Verify: the tests fail on the current head, except the guard, and pass after.
- [x] 1.4 **`safe_fetch` and `httpx.InvalidURL`** (D2), in `backend/src/catchup/net/safe_fetch.py`. Tests first, in `backend/tests/test_safe_fetch.py`: with the `resolve` fixture answering the host, `safe_fetch("https://public.example/a\x7fb")` raises `FetchError` with code `invalid_url`, and no route is called (`respx.mock(assert_all_mocked=True, assert_all_called=False)` with a route whose `side_effect` fails). For `article_text` (existing tests: `backend/tests/test_sources_api.py:193-219`): a short feed entry whose link contains `\x7f` keeps its feed text, with origin `feed`. Mock DNS for this test (the `app` fixture in `test_collection.py`, or a `getaddrinfo` lookup like the `resolve` fixture): the autouse block raises `AssertionError` from `getaddrinfo`, which `_check_address` does not catch, so without a lookup the test fails before and after the fix. `httpx.InvalidURL` is raised after DNS, when `client.stream` builds the URL.
  - `POST /api/sources/preview` with `https://public.example/a\x7fb` (DNS mocked) answers 422 `invalid_url`, not 500.

  Verify: the tests fail on the current head (`httpx.InvalidURL` escapes), and pass after. Then the named mutation "remove the `httpx.InvalidURL` mapping" fails the `safe_fetch` test, and is reverted.

## 2. One source's error stays with that source

- [x] 2.1 **The guard per source** (D3), in `backend/src/catchup/digest/runner.py`, used by the feed/podcast/YouTube loop and the X loop. Tests first, in `backend/tests/test_digest_runner.py`, with `FakeModel`:
  - **An unexpected error.** Monkeypatch `catchup.digest.runner.check_source` so it raises `RuntimeError("boom")` for source 1 only, and calls the real function for source 2: the run succeeds; source 1 has a `failed` check with error "Could not check this source.", `entries_seen` 0, and `last_check_status` `failed`; source 2 is checked and its items are in the digest; the log record names `RuntimeError` and does not contain "boom" (use `caplog`).
  - **An X account.** Monkeypatch `catchup.digest.runner.check_x_account` (the runner imports it by name; patching `sources/x_check.py` has no effect) with a fake that calls `budget.charge(3)` and then raises `RuntimeError` for one X account, and calls the real function for the other: that account is `failed` with the same message, the second X account is still read, and `x_reads` includes the 3 charged reads. Setup: save a token with `PUT /api/settings/x`, and give each X account a respx route, as `test_digest_runner.py`'s X tests do.
  - **A deleted source.** In a fake fetch for source 1 (monkeypatch `catchup.collection.safe_fetch`), delete source 1 with a new session from `app.state.session_factory`, then return a valid feed: the run succeeds, source 2 is checked, and no check row exists for source 1.

  - **Notes for the guard.** Use the loop's `source_id`, never `source.id`, after a rollback: reading an attribute of a deleted row raises `ObjectDeletedError`. Do not use `check_source`'s return value: existing stubs return `None` (`test_caption_pass.py:198-203`, `test_digest_runner.py:1327-1334`).

  Verify: the tests fail on the current head (the run fails), and pass after. Then the named mutation "re-raise in the guard instead of recording `failed`" fails the unexpected-error test, and is reverted.
- [x] 2.2 **The caption pass per item** (D4), in `caption_pass` (`backend/src/catchup/digest/runner.py:66-112`). Collect the item ids before the loop, and load each with `session.get(Item, id)`, skipping `None`: a preloaded item whose channel was deleted raises `ObjectDeletedError` on its first attribute read, and so does logging `item.id` after a rollback. Tests first, in `backend/tests/test_caption_pass.py` (or `test_digest_runner.py`):
  - three pending YouTube items: items 1 and 2 from channel 1, item 3 from channel 2; `fetch_captions` is faked so that, while fetching item 1, it deletes channel 1 with a new session; the run succeeds, item 2 is skipped without an error, and item 3 gets its captions;
  - a second test: item 1's update fails once, through `event.listen(Item, "before_update", …)` that raises `RuntimeError` for item 1 only on its first call (the pattern of the existing `event.listen(DigestItem, "before_insert", …)` test), or by patching `catchup.digest.runner.is_short` to raise for item 1; item 2 is still processed, and item 1 keeps its previous `transcript_status`.

  Verify: the tests fail on the current head (`StaleDataError` / `RuntimeError` fails the run), and pass after.

## 3. Report and checks

- [x] 3.1 **Report.** Write `docs/process/test-report-isolate-source-check-failures.md`, with each task's observed red result, each named mutation's result, and the final numbers.
- [x] 3.2 **Checks, in this order:**
  1. `npm run build` in `frontend/` (the backend tests serve the built frontend);
  2. `uv run --python 3.12 pytest --cov=catchup --cov-report=term` in `backend/`;
  3. `npm test -- --run` in `frontend/`, and `npm test -- --run` in `extension/` (unchanged, as a guard);
  4. `docker build -t catchup:isolate-local .` and `scripts/docker-smoke.sh catchup:isolate-local`;
  5. `DO_NOT_TRACK=1 openspec validate isolate-source-check-failures --strict`.
- [x] 3.3 **Logs.** Add the coverage-summary line to `docs/process/coverage-summary.md`, and your AI usage log entry to `docs/process/ai-usage-log.md`, with a faithful excerpt of the prompt you received. Leave out the session id.

  Verify: every command passes, and the report has the actual numbers.
