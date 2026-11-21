# Tasks

Implementer notes:
- **Read first.** Read `proposal.md`, all of `design.md` (Context, D1–D6, Risks, Evidence, Testing), and both spec deltas under `specs/`. If something looks wrong or contradictory, stop and report instead of redesigning.
- **Work test-first with the `tdd` skill** (D-016). In each group, first write the group's tests, run them, and watch each fail for the reason the task gives. Then change the code. The seams are named in each task, and they count as agreed. They are:
  - from `backend/tests/test_digest_runner.py`: `execute(environment)`, `seed`, `stub_collection(monkeypatch, on_check=…)`, `stub_outcomes`, `seed_x_accounts`, and `FakeModel`;
  - from `backend/tests/test_context_gather.py`: `setup`, `html`, and the `public_dns` fixture;
  - respx routes with `side_effect` functions;
  - `HostSpacer(min_interval=…, clock=…, sleep=…)`, `RobotsCache`, `origin`, and `reachable_reads`;
  - `catchup.digest.runner.monotonic`, `catchup.digest.runner.caption_pass`, `catchup.digest.runner.HostSpacer`, and `catchup.context.gather.CONTEXT_WORKERS`, replaced with `monkeypatch`;
  - `mockPage` in `frontend/src/pages/Home.test.tsx`.
- **Test rules:**
  - **No real network.** Use `respx.mock(assert_all_mocked=True, …)`, and the `public_dns` fixture or the same `socket.getaddrinfo` stub.
  - **Concurrency tests** measure overlap inside respx side effects, with a `threading.Lock` and short real sleeps (50–300 ms). They never assert a wall-clock total for a whole run.
  - **Change no existing test,** except where a task says so.
- **Mutations.** For each named mutation, apply it alone, run the named tests, record the result, and restore the code exactly. Compare with `git diff` after restoring. The design marks one mutation, B1, as not reliably killable. Run it anyway, and record what happened.
- **Environment:**
  - **Backend.** Run `uv run --offline pytest …` in `backend/`. Do not add or upgrade packages.
  - **Frontend.** Use Node 22.17.1 with `export PATH="$HOME/.nvm/versions/node/v22.17.1/bin:$PATH"`. Then run `npm ci --offline --no-audit --no-fund` in `frontend/`. It installs the locked packages from the local npm cache. If it fails, stop and report. Do not change `package.json` or `package-lock.json`.
- **Do not run** `docker build` or `scripts/docker-smoke.sh`. Claude Code runs them at review.
- **Out of scope:**
  - the source checks, the caption pass, and the summary and grouping code, apart from the stage timing in `runner.py`;
  - `sources/discovery.py`;
  - the extension;
  - any setting for the number of items read at once;
  - the status-region text.
- **Do not edit:**
  - `proposal.md`, `design.md`, or the spec deltas;
  - `docs/process/decision-log.md` or `docs/process/requirements-changes.md`. Claude Code wrote D-036 and the requirements row with the plan.
- **OpenSpec.** Prefix every OpenSpec CLI call with `DO_NOT_TRACK=1`.
- **Commits.** Commit after each task group. Do not push, tag, or open a PR.

## 1. Run record: stage durations and a fixed source count (D1, D2)

