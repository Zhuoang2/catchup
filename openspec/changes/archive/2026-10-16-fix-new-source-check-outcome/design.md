# Design

The user chose on 2026-10-16:
- "New items" means the run includes something from that source.
- The labels stay "New items" and "No new items", with no count.

See `proposal.md` for the motivation and `research.md` for the code facts.

## Context

- **What `check_source` records.** It stores a `SourceCheck` whose `status` and `new_count` describe only the entries this check saw for the first time (`backend/src/catchup/collection.py:105-137`). A skipped Short is stored as `baseline` but still adds to `new_count` (`:114-130`).
- **What the run includes.** After all checks and the caption pass, the run loads every pending item, and `select_pending` splits it into ready, Creator updates, waiting, and deferred (`backend/src/catchup/digest/runner.py:209-229`, `:35-58`).
- **What the API returns.** `run_detail` returns each check's `status` (`runner.py:392-396`). `GET /api/sources` reads the latest check (`backend/src/catchup/api/sources.py:169-176`).

## Goals / Non-Goals

**Goals:**
- A run's per-source outcome matches the digest that run builds.
- The outcome is final before summarizing starts.

**Non-Goals:**
- Changing labels or showing counts.
- Changing the API shape, the frontend, or the schema.
- Changing the confirm-time check written when a source is added, or how entries are recorded.

## Decisions

### D1. Finalize outcomes in the runner, right after selecting items
- **Where.** Inside the session that runs `select_pending` and stores `waiting_count` and `deferred_count` (`runner.py:211-229`), before that session's commit.
- **The count.** For each source, count the run's included items: the `ready` items and the `creator_updates` from that source. `select_pending` returns Creator updates as item ids, so map them to source ids through the loaded rows.
- **Updates.** For each `SourceCheck` with this `run_id` and a status other than `failed`:
  - set `status` to `new_items` when the count is above 0, otherwise to `no_new_items`
  - set `new_count` to the count
  - set the source's `last_check_status` to the same value
- **A source deleted during the run.** It must not fail the run (review, 2026-10-16). Deleting a source cascades to its checks, so checks and sources that no longer exist are skipped. The update must not raise when its row is already gone; for example, use a bulk `UPDATE` by id, not ORM attribute changes on loaded rows. This matches how the save step already tolerates deleted items.
- **Commit.** All of this commits together with the waiting and deferred counts. It therefore happens before the `no_new_content` return (`runner.py:233-240`), and before the stage moves to summarizing.
- **Alternative:** compute the final outcome inside `check_source`. Rejected: caption results are known only after `caption_pass`, and the waiting and deferred rules live in `select_pending`. Repeating them in the collector would split one rule across two places.

### D2. `check_source` stays as it is
- During collecting, the run JSON shows each check's own result, which the spec allows.
- A source with only carried-over items can therefore show "No new items" while sources are still being checked, then "New items" once the run has chosen its items. This lasts only for the collecting stage.
- The collector's tests (`backend/tests/test_collection.py`) are unchanged.

### D3. What a failed run shows
- A run that fails after choosing its items still shows `new_items` for the sources whose items it had chosen, while its result says that no digest was saved. This matches the meaning "this run includes something from this source".
- **Alternative:** recompute the outcomes on failure. Rejected: it adds a second code path, and "No digest was saved" already explains the result.

### D4. Alternatives the user rejected
- **"The source still has pending items."** Waiting podcasts would show "New items" on every run while nothing from them appears.
- **"Fix only the first run after adding a source."** The carried-over and Shorts mismatches would remain.
- **Counts in the labels**, such as "3 new items". This would mean a larger change to the API, the UI, and the tests.

## Risks / Trade-offs

- **[Brief flip during collecting]** A source with only carried-over items can change from "No new items" to "New items" when the stage moves to summarizing. → Accepted. The final value is set before any item is summarized.
- **[Tests that stub collection]** `stub_collection` (`backend/tests/test_digest_runner.py:78-87`) always writes `no_new_items`, and those tests seed pending items, so their checks become `new_items`. → They assert only the number of checks, not statuses. The new tests assert the final statuses explicitly.

## Migration Plan

- No schema change and no data migration.
- Checks from runs before this change keep their stored statuses. Rollback is a revert.
