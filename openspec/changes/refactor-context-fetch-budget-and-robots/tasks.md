# Tasks

Implementer notes:
- **Read first.** Read `proposal.md`, `design.md` (all of "Context", and D1–D5), and the spec delta under `specs/`. If something looks wrong or contradictory, stop and report instead of redesigning.
- **Work test-first with the `tdd` skill** (D-016). For each group, first write its tests, run them, and watch them fail for the stated reason. Then implement until they pass. The seams are named in each task, and they count as agreed:
  - `respx` routes;
  - the `resolve` fixture and `PUBLIC` in `backend/tests/test_safe_fetch.py`;
  - the `public_dns` fixture;
  - `monkeypatch` of `catchup.net.safe_fetch.monotonic`;
  - the helpers in `backend/tests/test_digest_runner.py` and `backend/tests/test_context_gather.py`: `environment`, `seed`, `setup`, `html`, `stub_collection`, and `execute`;
  - `page` and `comment` in `backend/tests/test_context_comments.py`.
- **Test rules.**
  - No real network and no real sleeps.
  - Use `respx.mock(assert_all_mocked=True, ...)` as the existing tests do. `assert_all_called` defaults to `True`. A test with a route that must not be called passes `assert_all_called=False`.
  - httpx lowercases a host name and drops a default port (design, probes). So one route on `https://site.example/...` receives requests written as `https://SITE.example/...` and `https://site.example:443/...`. Count calls on that one route.
  - A respx route without a port matches every port, and the first matching route wins. Register a route with a non-default port before the route without a port for the same host.
  - httpx keeps the letter case of an IPv6 address, so write IPv6 routes in lowercase, as the normalized origin is.
  - `gather.fetch` swallows every exception except `BudgetExhausted`. An `assert` inside a respx `side_effect` or an `allow` callback therefore has no effect during a run. Record values in a list, and assert after `execute`.
  - `tests/conftest.py` replaces `catchup.net.safe_fetch.sleep` with a function that raises.
  - Change no existing test, except `test_robots_request_uses_shared_budget` in task 2.1. If any other existing test fails after a change, stop and report: the design says the behavior stays.
  - Do not edit `docs/process/decision-log.md` or `docs/process/requirements-changes.md`. Claude Code wrote D-031 and the requirements row with the plan.
- **Out of scope:**
  - `frontend/` and `extension/`;
  - `api/`, `collection.py`, `sources/discovery.py`, and `digest/runner.py`;
  - migrations, models, and dependency versions.
- **Commits.** Commit after each task group. Do not push, tag, or open a PR.

## 1. `safe_fetch`: one budget error and a per-request check (D1, D3)

- [x] 1.1 Write the failing tests in `backend/tests/test_safe_fetch.py`. Use the `resolve` fixture and `PUBLIC`. Import `BudgetExhausted` inside the new tests, not at the top of the module: until 1.2, a module-level import would stop all 62 existing tests from being collected. Move it to the module import in 1.2.
  - `test_budget_exhausted_is_a_fetch_error`. Call `safe_fetch(PUBLIC, budget=[0])` under `respx.mock(assert_all_mocked=True, assert_all_called=False)`, with a `PUBLIC` route. Assert that it raises `BudgetExhausted`, that the error is a `FetchError` with code `fetch_failed` and the message "Feed probing request limit reached.", and that the route was not called.
  - `test_allow_sees_every_request_url`. `PUBLIC` answers 302 to `https://public.example/two`, which answers 302 to `https://public.example/three`, which answers 200 `b"ok"`. Pass `allow` as a function that appends each URL to a list and returns `True`. Assert:
    - the list is the three URLs, in order;
    - the content is `b"ok"`.
  - `test_refused_redirect_target_is_not_requested`. `PUBLIC` answers 302 to `https://public.example/private`. `allow` returns `False` only for that URL. Pass `budget=[5]`. Assert:
    - `FetchError` with code `robots_disallowed`;
    - the `/private` route was not called;
    - the budget is `[4]`: only the first request took a unit.
  - `test_allow_runs_after_the_address_check_and_before_budget_and_spacing`. Two cases:
    - the address resolves to `127.0.0.1` (as in `test_address_check_runs_before_budget_and_spacing`). Assert that `allow` was not called, and that the error code is `blocked_address`;
    - `allow` returns `False`, with `budget=[1]` and a spacer whose `wait` calls `pytest.fail`. Assert code `robots_disallowed`, and that the budget is still `[1]`.
  - `test_time_in_allow_does_not_count_against_the_deadline`. Replace `catchup.net.safe_fetch.monotonic` with a list-backed clock that starts at `100.0`. `allow` moves the clock forward by 40 seconds and returns `True`. `PUBLIC` answers 200 `b"ok"`. Assert that the content is `b"ok"`.

  Verify: run `uv run pytest tests/test_safe_fetch.py` in `backend/`. Before 1.2, the new tests fail on the missing import, or on the unknown `allow` argument. Every existing test passes.