- [x] 1.1 Write these tests and watch them fail. The model and migration tests fail on the missing columns, the API tests on the missing `stage_seconds` key or on the live count.

  **In `backend/tests/test_db.py`,** follow `test_x_migration_upgrades_0006_and_preserves_other_sources_on_downgrade`:
  - **`test_run_progress_migration_fills_sources_total_and_downgrades`.**
    - Migrate a database to `0007_x_accounts`.
    - Insert two sources, and two runs: run A with two `source_checks` rows, and run B with none.
    - Upgrade to head. `sources_total` is 2 for A and 0 for B, and `stage_seconds` is NULL for both.
    - Downgrade to `0007_x_accounts`. Neither column is left, and both runs and all checks are kept.

  **In `backend/tests/test_digest_runner.py`:**
  - **`test_stage_durations_are_saved_for_each_stage`.**
    - `seed(environment)`. Replace `catchup.digest.runner.monotonic` with `lambda: clock[0]`, where `clock = [100.0]`. Use `raising=False`, so the test reaches the run before the code exists, and fails on the missing `stage_seconds` key.
    - Use `stub_collection(monkeypatch, on_check=…)`, with an `on_check` that adds 2.0 to the clock.
    - Wrap these with `monkeypatch`, calling the original each time, then adding to the clock:
      - `catchup.digest.runner.caption_pass`: add 0.5;
      - `catchup.digest.runner.gather_context`: add 7.0;
      - `catchup.digest.runner.summarize_items`: add 3.0;
      - `catchup.digest.runner.group_items`: add 1.0, and return the original's result.
    - The result's `stage_seconds` equals `{"checks": 2.0, "captions": 0.5, "context": 7.0, "summaries": 3.0, "grouping": 1.0}`.
  - **`test_failed_run_keeps_durations_of_finished_stages`.** `seed(environment)`, `stub_collection`, and a `FakeModel([AuthFailed("bad key")])`. The run fails, and the keys of `stage_seconds` are exactly `{"checks", "captions", "context"}`.
  - **`test_run_with_nothing_to_summarize_records_three_stages`.** `seed(environment, count=0)` and `stub_collection`. The status is `no_new_content`, and the keys of `stage_seconds` are exactly `{"checks", "captions", "context"}`.
  - **`test_sources_total_stays_fixed_when_a_source_is_added_during_the_run`.** Follow the background-run test that ends at about line 1160, with its `entered` and `release` events.
    - Use two sources, and hold the first check.
    - While it is held, insert a third `Source` row directly with a session.
    - `/api/digest-runs/active` has `sources_total == 2`.
    - Release the check. The finished run has `sources_total == 2` and two `source_checks`.
  - **`test_source_added_before_the_run_thread_starts_is_counted`.**
    - `seed(environment)` and `stub_collection`.
    - Call `start_run(environment.app, background=False)`.
    - Insert a second `Source` row.
    - Call `run_digest(environment.app, run.id)`. The run has `sources_total == 2` and two `source_checks`.

    This passes today, because the live count is also 2. It guards N2.
  - **`test_sources_total_counts_x_accounts`.** `seed(environment)` with one feed source, `stub_collection(monkeypatch)`, then `seed_x_accounts(environment, ("a",))`, with no X token, so the X check is saved as failed. `sources_total` is 2. This passes today, because the live count includes X accounts. It guards the stored count.

  The existing `sources_total` assertions in `test_digest_runner.py` (lines 199, 305, 443, 465, 515, and 1151) must keep passing unchanged.

- [x] 1.2 Implement D1 and D2:
  - `DigestRun.stage_seconds` and `DigestRun.sources_total` in `backend/src/catchup/models.py`;
  - migration `backend/src/catchup/migrations/versions/0008_run_progress.py`, with `revision = "0008_run_progress"` and `down_revision = "0007_x_accounts"`;
  - in `backend/src/catchup/digest/runner.py`: the `monotonic` import, the stage helper, and the two `sources_total` writes;
  - in `run_detail`: `stage_seconds` and `sources_total`;
  - in `backend/tests/test_db.py`, the only existing test edits of this group:
    - change `"0007_x_accounts"` to `"0008_run_progress"` in the four head-revision assertions (lines 71, 240, 280, and 421);
    - add `assert (migrations / "versions" / "0008_run_progress.py").is_file()` to `test_migrations_live_inside_package`, after its `0007` line.

  Verify that the tests of 1.1 pass, and that `uv run --offline pytest` passes in full.

  **Mutations,** each applied alone and run against the named tests:
  - **D1:** do not save `context`. Run the durations test.
  - **D2:** save every duration only after the save step. Run the failed-run test.
  - **N1:** `run_detail` counts the sources live again. Run the source-added test.
  - **N2:** `run_digest` does not overwrite the count from `start_run`. Run the before-the-thread test.
  - **M1:** the migration leaves `sources_total` at 0. Run the migration test.

