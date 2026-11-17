# Proposal

## Why

#60 listed cleanup that earlier fix rounds left behind. PR #92 did parts 1 and 2. What is left:

- **A source check reads every past item in full.** `check_source` loads every item of the source as a full row (`backend/src/catchup/collection.py:99`), including its text. A delivered podcast or YouTube transcript can be about 170,000 characters. The check needs only the identity keys and links, plus the few pending episodes it may update.
- **Three rules have no test that fails when they break.** On `main` at `6ee13dd`, each mutation below passes the full backend suite (961 tests):
  - the caption pass clears an earlier summary when YouTube captions are found (`backend/src/catchup/digest/runner.py:117-118`). This is the spec scenario "Transcript found after an earlier summary". Only the podcast transcript case is tested;
  - a new summary resets every context row's `used` flag (`runner.py:374-375`). `part.used = part.used or …` passes;
  - a source check clears an earlier summary when a waiting episode turns into a text post (`collection.py:122-123`).
- **#60 part 3.** In `frontend/src/pages/Home.test.tsx`, 19 places repeat the same two steps after `watchPollTimer()`: wait for the poll timer, then advance fake time inside `act`.

## What Changes

- **Lighter source checks.** `check_source` reads only `identity_key` and `link` for the source's past items. It loads full rows only for the podcast episodes it may update: pending, with `transcript_status` `to_fetch`, `waiting`, or empty. What a check stores, and what it reports, do not change.
- **Pins for the three rules.** One test each. No source change.
- **One poll helper.** `watchPollTimer()` returns `advancePoll(ms = 1000)`, which waits for the poll timer and then advances fake time. The 19 call sites use it. No test changes what it checks.
- No API, data model, UI, or spec change. No migration.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- None. No requirement changes; `skip_specs: true` is set in `.openspec.yaml`.

## Impact

- Code: `backend/src/catchup/collection.py` (the past-item queries in `check_source`).
- Tests:
  - `backend/tests/test_podcast_collection.py`, `test_caption_pass.py`, and one runner test file;
  - three new source-check tests: the rows loaded for a podcast source and for a website source, and a website source upgraded to a podcast, whose pending item has no transcript status yet;
  - `frontend/src/pages/Home.test.tsx` (the helper and its 19 call sites).

  Every existing backend test passes unchanged.
- Docs: the decision log (D-032), a test report, and the AI usage log.
- Out of scope:
  - other queries that load full items, such as the run's pending items;
  - the `used` and summary rules themselves;
  - other repeated steps in frontend tests.
