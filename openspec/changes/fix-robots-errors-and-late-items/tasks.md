# Tasks

Implementer notes:
- **Read first.** Read `proposal.md`, `design.md` (D1, D2, and the probe findings under "Context"), and both spec deltas under `specs/`. If something looks wrong or contradictory, stop and report instead of redesigning.
- **Work test-first with the `tdd` skill** (D-016). For each group, first write its tests, run them, and watch them fail for the stated reason. Then implement until they pass. The seams are named in each task, and they count as agreed: `respx` routes, the `public_dns` fixture, `monkeypatch` of `socket.getaddrinfo`, and the helpers in `backend/tests/test_digest_runner.py` and `backend/tests/test_context_gather.py` (`environment`, `seed`, `setup`, `html`, `stub_collection`, `execute`).
- **Test rules.**
  - No real network and no real sleeps.
  - Use `respx.mock(assert_all_mocked=True, ...)` as the existing tests do. `assert_all_called` defaults to `True` in respx. Any test that defines a route and expects it not to be called must pass `assert_all_called=False`, or it fails with "some routes were not called" after the fix.
  - An `assert` inside a respx `side_effect` has no effect during a run: `gather.fetch` swallows every exception (`context/gather.py:67-69`). Record values in a list inside the side effect, and assert on them after `execute`.
  - `tests/conftest.py` replaces `catchup.net.safe_fetch.sleep` with a function that raises. A test that makes `safe_fetch` wait (a `Retry-After` of 10 seconds or less) errors instead.
  - Change no existing test except two in `test_context_robots.py`: replace `test_failed_robots_request_allows`, and extend the parameters of `test_missing_or_restricted_robots` (task 1.1). The probe found that no other backend test depends on the old rule.
  - Do not edit `docs/process/decision-log.md` or `docs/process/requirements-changes.md`. Claude Code wrote D-030 and the requirements row with the plan.
- **Out of scope:**
  - `context/gather.py`, `net/safe_fetch.py`, and the API modules;
  - `frontend/` and `extension/`;
  - migrations, models, and dependency versions.
- **Commits.** Commit after each task group. Do not push, tag, or open a PR.

## 1. An unreachable robots.txt refuses its site for the run (#76)

- [x] 1.1 Write the failing tests.

  In `backend/tests/test_context_robots.py`:
  - Replace `test_failed_robots_request_allows` with `test_unreachable_robots_disallows`. It is parametrized over three `side_effect`s for the robots.txt route: `httpx.ConnectTimeout`, `httpx.ConnectError`, and `httpx.ReadTimeout`. It asserts that `RobotsCache(budget=[2]).allowed("https://site.example/post")` is `False`.
  - Add `test_unresolvable_robots_host_disallows`. Inside the test, `monkeypatch` replaces `socket.getaddrinfo` with a function that raises `socket.gaierror`. Use `respx.mock(assert_all_mocked=True, assert_all_called=False)` with a robots.txt route. Assert that `allowed(...)` is `False`, and that no request was sent: the route was not called, and the budget is unchanged (the address check runs before the budget is used).
  - Extend the parameters of `test_missing_or_restricted_robots`:
    - add `(410, True)`, `(429, True)`, `(500, False)`, `(502, False)`, and `(503, False)`;
    - keep `(404, True)`, `(401, False)`, and `(403, False)`.
  - Add `test_rate_limited_server_error_disallows`. robots.txt answers 503 with `Retry-After: 120`. Assert `False`. Keep the delay above 10 seconds, so `safe_fetch` does not wait (see the test rules).
  - Add `test_unreadable_robots_response_disallows`, parametrized over two responses:
    - a `302` with no `Location` header;
    - a `200` whose body is 512 KiB + 1 byte.

    Assert `False` for both.
  - Add `test_unreachable_robots_is_cached_for_the_run`. robots.txt answers 503. Call `allowed` for `https://site.example/a` and `https://site.example/b`. Assert:
    - both calls return `False`;
    - the robots.txt route was called once;
    - the budget went from 5 to 4.

  In `backend/tests/test_context_gather.py`:
  - Add `test_robots_server_error_skips_the_sites_pages` (spec scenario "robots.txt answers a server error"). Use `setup` with links `https://docs.example/a` and `https://docs.example/b`, and `stub_collection(monkeypatch)`. Use `respx.mock(assert_all_mocked=True, assert_all_called=False)`. robots.txt answers 503. Assert:
    - the robots.txt route was called once, and neither page route was called;
    - the run's `status` is `"succeeded"`;
    - no `ItemContext` row exists, and the item is `delivered`.
  - Add `test_unreachable_robots_keeps_other_sites` (spec scenario "robots.txt cannot be reached"). Use `setup` with links `https://docs.example/a` and `https://other.example/b`, and `stub_collection(monkeypatch)`. Use `respx.mock(assert_all_mocked=True, assert_all_called=False)`. The `docs.example` robots.txt raises `httpx.ConnectTimeout`. The `other.example` robots.txt answers 404, and `https://other.example/b` answers `html("Other", "Other context " * 40)`. Assert:
    - the `docs.example/a` route was not called;
    - exactly one `ItemContext` row exists, with URL `https://other.example/b`.

  The spec scenario "robots.txt missing" maps to the existing `test_runner_stores_three_links_in_order_and_ignores_tags` (robots.txt 404, pages read). Do not add a test for it.

  Verify: run `uv run pytest tests/test_context_robots.py tests/test_context_gather.py` in `backend/`. Before 1.2, the network-error, DNS, 5xx, 503 `Retry-After`, unreadable-response, cache, and both gather tests fail because `allowed` returns `True`, or because a page route was called. The 404, 410, 429, 401, and 403 cases pass. No test may fail because of a mock error.