## 2. Held items show "New items" when their source is checked (D5)

- [x] 2.1 Write these tests in `backend/tests/test_digest_runner.py`. Watch the first two fail with `no_new_items` seen during the run. The other three pass today, and guard H3 and H4.

  Each test wraps `catchup.digest.runner.caption_pass`, which runs right after the checks. Before calling the original, the wrapper records `(check.status, source.last_check_status)` for every `SourceCheck` of the run, joined with its source, in source-id order.
  `stub_collection` saves a check row but leaves `Source.last_check_status` unset. So the feed, podcast, and no-pending tests use `stub_outcomes(monkeypatch, {"Source 0": "no_new_items"})`, which sets both.
  - **`test_feed_with_held_items_shows_new_items_when_checked`.** `seed(environment)`, where the one item is pending, and `stub_outcomes(monkeypatch, {"Source 0": "no_new_items"})`.
    - The wrapper records `[("new_items", "new_items")]`.
    - The finished run's only check is `new_items`.
  - **`test_x_account_with_held_posts_shows_new_items_when_checked`.**
    - `seed(environment, sources=0)`, then `seed_x_accounts(environment, ("a",))`.
    - Add a pending `Item` to that X source: `identity_key="x:post:900"`, `link="https://x.com/a/status/900"`, `title="Held post"`, `content_text="Held post"`, `content_origin="feed"`, `state="pending"`.
    - Save an X token as in `test_complete_two_page_x_read_does_not_count_account_as_waiting`.
    - Mock `https://api.x.com/2/users/100/tweets` to answer `{"meta": {"result_count": 0}}`.
    - The wrapper records `[("new_items", "new_items")]`.
  - **`test_waiting_podcast_episode_keeps_no_new_items_when_checked`.** `seed(environment)`. Set the source's kind to `podcast`, and the item's `transcript_status` to `waiting`, with `discovered_at` now. Use `stub_outcomes(monkeypatch, {"Source 0": "no_new_items"})`. The wrapper records `[("no_new_items", "no_new_items")]`.
  - **`test_source_without_pending_items_keeps_no_new_items`.** `seed(environment, count=0)` and `stub_outcomes(monkeypatch, {"Source 0": "no_new_items"})`. The wrapper records `[("no_new_items", "no_new_items")]`.
  - **`test_failed_check_with_held_items_stays_failed`.** `seed(environment)` and `stub_outcomes(monkeypatch, {"Source 0": "failed"})`. The wrapper records `[("failed", "failed")]`.

- [x] 2.2 Implement `_show_held_items` in `backend/src/catchup/digest/runner.py`, and call it after each `check_one_source` call in both loops. Verify that the tests of 2.1 and the full backend suite pass.

  **Mutations:**
  - **H1:** no call in the feed loop. Run the feed test.
  - **H2:** no call in the X loop. Run the X test.
  - **H3:** count every pending item, without `select_pending`. Run the podcast test.
  - **H4:** also upgrade `failed` checks. Run the failed-check test.

## 3. Thread-safe host spacing, budget, and robots.txt (D3 `verdict` and `origin`, D4)

