# Tasks

Implementer notes:
- **Read first.** Read `proposal.md` and `design.md` (all of "Context", and D1–D3). This change has no spec delta (`skip_specs: true`): no behavior changes. If something looks wrong or contradictory, stop and report instead of redesigning.
- **Work test-first with the `tdd` skill** (D-016). For each group, first write its tests, run them, and watch them fail, or pass, as the task states. Then change the code. The seams are named in each task, and they count as agreed:
  - `respx` routes;
  - `sqlalchemy.event.listen(Item, "load", …)`;
  - `monkeypatch` of `catchup.digest.runner.fetch_captions`;
  - `FakeModel`, `environment`, `seed`, `stub_collection`, and `execute` in `backend/tests/test_digest_runner.py`;
  - `ready` and `videos` in `backend/tests/test_caption_pass.py`;
  - `client`, `seed_source`, `episode_feed`, `run_check`, `FEED_URL`, and `TRANSCRIPT_URL` in `backend/tests/test_podcast_collection.py`;
  - `watchPollTimer` and the fake timers in `frontend/src/pages/Home.test.tsx`.
- **Test rules.**
  - No real network and no real sleeps.
  - Use `respx.mock(assert_all_mocked=True, ...)` as the existing tests do. A test with a route that must not be called passes `assert_all_called=False`.
  - Change no existing backend test. In `Home.test.tsx`, change only the poll steps (task 3.2).
  - The pin tests in group 2 pass on unchanged code. Their "red" step is the named mutation: apply it, watch the test fail, and restore the code.
- **Environment.**
  - Backend: run commands in `backend/` with `uv run`, without installing new packages.
  - Frontend: use Node 22.17.1 with `export PATH="$HOME/.nvm/versions/node/v22.17.1/bin:$PATH"`. Then run `npm ci --offline --no-audit --no-fund` in `frontend/`: it installs the locked packages from the local npm cache. If it fails, stop and report. Do not download packages, and do not change `package.json` or `package-lock.json`.
- **Out of scope:**
  - every backend source file except `backend/src/catchup/collection.py`;
  - frontend source files, and frontend test files other than `Home.test.tsx`;
  - `extension/`, migrations, models, and dependency versions.
- **Do not edit** `proposal.md`, `design.md`, `docs/process/decision-log.md`, or `docs/process/requirements-changes.md`. Claude Code wrote D-032 with the plan.
- **Commits.** Commit after each task group. Do not push, tag, or open a PR.

## 1. A source check loads full rows only for episodes it may update (D1)

- [x] 1.1 Write two failing tests in `backend/tests/test_podcast_collection.py`. In both, record loads with `event.listen(Item, "load", on_load)`, where `on_load(target, _context)` appends `target.identity_key`, and remove the listener in a `finally`. Mock every request the checks make with respx: the feed, and any episode page or show-notes link they fetch. Read `_resolve_episode` and `article_text` in `collection.py` to see which ones.
  - `test_podcast_check_loads_only_episodes_it_may_update`. Use `seed_source(client)` and one feed with three entries (guids `delivered`, `found`, and `waiting`), each with an enclosure and no transcript tag.
    1. Run `run_check(client)` once to create the three episodes.
    2. In a session, set `delivered` to `state="delivered"` with a 200,000-character `content_text`, and `found` to `transcript_status="found"` with a 200,000-character `content_text`. Leave `waiting` as created. Commit.
    3. Clear the recorded loads, and run `run_check(client)` again with the same feed.

    Assert that the recorded loads are exactly `["waiting"]`.
  - `test_website_check_loads_no_full_rows`. Do not call `seed_source`. Add a `Source` with `kind="feed"` and `feed_url=FEED_URL`, and two items for it: one `delivered` and one `pending`, each with a 200,000-character `content_text` and no `transcript_status`. The feed has one entry with a new guid and **no enclosure**: with an audio enclosure, the check upgrades the source to a podcast (`collection.py:96-97`), and the pending item is then rightly loaded. Mock the entry's link page, which `article_text` fetches when the entry's text is short. Clear the loads, run `run_check(client)`, and assert that no load was recorded.
  - In both tests, copy the recorded loads right after the `run_check` call under test, before the test reads any item itself: the listener also records the test's own reads.
  - `test_feed_upgraded_to_podcast_resolves_pending_item`. Add a `Source` with `kind="feed"` and `feed_url=FEED_URL`, and one `pending` item for it with `identity_key="ep1"`, link `https://site.example/episode`, and no `transcript_status`. Run `run_check(client)` with `episode_feed()`. Assert that the source's kind is now `"podcast"`, and that the item's `transcript_status` is `"waiting"`.

  Verify: run `uv run pytest tests/test_podcast_collection.py` in `backend/`. Before 1.2 the two load tests fail: the podcast test records all three keys, and the website test records two. The upgrade test passes: it guards D1's `NULL` case and the query's place after the upgrade. Every existing test passes.
