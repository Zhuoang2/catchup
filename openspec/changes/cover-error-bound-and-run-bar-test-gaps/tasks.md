# Tasks

Implementer notes:
- **Read first.** Read `proposal.md`. There are no spec deltas and no design document. If something looks wrong, stop and report.
- **Use the `tdd` skill.** The code is already correct, so the red step for each new check is a named temporary mutation of the runtime code, applied by hand:
  1. Write the check and see it pass.
  2. Apply the mutation, and see the check fail.
  3. Revert the mutation, and see the check pass again.

  Record each check, its mutation, and the failing result in the report. Before each commit, `git diff` must show only test files and docs.
- **Test rules.**
  - Backend: `respx` and the existing DNS fixtures (`public_dns`, `blocked_candidate_dns`), no real network.
  - Frontend: mock `fetch` as the existing tests do, no real timers, and run `expectAccessible` on new rendered states.
- **Out of scope:**
  - any change to runtime code
  - the row order of the attention list
  - #44 item 5
- **Commits.** Commit after each task group. Do not push, tag, or open a PR.

## 1. Feed discovery bounds (#44)

- [x] 1.1 In `backend/tests/test_discovery.py`, add:
  1. **404, then over the size limit.** A page declares two feeds: the first answers 404, and the second answers 200 with a body over `max_feed_bytes`. `discover` raises `feed_unavailable` with `status_code` 404.
  2. **Blocked, then over the size limit.** The first declared feed is on a host that `blocked_candidate_dns` resolves to a private address, and the second is over the size limit. `blocked_address` is raised.
  3. **307 without `Location`.** The pasted page answers 307 with no `Location`. `fetch_failed` is raised with `status_code` 307, and no probe request is made.
  4. **Status 600.** A declared feed answers 600. `feed_unavailable` is raised with 600.
  5. **Message text.** In one existing `feed_unavailable` test, also assert the message: "The site's feed is temporarily unavailable."

  Named mutations, each to be seen failing:
  - For 1 and 2: reduce the declared-candidate guard to `if exc.code == "fetch_failed":`.
  - For 3: change the bound in `http_error_status` to `>= 303`. Test 3 fails because the page then probes.
  - For 4: add `and exc.status_code < 600` to `http_error_status`.
  - For 5: change the text of `FEED_UNAVAILABLE_MESSAGE`.

  Verify: all new checks pass on the current code, each named mutation fails its check, and every mutation is reverted.
- [x] 1.2 In `backend/tests/test_sources_api.py`, add a preview of a page that answers 307 without `Location`. It returns 422 `fetch_failed`, and the JSON has no `http_status` key. Mutation: change the bound in `http_error_status` to `>= 303`.

  In `frontend/src/pages/Sources.test.tsx`, add a case to the bounds table: `fetch_failed` with `http_status` 307 gives the unchanged no-status message, "Could not fetch the source. Check the URL and try again." Mutation: change the frontend bound to `>= 303`.

  Verify: both checks pass on the current code, each mutation fails its check, the mutations are reverted, and `uv run pytest` and `npm test -- --run` pass.

## 2. Result titles in the ended-run table (#38)

- [x] 2.1 In the 12-row ended-run table in `frontend/src/pages/Home.test.tsx` ("shows %s in the %s layout with %s"), add one shared title assertion per status:
  - `succeeded`: the `Digest run` region contains "Your digest is ready".
  - `no_new_content`: the region contains "No new content".
  - `failed`: the page shows the alert title "Digest generation failed". In the compact layout, it is inside the `Digest run` region.

  Named mutations, each to be seen failing:
  - Drop the title from the compact result line for `succeeded`.
  - Change the alert title in the failed branch.
  - Change the alert title in the failed branch only when `compact`.

  Verify: all 12 rows pass on the current code, each mutation fails at least one row, the mutations are reverted, and `npm test -- --run` passes.

## 3. Checks and report

- [ ] 3.1 Run `npm run build` in `frontend/` first, then:
  - `uv run pytest --cov=catchup --cov-report=term` in `backend/`
  - `npm test -- --run` in `frontend/`
  - `openspec validate cover-error-bound-and-run-bar-test-gaps --strict`

  Write the commands, their real results, and the mutation table to `docs/process/test-report-cover-error-bound-and-run-bar-test-gaps.md`. Add your entry to `docs/process/ai-usage-log.md` after the latest entry, with a faithful excerpt of the prompt you actually received, and the tool and model. Leave out the session id.

  Verify: every command passes, and the report has the actual numbers.