- [x] 3.1 Write these tests and watch each fail.

  **In `backend/tests/test_host_spacing.py`:**
  - **`test_other_hosts_do_not_wait_while_one_host_sleeps`.**
    - Build `HostSpacer(min_interval=1.0, sleep=blocking_sleep)` with the real clock. `blocking_sleep` sets a `threading.Event` called `entered`, then waits on another called `release`, up to 5 s.
    - Call `wait("https://a.example/1")` on the main thread.
    - Start a thread that calls `wait("https://a.example/2")`. It sleeps, and blocks on `release`. Wait for `entered` (up to 5 s) before the next step.
    - Then, on another thread, call `wait("https://b.example/1")`, and `join(timeout=1)`. That thread must have finished while `release` is still unset.
    - Finally set `release` and join the first thread.

    Today it fails because the one lock is held while host a sleeps.
  - **`test_same_host_waits_are_spaced_across_threads`.**
    - Use `HostSpacer(min_interval=0.2, sleep=time.sleep)` with the real clock. Pass `sleep` explicitly: the autouse fixture in `tests/conftest.py` makes the default sleep a no-op.
    - Three threads pass a `threading.Barrier(3)`, then call `wait("https://h.example/x")`, and each records `time.monotonic()` when `wait` returns.
    - Sorted, consecutive times differ by at least 0.19 s.

    This passes today, with the explicit sleep. It guards against mutation S2.

  **In `backend/tests/test_context_robots.py`:**
  - **`test_origin_ignores_case_and_default_port`.**
    - `origin("https://SITE.example:443/a") == origin("https://site.example/b") == "https://site.example"`;
    - `origin("http://site.example:8080/x") == "http://site.example:8080"`;
    - `origin("https://[2001:db8::1]/x") == "https://[2001:db8::1]"`.

    Import `origin` inside the test function, so the missing name fails only this test.
  - **`test_verdict_never_requests_and_reads_stored_rules`.** Use respx routes and the `getaddrinfo` stub from that file.
    - Before any `allowed` call, `verdict("https://site.example/private/x")` is `None`, and no route was called.
    - Then `allowed("https://site.example/ok")` reads robots.txt `User-agent: *\nDisallow: /private\n` once.
    - After that, `verdict(".../private/x")` is `False` and `verdict(".../ok")` is `True`, and the robots.txt route's `call_count` is still 1.
    - For an origin whose robots.txt answers 503 after `allowed`, `verdict` is `False`. For one that answers 404, it is `True`.
  - **`test_robots_is_read_once_when_two_threads_ask_at_once`.**
    - `RobotsCache(budget=[10])`.
    - The robots.txt route's side effect sleeps 0.2 s, and answers 404.
    - Two threads pass a `threading.Barrier(2)`, then call `allowed("https://site.example/a")` and `allowed("https://SITE.example/b")`.
    - Both return `True`, and the route's `call_count` is 1. Today it is 2.

  **In `backend/tests/test_safe_fetch.py`:**
  - **`test_budget_units_are_taken_once_per_request_across_threads`.**
    - `budget = [5]`.
    - Four threads each call `safe_fetch` three times on their own host, through one regex route answering 200, and catch `BudgetExhausted`.
    - Exactly 5 calls succeed, the route's `call_count` is 5, and `budget == [0]`.

    It may pass today. It documents the rule, and is the test for mutation B1.