- [x] 1.2 Implement D1 and the `safe_fetch` part of D3 in `backend/src/catchup/net/safe_fetch.py`.
  - Add `class BudgetExhausted(FetchError)`, whose constructor takes no arguments and sets today's code and message (design D3). Raise `BudgetExhausted()` where the budget runs out.
  - Add the keyword argument `allow=None`. Call it after `_check_address(current)`, and before the budget unit is taken. When it returns `False`, raise `FetchError("robots_disallowed", "robots.txt does not allow this page.")`.
  - Measure the time spent in `allow` with `monotonic()`, and add it to `deadline`.
  - Change nothing else.

  Verify:
  - the 1.1 tests pass, and `uv run pytest` passes in `backend/`;
  - each mutation below makes at least the named test fail. Run each one alone, watch it fail, and restore the code. Record each mutation and the tests that failed in the test report (task 5.1):
    - (S1) Call `allow` only for the first request: `test_refused_redirect_target_is_not_requested`.
    - (S2) Call `allow` after taking the budget unit: `test_refused_redirect_target_is_not_requested` (budget `[3]`) and `test_allow_runs_after_the_address_check_and_before_budget_and_spacing`.
    - (S3) Do not move the deadline: `test_time_in_allow_does_not_count_against_the_deadline`.
    - (S4) Raise a plain `FetchError` instead of `BudgetExhausted`: `test_budget_exhausted_is_a_fetch_error`.

## 2. robots.txt: one read per origin, and the budget error (D2, D3)

- [x] 2.1 Write the failing tests in `backend/tests/test_context_robots.py`.
  - Change `test_robots_request_uses_shared_budget`, the one existing test that pins the old signal. With `budget=[0]`, `allowed(...)` raises `BudgetExhausted` (`pytest.raises`), and the route is not called.
  - `test_one_robots_read_for_three_spellings`. One route, `https://site.example/robots.txt`, answers `"User-agent: *\nDisallow: /b\n"`. With `budget=[5]`, call `allowed` for `https://SITE.example/a`, `https://site.example:443/b`, and `https://site.example/c`. Assert:
    - the results are `True`, `False`, and `True`;
    - the route was called once;
    - the budget is `[4]`.
  - `test_scheme_and_other_ports_stay_separate_origins`. Register a route for `https://site.example:8443/robots.txt` first, then routes for `https://site.example/robots.txt` and `http://site.example/robots.txt`, each answering 404 (see the test rules on ports). Call `allowed` for one URL on each, plus `http://site.example:80/x`. Assert that each route was called once.
  - `test_ipv6_host_keeps_its_brackets`. One route on `https://[2001:db8::1]/robots.txt`, answering 404. Assert that `allowed("https://[2001:DB8::1]/x")` is `True`, and that the route was called once.
  - `test_budget_running_out_in_a_robots_redirect_propagates`. `https://site.example/robots.txt` answers 302 to `/robots-moved.txt`. On one `RobotsCache(budget=[1])`, call `allowed("https://site.example/post")` twice. Both calls raise `BudgetExhausted`, and the robots.txt route was called once.

  Verify: run `uv run pytest tests/test_context_robots.py` in `backend/`. Before 2.2:
  - the changed budget test and the redirect test fail, because `allowed` returns `False`;
  - the three-spellings test fails, because robots.txt is read three times;
  - the separate-origins test fails, because `http://site.example:80/x` reads the `http` robots.txt a second time. Its other three calls guard D2 against merging too much (O2);
  - the IPv6 test fails, because the robots.txt request keeps the upper-case address and matches no route.
