# Proposal

## Why

A run's per-source outcome can contradict the digest the run saves (issue #31). After a source is added, its first run reports "No new items" for it, although the digest contains the entries recorded when the source was added. The outcome describes only what the run's own feed check discovered, while the run digests every pending item (`research.md`, "Checking a source in a run" and "What a run digests"). The same mismatch occurs in three other cases:
- an item left pending by a failed run reappears without "New items"
- a podcast episode whose transcript arrives later appears without "New items"
- a newly seen YouTube Short that is skipped counts as "New items" although nothing reaches the digest

## What Changes

- **New meaning.** A run's outcome for a source means "this run includes something from this source". It is `new_items` when the run includes at least one of the source's items, either summarized or under Creator updates. It does not matter whether the entry was first seen in this check, recorded when the source was added, or held from an earlier run. Otherwise a successful check is `no_new_items`.
- **Items not yet delivered.** Items still waiting for a transcript or captions, or deferred to a later run, do not make the outcome `new_items`. The run already reports them separately as waiting or deferred.
- **When the outcome is set.** While sources are being checked, each check shows what it found. The outcome becomes final as soon as the run has chosen its items, before summarizing.
- **Unchanged:**
  - `failed`, including the rate-limited flag and the error text
  - possible gap
  - the confirm-time outcome when a source is added
  - the labels "New items" and "No new items"
  - the API shape
- **The Sources list** shows the final outcome, because it reads the latest check.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `content-collection`, "Check every source on each run": `new_items` and `no_new_items` are redefined in terms of what the run includes from the source, and the outcome is final once the run has chosen its items. New scenarios cover:
  - the first run after adding a source
  - an item carried over from a failed run
  - an episode held for its transcript
  - a skipped Short

## Impact

- **Backend.**
  - `backend/src/catchup/digest/runner.py`: after the run selects its items, each successful check of the run is updated, both its status and its count, together with the source's last-check status.
  - `backend/src/catchup/collection.py` is unchanged; it still records what the feed check found.
- **Tests.**
  - `backend/tests/test_core_flow.py:84` currently asserts `no_new_items` for the first run after adding a source, and changes to `new_items`.
  - New runner tests go in `backend/tests/test_digest_runner.py`.
- **No change** to the frontend, the API shape, the database schema, or the confirm flow.