- [x] 1.2 Implement D1 in `backend/src/catchup/collection.py`.
  - Replace `existing_items` with the column query `known`, and build `keys`, `links`, and `possible_gap` from it.
  - Build `by_key` from the full-row query for podcast sources only, after the `source.kind` upgrade. Use `Item.transcript_status.in_(("to_fetch", "waiting")) | Item.transcript_status.is_(None)`.
  - Keep the loop and its condition unchanged.

  Verify:
  - the three 1.1 tests pass, and `uv run pytest` passes in `backend/`, with no existing test changed;
  - each mutation below makes at least the named test fail. Run each one alone, watch it fail, and restore the code. Record each mutation and the tests that failed in the test report (task 4.1):
    - (M1) Load every item of the source as a full row again, for `by_key`: `test_podcast_check_loads_only_episodes_it_may_update`.
    - (M2) Drop the `transcript_status` filter, keeping `state == "pending"`: the same test, because `found` is loaded.
    - (M3) Build `by_key` for every source kind: `test_website_check_loads_no_full_rows`.
    - (M4) Drop the `is_(None)` part of the filter: `test_feed_upgraded_to_podcast_resolves_pending_item`.
    - (M5) Use `bool(by_key)` instead of `bool(known)` for `possible_gap`: at least one possible-gap test in `tests/test_collection.py`, such as `test_possible_gap_only_with_prior_items_and_no_match`. Name every test that fails in the report.
    - (M6) Build `by_key` before the `source.kind` upgrade: `test_feed_upgraded_to_podcast_resolves_pending_item`.

## 2. Pins for three rules (D2)

- [x] 2.1 Add `test_found_caption_replaces_earlier_summary` to `backend/tests/test_caption_pass.py`. Use `ready`, and `videos(client, 1, status="caption_wait", discovered=NOW - timedelta(hours=6))` as `test_caption_wait_retries_then_finds_caption` does.
  - Set the item's `summary` to "Old description summary", and its `summary_language` to `"en"`.
  - Monkeypatch `fetch_captions` to return `("found", "Transcript now available")`.
  - Run `execute(client)`, and assert:
    - the run succeeded;
    - one model call's messages contain "Transcript now available";
    - the item's `summary` is not "Old description summary".

  Verify: the test passes on unchanged code. Under (Y1), removing `item.summary = None` and `item.summary_language = None` after captions are found (`runner.py:117-118`), it fails. Restore the code.
