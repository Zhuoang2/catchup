# Design

## Context

The motivation is in proposal.md ("Why"). The code on `main` at `6ee13dd`:

- **`check_source`** (`backend/src/catchup/collection.py:76-165`) loads `existing_items = session.scalars(select(Item).where(Item.source_id == source.id)).all()` (`:99`). It uses the rows in four places:
  - `keys`, the identity keys (`:100`);
  - `by_key`, a map from key to row (`:101`). It is read only for podcast sources (`:113`), and only for rows that are `pending` with `transcript_status` in `("to_fetch", "waiting", None)` (`:114`). Those rows are then updated: through `_resolve_episode` when the entry has audio, or by setting the text and clearing the summary when it does not (`:117-123`). A pending podcast item with no `transcript_status` exists only when a website source was upgraded to a podcast (`:96-97`);
  - `links`, the links that are not fallback links (`:103`);
  - `bool(existing_items)`, for `possible_gap` (`:157`).

  Each row carries `content_text`, which for a delivered podcast or YouTube transcript can be about 170,000 characters, as well as `summary`, `entry_links`, and `image_candidates`.
- **The caption pass** (`backend/src/catchup/digest/runner.py:67-123`). It skips an item in `caption_wait` once `caption_wait_hours` have passed since discovery (`:90-93`). When captions are found, it sets the text and origin, and clears `summary` and `summary_language` (`:114-118`).
- **The summary stage** reuses a summary when `item.summary` is set and `item.summary_language` equals the run's language (`backend/src/catchup/digest/summarize.py:146-147`). So an uncleared summary is reused instead of being made again from the transcript.
- **`record`** (`runner.py:364-379`) sets `part.used = part.ref in result.used` for every context row of a newly summarized item (`:374-375`).
- **Existing tests.**
  - `test_missing_transcript_waits_and_later_replaces_summary` (`backend/tests/test_podcast_collection.py:100-119`) covers the podcast transcript path (`_resolve_episode`), but not the text path at `collection.py:117-123`.
  - No test checks a website source upgraded to a podcast with a pending item, so the `NULL` part of the condition at `:114` is unpinned.
  - `test_caption_wait_retries_then_finds_caption` (`backend/tests/test_caption_pass.py:117-128`) starts with no summary.
  - No test sets `used` before a new summary.
- **Mutation probe** on 2026-11-16, in a scratch worktree at `main`. Each of these passed the full suite (961 tests):
  - Y1: remove the summary clearing in the caption pass;
  - U1: `part.used = part.used or part.ref in result.used`;
  - P1: remove the summary clearing in the text path of `check_source`.
- **`Home.test.tsx`.** `watchPollTimer()` (`frontend/src/pages/Home.test.tsx:10-19`) spies on `window.setInterval`, and returns a function that waits until a 1,000 ms interval was set, and then restores the spy.
  - It is called before `render` in 15 tests, and again before a second Generate in 4 of them.
  - Each of the 19 waits is followed by `await act(async () => { await vi.advanceTimersByTimeAsync(…) })`. The time is 1000 in 18 places, and 2000 in one (`:1194-1195`).
  - `Home.tsx` polls every 1,000 ms (`frontend/src/pages/Home.tsx:187-196`).
- **Probes** on 2026-11-16:
  - **SQLAlchemy.** An `Item` `"load"` event listener (`sqlalchemy.event.listen(Item, "load", …)`) fires once for each full `Item` row loaded into a session. In a podcast `check_source` with one delivered item, it fired once. `select(Item.identity_key, Item.link)` returns tuples and fires no `"load"` event.
  - **Frontend.**
    - With Node 22.17.1 (`~/.nvm/versions/node/v22.17.1/bin`), `npm ci --offline --no-audit --no-fund` in `frontend/` installed the locked packages from the local npm cache, with no download.
    - `npx vitest run src/pages/Home.test.tsx` then passed 99 tests.
    - The default `node` on this machine is 20.19.0. CI uses Node 24.

## Goals / Non-Goals

**Goals:**
- A source check holds full rows only for the pending podcast episodes it may update.
- Each of Y1, U1, and P1 makes a test fail.
- The 19 poll steps in `Home.test.tsx` use one helper, and the tests check the same things.

**Non-Goals:**
- Changing what a source check stores or reports.
- Other places that load full items: the run's pending query, gathering, and History.
- Changing the summary or `used` rules.
- Refactoring other frontend tests.

