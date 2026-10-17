# Tasks

Implementer notes:
- **Read first.** Read `proposal.md`, `design.md` (D1–D3), and `specs/content-collection/spec.md` before starting. If something looks wrong or contradictory, stop and report instead of redesigning.
- **Work test-first with the `tdd` skill** (D-016). For each task, first write its verification items as failing tests and watch them fail, then implement until they pass. The seams to test are the ones named in each task; they count as agreed.
- **Test rules.** Tests make no real network calls (respx and the autouse DNS block), use no real sleeps, and write nothing outside temp dirs.
- **Out of scope:**
  - `backend/src/catchup/collection.py` (design D2)
  - the confirm-time check in `backend/src/catchup/api/sources.py`
  - the frontend
  - the API shape
  - the database schema
- **Commits.** Commit after each task group. Do not push, tag, or open a PR.

## 1. Final per-source outcomes after the run chooses its items

- [x] 1.1 Write the failing tests first.
  - In `backend/tests/test_core_flow.py:84`, change the first run's expected check from `no_new_items` to `new_items`, because that run includes the 2 entries recorded when the source was added. Keep the second run (`:95`, `no_new_items`) and the third (`:108`, `new_items`) as they are.
  - In `backend/tests/test_digest_runner.py`, add tests. They use `seed`, `execute`, and either `stub_collection` or a variant that writes a chosen status. The seams are:
    - the run JSON's `source_checks[*].status`
    - the `SourceCheck` row's `new_count`
    - `GET /api/sources` `last_check_status`
  - Cases:
    1. **Carried-over items.** A source has a pending item, and its check found nothing new: the stub writes `no_new_items`. After the run, its outcome is `new_items`, `new_count` is 1, and the Sources list shows `new_items`.
    2. **Two sources.** One source has a pending item and one has none: `new_items` and `no_new_items`.
    3. **Held episode.** A podcast source's only pending item is still waiting for its transcript (`transcript_status="waiting"`, recently discovered). The outcome is `no_new_items`, and the run's `waiting_count` is 1.
    4. **Recorded but not delivered.** The stub writes `new_items` with `new_count=1`, but the source's only new item is `baseline`, like a skipped Short. The outcome is `no_new_items`, with `new_count` 0.
    5. **A failed check stays failed.** The stub writes `failed` for a source that has a pending item, which the run includes. The outcome stays `failed`, with its error.
    6. **Carry-over after a failed run.** In the existing group-failure scenario (`test_group_failure_preserves_pending_and_retry_uses_cached_summary`), the retry run's check for that source is `new_items`.
    7. **No new content.** The stub writes `new_items` for a source with no pending item. The run ends `no_new_content`, and the outcome is `no_new_items`.
    8. **Final before summarizing.** The outcomes are already final when the first summary call is made: a fake model that reads the run's `SourceCheck` rows inside its first summary call sees the final statuses.

  Verify: the new and changed tests fail before 1.2.
- [x] 1.2 In `backend/src/catchup/digest/runner.py`, implement design D1.
  - Inside the session that runs `select_pending` (`:211-229`), count each source's included items: the ready items plus the Creator updates, mapping Creator-update item ids to sources through the loaded rows.
  - Update every `SourceCheck` of this run that is not `failed`: set `status` and `new_count`, and set the source's `last_check_status` to the same status.
  - Commit this together with the waiting and deferred counts, before the `no_new_content` return.

  Verify: the 1.1 tests pass, the whole `uv run pytest` suite passes, and the coverage reported for `digest/runner.py` does not drop.

## 2. Integration checks and report

- [x] 2.1 Run the full checks:
  - `uv run pytest --cov=catchup --cov-report=term` in `backend/` (count and coverage)
  - `npm test -- --run` and `npm run build` in `frontend/` (unchanged, a regression check)
  - `openspec validate fix-new-source-check-outcome --strict`
  - a local `docker build`, if available

  Write the commands and their real results to `docs/process/test-report-fix-new-source-check-outcome.md`. List the manual check that was not performed: adding a public feed on a local instance, then running a digest, and seeing "New items" for it next to its items in the digest.

  Add your entry to `docs/process/ai-usage-log.md`, after the latest entry, with the Droid session id, a faithful prompt excerpt, the outcome, and the problems.

  Verify: every command passes, and the report has the actual numbers.

## 3. Review fixes, round 1

Notes for this round:
- These tasks come from the review of groups 1–2 (`/code-review`, the spec subagent with mutation tests, and a live check on a local instance). Each finding was confirmed.
- Design D1 has a new "A source deleted during the run" bullet; read it first.
- **Use `diagnosing-bugs`** for 3.1 and **`tdd`** for 3.2.
- Do not edit `proposal.md`, `design.md`, or the spec deltas.

- [x] 3.1 A source deleted during the run fails the whole run (design D1).
  - **Cause.** The finalizing loop (`backend/src/catchup/digest/runner.py:235-241`) loads the run's checks and then changes them and their sources through the ORM. If the source is deleted after that SELECT, two things go wrong:
    - `session.get(Source, …)` returns `None`, which raises `AttributeError` when the source had no pending item.
    - The UPDATE of the cascade-deleted check matches 0 rows, which raises `StaleDataError` when the source had a pending item.
    - Either way the run ends "Digest generation failed".
  - **Reproduction.** Use a failing-first test in `backend/tests/test_digest_runner.py`. A SQLAlchemy `after_cursor_execute` hook, or an equivalent seam, deletes a source right after the finalizing SELECT. Write one case for a source with a pending item and one for a source without.
  - **Fix.** Make the finalizing step skip checks and sources that no longer exist, and write the updates so that a missing row cannot raise.

  Verify:
  - Both cases end `succeeded` or `no_new_content`, not `failed`.
  - The remaining sources get their final outcomes.
  - The deleted source's items are not saved, as in `test_deleted_source_during_grouping_saves_only_surviving_items`.
  - The new tests fail before the fix.
- [ ] 3.2 Make `test_held_podcast_episode_is_waiting_not_new` detect the bug it names. Today it uses `stub_collection`, which already writes `no_new_items`, so it passes without the fix.
  - Switch it to `stub_outcomes({"Source 0": "new_items"})`, as a real check would report for a newly seen episode.
  - Keep its assertions: `no_new_items`, `new_count == 0`, `waiting_count == 1`, and the Sources list.

  Verify: the test fails when the finalizing block (`runner.py:230-241`) is removed, and passes with it.
- [ ] 3.3 Docs:
  - In `docs/process/ai-usage-log.md`, your entry's heading names session `49b78a6b-…`, which is the Claude Code session. Correct it to your Droid session `ec0f2c13`, and add one short sentence on this round.
  - In `docs/process/test-report-fix-new-source-check-outcome.md`, re-run the backend coverage and record the real counts; the review measured 77 missed statements, not 78. Append a "Review fixes, round 1" section with the re-run results.

  Verify: the log heading names `ec0f2c13`, and the report numbers match a fresh run.
