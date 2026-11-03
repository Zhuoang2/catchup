# Tasks

Implementer notes:
- **Read first:** `proposal.md`, `design.md` (D1–D6), and `specs/content-collection/spec.md`. Line numbers are at main `8faaed6`; re-check them. If something looks wrong, stop and report instead of redesigning.
- **Test-first with the `tdd` skill** (D-016). Each check must fail on the current branch head first, except checks marked "guard (already green)", which must instead fail under their named mutation. Run each named mutation, record its result, and revert it.
- **Tests:** backend pytest with `respx`, the autouse network block (`backend/tests/conftest.py`), and `FakeModel` for runs. Fixtures are invented. No test may hang or sleep for real; give any mocked route that could be called more often than expected a `side_effect` that fails on the extra call.
- **OpenSpec CLI:** always `DO_NOT_TRACK=1 openspec …`.
- **Commits:** commit after each task group. Do not push, tag, or open a PR.

## 1. Addresses that cannot be parsed

- [ ] 1.1 **The helper** (D1): add `backend/src/catchup/net/urls.py` with `join_url(base, href)` and `split_url(url)`, returning `None` when `urljoin`/`urlsplit` raise `ValueError`. Tests first, in a new `backend/tests/test_urls.py`: `join_url("https://blog.example/post", "https://[object Object]")` and `join_url("https://blog.example/", "http://[x")` give `None`; `split_url("http://[x")` gives `None`; ordinary relative and absolute joins match `urljoin`. Verify: the tests fail before the module exists, and pass after.
- [ ] 1.2 **Feeds and saved pages** (D1), in `backend/src/catchup/sources/feeds.py` (`filter_image_urls`, the entry HTML link collector near `:224`). Tests first, in `backend/tests/test_feeds.py`:
  - `filter_image_urls` with candidates `https://[object Object]`, `http://[x`, and one good image keeps only the good one;
  - `parse_feed` on an invented RSS feed with two entries, where entry 1 has `<img src="https://[object Object]">` in its HTML, a `media:content url="http://[x"`, and a link `<a href="http://[x">`, and entry 2 is ordinary: both entries are parsed, entry 1 keeps its text and its good links and images, and the bad addresses are absent;
  - `POST /api/captures` (in `backend/tests/test_extension_api.py`) with an image whose URL is `https://[object Object]` saves the page without that image, instead of answering 500;
  - **through a run** (in `backend/tests/test_digest_runner.py`, with `FakeModel`): source 1's feed has that entry 1, and source 2 is healthy; the run succeeds, both sources are checked, and entry 1 is in the digest.

  Verify: the tests fail on the current head (`ValueError`), and pass after. Then the named mutation "call `urljoin` directly in `filter_image_urls` again" fails the `filter_image_urls` test, and is reverted.
- [ ] 1.3 **Discovery and linked pages** (D1), in `backend/src/catchup/sources/discovery.py` (declared-feed loop near `:118`) and `backend/src/catchup/context/links.py` (`related_links`). Tests first:
  - in `backend/tests/test_discovery.py`: a page declaring two feeds, `<link rel="alternate" type="application/rss+xml" href="http://[x">` and a good one, previews the good one (the bad `href` is skipped, and no 500);
  - in `backend/tests/test_context_links.py`: `related_links` with an item link `http://[x`, or a site URL `https://[object Object]/`, and one good link returns the good link; a link `http://[x` among the links is skipped.

  Verify: the tests fail on the current head, and pass after.
- [ ] 1.4 **`safe_fetch` and `httpx.InvalidURL`** (D2), in `backend/src/catchup/net/safe_fetch.py`. Tests first, in `backend/tests/test_safe_fetch.py`: with the `resolve` fixture answering the host, `safe_fetch("https://public.example/a\x7fb")` raises `FetchError` with code `invalid_url`, and no route is called (`respx.mock(assert_all_mocked=True, assert_all_called=False)` with a route whose `side_effect` fails). In `backend/tests/test_collection.py` (or the existing `article_text` tests): a short feed entry whose link contains `\x7f` keeps its feed text, with origin `feed`.

  Verify: the tests fail on the current head (`httpx.InvalidURL` escapes), and pass after. Then the named mutation "remove the `httpx.InvalidURL` mapping" fails the `safe_fetch` test, and is reverted.

## 2. One source's error stays with that source

- [ ] 2.1 **The guard per source** (D3), in `backend/src/catchup/digest/runner.py`, used by the feed/podcast/YouTube loop and the X loop. Tests first, in `backend/tests/test_digest_runner.py`, with `FakeModel`:
  - **An unexpected error.** Monkeypatch `catchup.digest.runner.check_source` so it raises `RuntimeError("boom")` for source 1 only, and calls the real function for source 2: the run succeeds; source 1 has a `failed` check with error "Could not check this source.", `entries_seen` 0, and `last_check_status` `failed`; source 2 is checked and its items are in the digest; the log record names `RuntimeError` and does not contain "boom" (use `caplog`).
  - **An X account.** Monkeypatch `check_x_account` to raise `RuntimeError` for one X account: that account is `failed` with the same message, a second X account is still read, and `x_reads` counts the reads already charged.
  - **A deleted source.** In a fake fetch for source 1 (monkeypatch `catchup.collection.safe_fetch`), delete source 1 with a new session from `app.state.session_factory`, then return a valid feed: the run succeeds, source 2 is checked, and no check row exists for source 1.

  Verify: the tests fail on the current head (the run fails), and pass after. Then the named mutation "re-raise in the guard instead of recording `failed`" fails the unexpected-error test, and is reverted.
- [ ] 2.2 **The caption pass per item** (D4), in `caption_pass` (`backend/src/catchup/digest/runner.py:66-112`). Tests first, in `backend/tests/test_digest_runner.py` (or the existing caption tests): two pending YouTube items from two channels; `fetch_captions` is faked so that, while fetching item 1, it deletes item 1's channel with a new session; the run succeeds, and item 2 gets its captions. A second test: committing item 1 raises a monkeypatched `RuntimeError` once; item 2 is still processed, and item 1 keeps its previous `transcript_status`.

  Verify: the tests fail on the current head (`StaleDataError` / `RuntimeError` fails the run), and pass after.

## 3. Report and checks

- [ ] 3.1 **Report.** Write `docs/process/test-report-isolate-source-check-failures.md`, with each task's observed red result, each named mutation's result, and the final numbers.
- [ ] 3.2 **Checks, in this order:**
  1. `npm run build` in `frontend/` (the backend tests serve the built frontend);
  2. `uv run --python 3.12 pytest --cov=catchup --cov-report=term` in `backend/`;
  3. `npm test -- --run` in `frontend/`, and `npm test -- --run` in `extension/` (unchanged, as a guard);
  4. `docker build -t catchup:isolate-local .` and `scripts/docker-smoke.sh catchup:isolate-local`;
  5. `DO_NOT_TRACK=1 openspec validate isolate-source-check-failures --strict`.
- [ ] 3.3 **Logs.** Add the coverage-summary line to `docs/process/coverage-summary.md`, and your AI usage log entry to `docs/process/ai-usage-log.md`, with a faithful excerpt of the prompt you received. Leave out the session id.

  Verify: every command passes, and the report has the actual numbers.