- [x] 2.2 Implement D2 and the `RobotsCache` part of D3 in `backend/src/catchup/context/robots.py`.
  - Build the cache key and the robots.txt URL from the normalized origin.
  - Raise `BudgetExhausted()` at budget 0 for an origin that is not cached yet. The class sets its own code and message (design D3).
  - Let a `BudgetExhausted` from the robots.txt request propagate without caching. Keep today's rule for every other `FetchError`.

  Verify:
  - the 2.1 tests pass, and `uv run pytest` passes in `backend/`;
  - mutations, recorded as in 1.2:
    - (O1) Key by the raw `netloc` again: `test_one_robots_read_for_three_spellings`.
    - (O2) Key by `hostname` alone, without scheme and port: `test_scheme_and_other_ports_stay_separate_origins`.
    - (O3) Cache `False` for a `BudgetExhausted` from the robots.txt request, either returning `False` or re-raising after caching: `test_budget_running_out_in_a_robots_redirect_propagates`. Run both forms.
    - (O4) Build the origin without brackets around an IPv6 address: `test_ipv6_host_keeps_its_brackets`.

## 3. The linked-page pass: robots for every request, one budget signal (D1, D3)

- [ ] 3.1 Write the failing tests in `backend/tests/test_context_gather.py`. Use `setup`, `stub_collection(monkeypatch)`, `html`, and `respx.mock(assert_all_mocked=True, assert_all_called=False)`.
  - `test_redirect_to_disallowed_page_is_not_requested` (spec scenario "Link redirects to a disallowed page"). One link, `https://short.example/x`.
    - `short.example` robots.txt answers 404, and `/x` answers 302 to `https://docs.example/private`.
    - `docs.example` robots.txt answers `"User-agent: *\nDisallow: /private\n"`.

    Assert:
    - the run succeeds, and the `/private` route was not called;
    - no `ItemContext` row exists;
    - `context_done` is 1: a refused fetch counts as finished.
  - `test_redirect_to_site_with_unreadable_robots_is_not_requested` (spec scenario "Link redirects to a site whose robots.txt cannot be read"). Links `https://short.example/x` and `https://other.example/b`.
    - `short.example` robots.txt answers 404, and `/x` answers 302 to `https://down.example/p`.
    - `down.example` robots.txt answers 503.
    - `other.example` robots.txt answers 404, and `/b` answers `html("Other", "Other context " * 40)`.

    Assert:
    - the `down.example/p` route was not called;
    - exactly one `ItemContext` row exists, with URL `https://other.example/b`.
  - `test_three_spellings_of_one_site_share_robots` (spec scenario "One site written three ways"). Links `https://SITE.example/a`, `https://site.example:443/b`, and `https://site.example/c`. Use one robots.txt route on `https://site.example/robots.txt`, answering `"User-agent: *\nDisallow: /b\n"`. Use page routes on `https://site.example/a`, `/b`, and `/c`, with `html(...)` bodies of at least 600 characters. Assert:
    - the robots route was called once;
    - the `/b` route was not called;
    - two `ItemContext` rows exist, for `/a` and `/c`.
  - `test_failed_request_on_last_budget_unit_counts_as_read` (design D3, "Effect on progress"). Links `https://docs.example/one` and `https://docs.example/two`, with `context_fetches_per_run=2` (see `test_budget_spent_on_robots_marks_attempted_item_none`).
    - robots.txt answers 404, and `/one` answers 404.
    - `/two` has a route that must not be called.

    Assert:
    - `(context_total, context_done) == (2, 1)`;
    - the `/two` route was not called;
    - the item's `context_status` is `"none"`.

  Verify: run `uv run pytest tests/test_context_gather.py` in `backend/`. Before 3.2:
  - the two redirect tests fail, because the redirect target is requested;
  - the last-unit test fails with `context_done` 0;
  - the three-spellings test passes, because group 2 already normalizes the key. It is the runner-level check for the spec scenario;
  - every existing test passes.