- [x] 1.2 Implement design D1 in `backend/src/catchup/context/robots.py`.
  - In the `FetchError` branch, cache `True` only when `exc.status_code` is in 400–499 and is not 401 or 403. Otherwise cache `False`.
  - Change nothing else in the file.

  In `README.md`, after "Context fetches honor each site's robots.txt.", add one sentence: when a site's robots.txt cannot be read because of a server error or a network failure, CatchUp reads no page from that site in that run.

  Verify:
  - the 1.1 tests pass, and `uv run pytest` passes in `backend/`.
  - Each mutation below makes at least the named tests fail. Run each one, watch the tests fail, and restore the code. Record each mutation and the tests that failed in the test report (task 3.1).
    - (R1) Restore the old rule, `exc.status_code not in (401, 403)`: the network-error, DNS, 5xx, unreadable-response, and cache tests, and both gather tests.
    - (R2) Allow when there is no status (`code is None or ...`): `test_unreachable_robots_disallows`, `test_unresolvable_robots_host_disallows`, `test_unreachable_robots_keeps_other_sites`.
    - (R3) Drop the 401/403 exception: the 401 and 403 cases.
    - (R4) Allow only 404 (`code == 404`): the 410 and 429 cases.
    - (R5) Do not cache the `False` result: `test_unreachable_robots_is_cached_for_the_run`.

## 2. Items recorded during the context pass wait for the next run (#70)