- [x] 3.2 Implement:
  - in `backend/src/catchup/net/host_spacing.py`: a lock per host;
  - in `backend/src/catchup/net/safe_fetch.py`: the locked unit take;
  - in `backend/src/catchup/context/robots.py`: the module-level `origin(url)`, a lock per origin in `allowed`, and `RobotsCache.verdict(url)`.

  Verify that the tests of 3.1, the existing tests in these three files, `test_context_gather.py`, and the full backend suite pass.

  **Mutations:**
  - **S1:** one lock for every host, held while sleeping (today's code). Run the other-hosts test.
  - **S2:** compute the delay under the lock, release it, sleep, then store the time. Run the same-host test.
  - **R1:** no per-origin lock. Run the two-threads test.
  - **R2:** `verdict` calls `allowed`. Run the verdict test.
  - **B1:** no budget lock. Run the budget test. Expected: it survives, and is recorded as verified by review and probe P3.

## 4. The linked-page total (D3)

The context pass still reads one item after another in this group.

- [x] 4.1 Write these tests in `backend/tests/test_context_gather.py`, and watch them fail.

  - **`test_reachable_reads` (parametrized).** Call `reachable_reads(urls, verdict, units)`. `verdict` is a dict lookup that returns `None` for a missing URL. A, B, and C are `https://a.example/`, `https://b.example/`, and `https://c.example/`.

    | Case | URLs | Verdicts | Units | Expected |
    | --- | --- | --- | --- | --- |
    | a | A1, A2, B1, B2, C1, C2 | none | 5 | 3 |
    | b | the same | none | 0 | 0 |
    | c | A1, A2 | A1 and A2 `True` | 1 | 1 |
    | d | A1, A2, A3 | A1 `True`, A2 `False`, A3 `True` | 1 | 2 |
    | e | A1, B1, A2 | none | 3 | 1 |
    | f | `https://SITE.example/a`, `https://site.example:443/b` | none | 3 | 2 |
    | g | (empty) | none | 4 | 0 |

    Import `reachable_reads` inside the test function, so the missing name fails only this test.
  - **`test_total_starts_at_what_the_limit_can_read`** (the spec scenario "Per-run limit lower than the links").
    - `setup(environment, …)` with six links: `https://a.example/1`, `https://a.example/2`, `https://b.example/1`, `https://b.example/2`, `https://c.example/1`, `https://c.example/2`.
    - `stub_collection`, with `context_fetches_per_run=5`.
    - Every robots.txt answers 404.
    - Every page answers `html(…, "Linked text " * 40)`. The side effect of `https://a.example/1` records the run's `context_total` from a new session.
    - The recorded total is 3, and the result's `(context_total, context_done)` is `(3, 3)`.
    - Neither `c.example` route nor `https://b.example/2` was called.

    Today the recorded total is 6.
  - **`test_links_after_the_cap_leave_the_total`.**
    - Eight links on `https://docs.example/0` … `/7`. robots.txt answers 404.
    - Every page answers `html(…, "Long linked text " * 300)`, which is over 3,000 characters after extraction.
    - The pass reads six pages. The sixth fills the 16,000-character cap, and `/6` and `/7` are never requested.
    - The result's `(context_total, context_done)` is `(6, 6)`. Today it is `(8, 6)`.
  - **`test_reads_of_a_deleted_item_leave_the_total`.**
    - Set `catchup.context.gather.CONTEXT_WORKERS` to 1 with `monkeypatch.setattr(…, raising=False)`, so the test keeps its meaning in group 5.
    - Two items on two sources, each with one link on its own site: item 1 on `https://one.example/p`, and item 2 on `https://two.example/p`.
    - The side effect of item 1's page deletes item 2's source, then answers with text.
    - The run's `context_total == context_done` at the end, and `two.example` was never requested.
  - **`test_total_is_committed_with_each_read`.**
    - Two links on `https://docs.example/one` and `/two`. robots.txt answers 404.
    - The side effect of `/two` records `(context_done, context_total)` from a new session.
    - The recorded value is `(1, 2)`.

    This passes today. It pins that both numbers are committed together, before the next request.
  - **`test_read_cut_by_the_limit_leaves_the_total_after_the_next_item`.** Added by Claude Code after Droid's first run stopped at T4. In the four changed tests below, no progress commit follows the read that the limit cuts, so they cannot see that read staying in progress.
    - Set `catchup.context.gather.CONTEXT_WORKERS` to 1 with `monkeypatch.setattr(…, raising=False)`.
    - `seed(environment, count=2, sources=2)`, `stub_collection`, and `context_fetches_per_run=3`.
    - Item 1 links to `https://a.example/1` and `https://b.example/1`. Item 2 links to `https://c.example/1`.
    - robots.txt answers 404 on `a.example` and `b.example`. `https://a.example/1` answers `html("A", "Linked text " * 40)`.
    - The result's status is `"succeeded"`, its `(context_total, context_done)` is `(1, 1)`, and neither `https://b.example/1` nor any `c.example` route was called.

    It fails before 4.2. With 4.2's code it passes, and under T4 it fails with `(2, 1)`.
  - **Change exactly these existing expectations,** because they pin the old total. No other assertion changes:
    - in `test_refused_links_count_as_read_once_budget_is_used`, `(3, 2)` becomes `(2, 2)`, and `(1, 1)` stays;
    - in `test_failed_request_on_last_budget_unit_counts_as_read`, `(2, 1)` becomes `(1, 1)`;
    - in `test_comment_budget_cutoff_keeps_link_without_requesting_post`, `(2, 1)` becomes `(1, 1)`. The post page on `s0.example` would need its robots.txt and the page, with no unit left;
    - in `test_comment_feed_budget_cutoff_keeps_link`, `(3, 2)` becomes `(2, 2)`, because the comment feed is added and then dropped by the limit.

    Run all four and watch them fail before 4.2.

- [x] 4.2 Implement `reachable_reads` and `ContextProgress` in `backend/src/catchup/context/gather.py`, as D3 describes, and use them in the existing one-item-at-a-time loop. They replace `progress()` and the `context_total` sum. Verify that the tests of 4.1, all of `test_context_gather.py`, and the full backend suite pass.

  **Mutations:**
  - **T1:** the initial total is the old sum of planned reads. Run the starts-at test.
  - **T2:** `reachable_reads` charges 1 unit for an origin not yet asked. Run cases a and e. Case f guards the origin normalization, not T2.
  - **T3:** the cap does not drop the remaining links. Run the cap test.
  - **T4:** `BudgetExhausted` does not drop the item's reads. Run the four changed tests and `test_read_cut_by_the_limit_leaves_the_total_after_the_next_item`. The four changed tests pass under T4 (recorded); the new test must fail.
  - **T5:** a read that robots.txt is known to refuse costs 1 unit. Run case d.
  - **T6:** `reachable_reads` skips an unaffordable read, and goes on with the next. Run case e.
  - **T7:** a deleted item's reads are not dropped. Run the deleted-item test.

## 5. Up to 4 items at the same time (D4, D6)

- [x] 5.1 Write these tests. Watch the four-items test and the README test fail. The other three pass today, and guard mutations of 5.2.

  **In `backend/tests/test_context_gather.py`:**
  - **`test_four_items_are_read_at_the_same_time`** (the spec scenario "Items on different sites").
    - `seed(environment, count=8)`. Give item n one link, `https://h{n}.example/p`, and `stub_collection`.
    - robots.txt answers 404 through one regex route.
    - The pages' regex route has a side effect:
      1. under a lock, it raises an in-flight counter and updates the peak;
      2. it releases the lock and sleeps 0.2 s;
      3. under the lock, it lowers the counter;
      4. it answers with text.
    - The peak is exactly 4, and the run succeeds with `(context_total, context_done) == (8, 8)`. Today the peak is 1.
  - **`test_two_items_on_one_site_share_robots_and_spacing`** (the spec scenario "Two items on one site").
    - Replace `catchup.digest.runner.HostSpacer` with `lambda: HostSpacer(min_interval=0.3, sleep=time.sleep)`. The explicit sleep is needed, because `tests/conftest.py` makes the default sleep a no-op.
    - Two items, with links `https://site.example/a` and `https://site.example/b`.
    - robots.txt's side effect sleeps 0.2 s, and answers 404.
    - Each page's side effect records `time.monotonic()`, and answers with text.
    - robots.txt `call_count` is 1, and the two page times differ by at least 0.29 s.

    Create the items with `seed(environment, count=2)`, and set each item's `entry_links`. This passes today, when items are read one after another. It guards R1 and S2 once the pool runs.
  - **`test_limit_holds_with_items_read_at_the_same_time`** (the spec scenario "Per-run limit with items read at the same time").
    - Eight items, each with three links on its own host. `context_fetches_per_run=10`. robots.txt answers 404.
    - Pages answer with text, after a 50 ms sleep.
    - The sum of `call_count` over all routes, robots.txt included, is at most 10.
    - The run succeeds, and `context_total == context_done`.
  - **`test_unexpected_item_error_fails_the_run`.**
    - Replace `catchup.context.gather.related_links` with a wrapper. When its fourth argument is 1, which is the check after a fetch (`gather.py:89`), it raises `RuntimeError`. Otherwise it calls the original.
    - Use four items, each with one link on its own host, and pages that answer with text.
    - The run's status is `failed`, and its `error_kind` is `run_failed`.

    This passes today, because the error reaches `run_digest`. It guards W3.

  **In `backend/tests/test_readme_context.py`:** add the three phrases of D6 to the tuple, and watch it fail.

- [x] 5.2 Implement the pool in `gather_context` with `CONTEXT_WORKERS = 4`, as D4 describes. Read `CONTEXT_WORKERS` from the module each time `gather_context` runs, not as a default argument, so that `monkeypatch` changes it. Add the README paragraph of D6 after "(including robots.txt)." in `README.md`.

  Then run `test_context_gather.py` and `test_digest_runner.py`. When an existing test fails only because items now run at the same time, for example because it asserts which of two items got context near the limit:
  - set `CONTEXT_WORKERS` to 1 in that test with `monkeypatch`;
  - change nothing else;
  - list it in the test report with its failing assertion.

  Expected examples:
  - `test_budget_leaves_unreached_items_ungathered_and_retries_do_not_refetch`, which pins `[gathered, None]`. With 4 workers, item 2 starts while units remain;
  - `test_second_item_keeps_partial_context_in_successful_digest`, whose result depends on which item takes the last of the 3 units.

  A failure for any other reason is a bug: diagnose it with the `diagnosing-bugs` skill.

  Verify that the tests of 5.1, the full backend suite, and the README test pass.

  **Mutations:**
  - **W1:** `CONTEXT_WORKERS = 1`. Run the four-items test.
  - **W2:** `CONTEXT_WORKERS = 8`. Run the four-items test.
  - **W3:** catch and log exceptions from a task instead of re-raising them. Run the item-error test.
  - **R1 again,** with the pool. Run the two-items test.
  - **Doc:** remove the README paragraph. Run the README test.

## 6. The run bar shows linked-page progress from the start of the context pass (D2)

- [x] 6.1 In `frontend/src/pages/Home.test.tsx`, replace `keeps source progress during the source checks despite planned linked pages`. It pins a state that the backend can no longer produce: `context_total > 0` while sources are still being checked.

  The new test is **`shows linked-page progress after a source is deleted during the checks`.**
  - Use `mockPage({ run: { ...run, context_total: 20, context_done: 7 } })`, where `run` has 2 of its 3 sources checked.
  - The progress bar named `Linked pages read: 7 of 20` is shown.
  - The status region still says `Checking sources, 2 of 3`.
  - It passes `expectAccessible`.

  Watch it fail, because today's bar reads "Sources checked: 2 of 3". `keeps the article beneath named run progress and source checks` and `shows linked-page progress after every source is checked without changing status text` stay unchanged.

- [x] 6.2 In `frontend/src/pages/Home.tsx`, show the linked-page line when the run is `collecting` and `context_total > 0`. Verify with `npm test -- --run` and `npm run build` in `frontend/`.

  **Mutation F1:** restore the `source_checks.length === run.sources_total` condition. Run the new test.

## 7. Final checks and report

- [x] 7.1 Run all of these:
  - `uv run --offline pytest` in `backend/`;
  - the concurrency files five times in a row: `for i in 1 2 3 4 5; do uv run --offline pytest tests/test_context_gather.py tests/test_host_spacing.py tests/test_context_robots.py tests/test_safe_fetch.py tests/test_digest_runner.py -q || break; done`. Every run must pass;
  - `npm test -- --run` and `npm run build` in `frontend/`;
  - `DO_NOT_TRACK=1 openspec validate improve-context-pass-speed-and-progress --strict`;
  - `git diff --check`.

  Do not run Docker.
- [x] 7.2 Write `docs/process/test-report-improve-context-pass-speed-and-progress.md`. Include:
  - for each task, the red result and the green result;
  - a table of every named mutation, with its test and result;
  - the existing tests set to one worker in 5.2, each with its reason;
  - the commands of 7.1, with their results.
- [x] 7.3 Add a Droid entry to `docs/process/ai-usage-log.md`, after Claude Code's planning entry for this change. Give the prompt as run, the tool and model, the outcome, and anything that failed or was retried.