- [ ] 3.2 Implement the `gather.py` part of D1 and D3 in `backend/src/catchup/context/gather.py`.
  - `fetch` calls `safe_fetch(..., allow=robots.allowed)`, and lets `BudgetExhausted` propagate. Remove its own robots check and its budget checks.
  - Wrap each item's link and comment fetches in one `try … except BudgetExhausted`. Keep the rows already added, then store captured replies, run the deleted-item check, and always run the status block.
  - The comment block keeps today's feed fallback in this group. Make sure its `except Exception` does not catch `BudgetExhausted` (design D3, "Extraction handlers").
  - Remove `EXHAUSTED`, `attempted`, `exhausted`, and the `elif`. Keep the skip for unreached items at the top of the loop.

  Verify:
  - the 3.1 tests pass, and `uv run pytest` passes in `backend/`, with no existing test changed;
  - `grep -n "EXHAUSTED\|attempted\|exhausted\|budget\[0\]" backend/src/catchup/context/gather.py` shows one line: the skip at the top of the loop;
  - mutations, recorded as in 1.2:
    - (G1) In `fetch`, return `None` on `BudgetExhausted`: `test_comment_feed_budget_cutoff_keeps_link`, because `context_done` becomes 3.
    - (G2) Treat any `FetchError` that leaves the budget at 0 as `BudgetExhausted` (the old translation): `test_failed_request_on_last_budget_unit_counts_as_read`.
    - (G3) Remove the skip for unreached items: `test_budget_leaves_unreached_items_ungathered_and_retries_do_not_refetch`.
    - (G4) Do not pass `allow` (call `robots.allowed(url)` once before `safe_fetch`, as today): both redirect tests.

  In `README.md`, change "Context fetches honor each site's robots.txt." to say that this includes the sites that links redirect to. `tests/test_readme_context.py` must still pass.

## 4. Comment replies: one markup check, set lookup (D4, D5)

- [ ] 4.1 Write the failing tests.

  In `backend/tests/test_context_comments.py`:
  - `test_feed_function_is_called_only_without_comment_markup`.
    - With `page(comment("one", "Writer", "Reply.", classes="bypostauthor"))` and a `fetch_feed` that records its calls, assert that the result is `["Reply."]` and that `fetch_feed` was not called.
    - With a page that has no comment markup, and a `fetch_feed` that returns a feed with one entry by "Writer" (reuse the feed shape from `test_comment_feed_fallback_skips_pingbacks_and_other_authors`), assert that it was called once and that the reply came from the feed.

  - `test_unparseable_feed_entry_is_skipped`. A page with no comment markup, and a feed with two entries by "Writer": the first summary is `<!-- c -->`, the second is "Real reply.". Assert that `author_replies(page_bytes, "Writer", feed)` returns `["Real reply."]`. Today it raises `ParserError`.
  - `test_empty_page_counts_as_no_comment_markup`. `author_replies(b"", "Writer", feed)` and `author_replies(b"   ", "Writer", feed)`, with the same one-entry feed, both return that entry's reply. Today both raise `AttributeError` (design, probes).

  In `backend/tests/test_context_gather.py`:
  - `test_unparseable_post_page_falls_back_to_comment_feed` (design D4, "Effect"). Use `setup(environment, [], comments=1)`. Set `entry_author` to "Writer" and `comment_feed_url` to `https://s0.example/comments/feed`, as in `test_comment_feed_fallback_counts_extra_fetch_and_saves_named_reply`.
    - The post page answers 200 with an empty body.
    - The feed answers with the same feed as that test.

    Assert:
    - the feed route was called once;
    - one `ItemContext` row with ref `A1` exists;
    - `(context_total, context_done) == (2, 2)`.

  Verify: run `uv run pytest tests/test_context_comments.py tests/test_context_gather.py` in `backend/`. Before 4.2:
  - the feed-function test fails on the unknown `fetch_feed` argument, the empty-page test fails with `AttributeError`, and the feed-entry test fails with `ParserError`;
  - the gather test fails, because the feed is not requested;
  - every existing test passes.