- [ ] 2.1 Write the failing tests in `backend/tests/test_context_gather.py`.
  - Add `test_page_saved_during_context_pass_waits_for_next_run` (spec scenario "Page saved while linked pages are read").
    - Setup:
      - `setup(environment, [("https://docs.example/page", "Page")])` and `stub_collection(monkeypatch)`;
      - create an extension token with the same `POST /api/settings/extension-tokens` call that `capture_with_context` makes. Copy the call; do not call `capture_with_context`, because it seeds the database again.
    - The `https://docs.example/page` route uses a `side_effect` function. It saves a capture through `environment.post("/api/captures", ...)`, with:
      - the URL `https://blog.example/post`, the title "Late post", and the text "Late text";
      - one link, `https://ref.example/a`;
      - the token header and the `Origin: chrome-extension://abcdefghijklmnop` header.

      It appends the response's status code and its JSON `id` to a list, and then returns `html("Page", "Substantial text " * 30)`. It must not assert (see the test rules).
    - Mock robots.txt for `docs.example` and `ref.example` as 404. `https://ref.example/a` answers `html("A", "Ref text " * 40)`.
    - Use one `respx.mock(assert_all_mocked=True, assert_all_called=False)` block around both `execute` calls.
    - Run `execute(environment)` once and assert:
      - the side effect ran once, and the capture's status was 201. Use the recorded id below;
      - the run's `status` is `"succeeded"`, and `digest_item_count` is 1;
      - the seeded item is delivered;
      - the capture is still `pending`, with `context_status` `None`;
      - the `ref.example/a` route was not called;
      - no `DigestItem` has the capture's id (import `DigestItem` from `catchup.models`).
    - Run `execute(environment)` again and assert:
      - the run's `status` is `"succeeded"`;
      - the `ref.example/a` route was called once;
      - the capture is `delivered`, with `context_status` `"gathered"`, and one `ItemContext` row with URL `https://ref.example/a`;
      - exactly one `DigestItem` has the capture's id.
  - Add `test_item_recorded_during_source_checks_is_included`. `seed(environment)` with one item and no links. Call `stub_collection(monkeypatch, on_check=...)`, where `on_check` adds a second pending feed item to the seeded source in its own session and commits. Give the item the same fields as `seed`: `identity_key="late"`, its own link, a title, `content_text`, `content_origin="feed"`, and `state="pending"`. Assert that the run's `status` is `"succeeded"`, and that `digest_item_count` is 2.

  Verify: run `uv run pytest tests/test_context_gather.py` in `backend/`. Before 2.2, `test_page_saved_during_context_pass_waits_for_next_run` fails on its first-run assertions: today the capture is delivered in the first run (probe). `test_item_recorded_during_source_checks_is_included` passes before 2.2. It guards the cutoff's position, and must still pass after 2.2.
- [ ] 2.2 Implement design D2 in `backend/src/catchup/digest/runner.py`.
  - Immediately before `gather_context(...)`, read `max(Item.id)` in a short session (`0` when there is none).
  - Add `Item.id <= cutoff` to the pending query that feeds `select_pending`.
  - Change nothing else.

  Verify:
  - the 2.1 tests pass, and `uv run pytest` passes in `backend/`.
  - Each mutation below makes at least the named test fail. Run each one, watch the test fail, and restore the code. Record each mutation and the result in the test report.
    - (L1) Remove the filter: `test_page_saved_during_context_pass_waits_for_next_run`.
    - (L2) Read the cutoff after `gather_context(...)`: `test_page_saved_during_context_pass_waits_for_next_run`.
    - (L3) Read the cutoff before the source checks, at the `collecting` stage: `test_item_recorded_during_source_checks_is_included`.
    - (L4) Use `<` instead of `<=`: `test_page_saved_during_context_pass_waits_for_next_run`, because the seeded item is then left out.

## 3. Checks and report

- [ ] 3.1 Run the full checks:
  - `uv run pytest` in `backend/` (record the count);
  - `DO_NOT_TRACK=1 openspec validate fix-robots-errors-and-late-items --strict`;
  - `docker build -t catchup:fix-robots-local .` from the repository root, then `scripts/docker-smoke.sh catchup:fix-robots-local`.

    If Docker is not available, or these commands are refused at your permission level, record that in the report and continue. Claude Code runs them at review. Remove the `catchup:fix-robots-local` image when the smoke script has finished. Do not remove or prune any other image, container, or volume.

  Write the commands and their real results to `docs/process/test-report-fix-robots-errors-and-late-items.md`:
  - map each scenario of the two modified requirements to its tests; the unchanged scenarios map to the existing tests;
  - record the mutations R1–R5 and L1–L4, and their results;
  - list the live check from design "Migration Plan" as not performed (Claude Code runs it at review).

  Add your entry to `docs/process/ai-usage-log.md` after the latest entry, with a faithful prompt excerpt. Leave out the session id; Claude Code adds it at review.

  Verify: every command that ran passes, and the report has the actual numbers.