- [x] 2.2 Add `test_new_summary_resets_used_context_rows` to `backend/tests/test_digest_runner.py`.
  - Use `seed(environment)` and `stub_collection(monkeypatch)`.
  - Give the item `context_status="gathered"`, no summary, and two `ItemContext` rows, `L1` and `L2` (kind `link`, positions 1 and 2), both with `used=True`. The gathered status keeps the pass from fetching anything.
  - Use `FakeModel([{"summary": "New summary", "used": ["L2"]}, {"topics": [{"title": "Topic", "overview": "Overview", "item_refs": ["i1"]}]}])`, as `test_newly_gathered_link_invalidates_cached_summary` does.
  - Run `execute(environment)`, and assert that the run succeeded, `L1.used` is `False`, and `L2.used` is `True`.

  Verify: the test passes on unchanged code. Under (U1), `part.used = part.used or part.ref in result.used` (`runner.py:375`), it fails. Restore the code.
- [x] 2.3 Add `test_waiting_episode_that_becomes_text_drops_earlier_summary` to `backend/tests/test_podcast_collection.py`.
  1. Use `seed_source(client)`, and run `run_check(client)` with `episode_feed()`, so that the episode is `waiting`.
  2. Set its `summary` to "Old description-based summary" and its `summary_language` to `"en"`.
  3. Run `run_check(client)` with a feed that lists the same entry (`guid` `ep1`) without an enclosure. Mock any page that `article_text` fetches for it.

  Assert that the episode's `transcript_status` is `"text"`, and that `summary` and `summary_language` are `None`.

  Verify: the test passes on the current code. Under (P1), removing the two lines `prior.summary = None` and `prior.summary_language = None` after `prior.transcript_status = "text"` in `collection.py`, it fails. Restore the code.

  Verify for the group: `uv run pytest` passes in `backend/`.

## 3. One poll helper in `Home.test.tsx` (D3)

- [x] 3.1 Record the baseline, with the environment from the implementer notes.
  - Run `npx vitest run src/pages/Home.test.tsx` in `frontend/`. Record the count; the probe found 99 passing tests.
  - Apply (F1, before): delete the 19 `await act(async () => { await vi.advanceTimersByTimeAsync(…) })` lines that follow the poll waits. Run the same command, record the names of the failing tests, and restore the file.
- [x] 3.2 Implement D3 in `frontend/src/pages/Home.test.tsx`.
  - `watchPollTimer()` returns `advancePoll(ms = 1000)`, which waits for the poll timer, restores the spy, and then advances fake time by `ms` inside `act`.
  - Replace each of the 19 waits and the `act` step after it with `await advancePoll()`. Name the first watcher in a test `advancePoll`, and a second one `advanceSecondPoll`. The site that advances 2000 ms passes `2000`.
  - Change nothing else in the file.

  Verify:
  - `npx vitest run src/pages/Home.test.tsx` passes the same number of tests as in 3.1;
  - `grep -c "advanceTimersByTimeAsync" src/pages/Home.test.tsx` gives 1, inside `advancePoll`. If another test advances time outside the poll steps, report the count instead;
  - (F1, after): delete the one `act` line inside `advancePoll`. The same tests fail as in 3.1. Restore the file. Record both lists in the report;
  - `npm test -- --run` and `npm run build` pass in `frontend/`.

## 4. Checks and report

- [x] 4.1 Run the full checks:
  - `uv run pytest` in `backend/` (record the count);
  - `npm test -- --run` and `npm run build` in `frontend/`, with Node 22.17.1 (record the counts);
  - `DO_NOT_TRACK=1 openspec validate finish-fix-round-cleanup --strict`.

  Do not run `docker build` or `scripts/docker-smoke.sh`: at `--auto medium` the smoke script is refused, and Claude Code runs both at review.

  Write the commands and their real results to `docs/process/test-report-finish-fix-round-cleanup.md`:
  - each new test, and the mutation that it kills;
  - mutations M1–M6, Y1, U1, and P1, with their results, and the F1 lists from 3.1 and 3.2;
  - the Docker smoke and the live comparison from design "Migration Plan", listed as not performed (Claude Code runs them at review).

  Add your entry to `docs/process/ai-usage-log.md` after the latest entry, with a faithful prompt excerpt. Leave out the session id; Claude Code adds it at review.

  Verify: every command that ran passes, and the report has the actual numbers.