- [ ] 4.2 Implement D4 and D5.
  - In `backend/src/catchup/context/comments.py`, add `fetch_feed`, catch `lxml.etree.ParserError` instead of `html.ParserError`, skip feed entries whose summary cannot be parsed, and use a set for the four membership tests.
  - In `backend/src/catchup/context/gather.py`, pass a `fetch_feed` that counts the feed in `context_total` and `context_done`, and calls `fetch`. Remove the page parse and the XPath from `gather.py`.

  Verify:
  - the 4.1 tests pass, and `uv run pytest` passes in `backend/`, with no existing test changed;
  - `grep -n "comment ')" backend/src/catchup/context/gather.py` finds nothing;
  - mutations, recorded as in 1.2:
    - (C1) Call `fetch_feed` even when the page has comment markup: `test_feed_function_is_called_only_without_comment_markup`.
    - (C2) Leave out the `context_total` increase in `gather.py`'s `fetch_feed`: `test_comment_feed_fallback_counts_extra_fetch_and_saves_named_reply`.
    - (C4) Restore `html.ParserError` in the `except` clause: `test_empty_page_counts_as_no_comment_markup` and `test_unparseable_post_page_falls_back_to_comment_feed`.
    - (C3) Check the author before calling `fetch_feed`: `test_comment_feed_budget_cutoff_keeps_link`, because its item has no `entry_author` and its counts become `(2, 2)`.
    - (C5) Let an unparseable feed entry raise again: `test_unparseable_feed_entry_is_skipped`.
  - Timing note for the report: build a page with 2,000 sibling comments in a scratch script outside the repository, and time `author_replies` on it before and after the set change. Record both times. Do not commit the script.

## 5. Checks and report

- [ ] 5.1 Run the full checks:
  - `uv run pytest` in `backend/` (record the count);
  - `DO_NOT_TRACK=1 openspec validate refactor-context-fetch-budget-and-robots --strict`.

  Do not run `docker build` or `scripts/docker-smoke.sh`: at `--auto medium` the smoke script is refused, and Claude Code runs both at review.

  Write the commands and their real results to `docs/process/test-report-refactor-context-fetch-budget-and-robots.md`:
  - map each scenario of the modified requirement to its tests; the unchanged scenarios map to the existing tests;
  - record mutations S1–S4, O1–O4, G1–G4, and C1–C5, and their results;
  - record the timing note from 4.2;
  - list the Docker smoke and the live comparison from design "Migration Plan" as not performed (Claude Code runs them at review).

  Add your entry to `docs/process/ai-usage-log.md` after the latest entry, with a faithful prompt excerpt. Leave out the session id; Claude Code adds it at review. The Docker results, if any, come from Claude Code; attribute them to Claude Code, not to the user.

  Verify: every command that ran passes, and the report has the actual numbers.