## Decisions

### D1. Read keys and links as columns, and load full rows only for episodes that may be updated

In `check_source`, replace `existing_items` with two queries.

- **Columns.** `known = session.execute(select(Item.identity_key, Item.link).where(Item.source_id == source.id)).all()`.
  - `keys` and `links` are built from `known`, as today.
  - `possible_gap` uses `bool(known)`.
- **Full rows.** For a podcast source only, `by_key` comes from `select(Item)` with `source_id`, `state == "pending"`, and `transcript_status` in `("to_fetch", "waiting")` or `NULL`. Use `Item.transcript_status.in_(…) | Item.transcript_status.is_(None)`, as the caption pass does (`runner.py:74-76`); SQL `IN` does not match `NULL`. For other kinds, `by_key` is empty.
  - The query runs after the `source.kind` upgrade at `:96-97`, as `by_key`'s only reader does today.
  - The loop keeps its own condition (`:114`) unchanged. With the narrower query it is always true; it stays as the rule's statement in one readable place.
- **Alternative: `load_only(Item.identity_key, Item.link)`, or `defer(Item.content_text)`.** Rejected: the rows would still enter the session as partial objects. The update branch would then load the deferred columns lazily, one item at a time.
- **Alternative: keep `select(Item)` for podcast sources only.** Rejected: delivered episodes have the longest texts.

### D2. One test for each unpinned rule, with no source change

- **Y1** (`backend/tests/test_caption_pass.py`). A pending YouTube item in `caption_wait`, discovered less than `caption_wait_hours` ago (so the caption pass retries it), with an earlier summary in the run's language. Captions are found. The new summary must come from a model call that contains the transcript text, and the stored summary must be the new one.
- **U1** (one runner test file). A pending item with two context rows, both `used=True`, and no summary. The model answers with `used: ["L2"]`. Afterwards L1 is `False` and L2 is `True`.
- **P1** (`backend/tests/test_podcast_collection.py`). A waiting episode with an earlier summary. The next check's feed lists the same entry without audio. Afterwards the episode has `transcript_status == "text"` and no summary.

Each test must fail under its mutation, and pass on `main`.

### D3. `watchPollTimer()` returns `advancePoll`

`watchPollTimer()` keeps its spy and its wait. The function it returns becomes `advancePoll(ms = 1000)`:
1. it waits for the 1,000 ms interval, and restores the spy (unchanged);
2. it then runs `await act(async () => { await vi.advanceTimersByTimeAsync(ms) })`.

Each call site becomes `const advancePoll = watchPollTimer()` … `await advancePoll()`. A second watcher is named `advanceSecondPoll`, and the 2000 ms site passes `2000`.

- **Why not a helper that also starts the watch.** The spy must be in place before `render` or the second Generate, while the wait comes later. So the two steps stay split, as today.
- **Check that the tests keep their strength.** Remove the time advance before and after the refactor: before, every `act` step after a poll wait; after, the one inside `advancePoll`. The same tests must fail. (A change to the poll interval is not a useful check: the watcher's own wait for a 1,000 ms interval fails first, both before and after.)

## Risks / Trade-offs

- [A podcast episode that the narrower query leaves out would no longer be updated.] → The query uses exactly the loop's condition. `test_missing_transcript_waits_and_later_replaces_summary` and the new P1 test cover both update branches, and a new test covers a website source upgraded to a podcast (the `NULL` case, and the query's place after the upgrade). The two load tests pin which rows are loaded.
- [The Y1 test depends on the run's language matching the stored summary's.] → The test stores `summary_language = "en"`, the test environment's language, as `backend/tests/test_digest_runner.py:1241` does. Before the fix it must show that the old summary would be reused: under Y1 no summary call for the item is made.
- [`npm ci --offline` depends on the local npm cache.] → The probe passed. If it fails for Droid, Droid stops and reports, and does not download.

## Migration Plan

No data migration. Roll back by reverting the merge.

At review, Claude Code runs:
- the Docker smoke script (`scripts/docker-smoke.sh`);
- the frontend suite and build under Node 22;
- a live comparison as in `refactor-context-fetch-budget-and-robots`:
  - images from `main` and from the branch, each on a fresh local instance (not 8800), with a stub model;
  - the same public podcast feed with `podcast:transcript` tags (picked at review), and the same website feed;
  - two runs on each. The second run checks the sources again, after the first run's items were delivered;
  - the run counters and the stored items must be the same on both.
