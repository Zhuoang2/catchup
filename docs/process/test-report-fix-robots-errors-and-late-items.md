# Test report: fix-robots-errors-and-late-items

Date: 2026-11-16. Issues: #76 and #70.

Implementation commits: `5d22465` (group 1) and `5d17e70` (group 2).
Group 3 resumes in a new worktree at `5d17e70`; run 1 stopped when the
Docker smoke step exceeded its `--auto medium` permission level.
Historical test and mutation results below are from Droid's earlier runs,
not new mutation runs in this worktree.

## Final checks

| Runner | Directory | Command | Actual result |
| --- | --- | --- | --- |
| Droid, resumed run | `backend/` | `uv run pytest` | Exit 0, **938 passed in 27.80s**. Python 3.12.13, pytest 9.1.1. uv created `.venv` and installed 60 packages. |
| Droid, resumed run | Repository root | `DO_NOT_TRACK=1 openspec validate fix-robots-errors-and-late-items --strict` | Exit 0, `Change 'fix-robots-errors-and-late-items' is valid`. |
| Claude Code, at `5d17e70` in this worktree | Repository root | `docker build -t catchup:fix-robots-local .` | Passed, as reported by the user at resumption. |
| Claude Code, at `5d17e70` in this worktree | Repository root | `scripts/docker-smoke.sh catchup:fix-robots-local` | Passed all **12 checks**, as reported by the user at resumption; script cleanup left no container or volume. |

Claude Code's reported smoke checks: container healthy; GET `/api/health`;
GET `/` returns HTML; manifest, `sw.js`, and `offline.html` have the expected
types; saved zh-Hans preference; responses refuse framing; non-root process;
database on the volume; image excludes `.env` and the backend source tree;
preference survives restart.

Droid did not rerun either Docker command in the resumed run. The user's
resumption instruction supersedes task 3.1's image-removal instruction:
**`catchup:fix-robots-local` remains for Claude Code's live check and removal
after review.** Droid deleted nothing in this resumed run and did not send
anything to port 8800. No push, tag, release, or Docker prune was performed.

## Test-first checks from run 1

All pytest commands in this section ran from `backend/`.

| Stage | Command | Observed result |
| --- | --- | --- |
| 1.1, before the robots fix | `uv run pytest tests/test_context_robots.py tests/test_context_gather.py` | **13 failed, 41 passed in 5.16s**. The failures were the 13 behavior assertions listed under R1 below, not mock errors. The 404, 410, 429, 401, and 403 cases passed. |
| 1.2, after the robots fix | Same command | **54 passed in 3.38s**. |
| 1.2, backend regression | `uv run pytest` | **936 passed in 22.26s**. |
| After R1–R5 restoration | `uv run pytest tests/test_context_robots.py tests/test_context_gather.py` | **54 passed in 3.51s**. |
| 2.1, before the cutoff | `uv run pytest tests/test_context_gather.py` | **1 failed, 36 passed in 4.26s**. The late-page test observed first-run `digest_item_count == 2`, not 1. The source-check insertion guard already passed. |
| 2.2, after the cutoff | Same command | **37 passed in 5.96s**. |
| 2.2, backend regression | `uv run pytest` | **938 passed in 25.83s**. |
| After L1–L4 restoration | `uv run pytest tests/test_context_gather.py` | **37 passed in 3.80s**. |
| Run 1's initial final checks | `uv run pytest` | **938 passed in 24.96s**. Strict OpenSpec validation also passed. The Docker build passed; the smoke invocation was refused at Droid's permission level, so the run stopped before the report commit. |

The change adds tests only in `test_context_robots.py` and
`test_context_gather.py`. The only replaced existing test is
`test_failed_robots_request_allows`; the only other existing test changed is
the parameter list of `test_missing_or_restricted_robots`.
All other tests in the full suite already existed.

The tests use mocked HTTP/DNS and virtual delays, not real network or sleeps.
Unused routes opt out of `assert_all_called`; the capture callback records its
response and makes assertions only after `execute`. `Retry-After: 120` avoids
the fetcher's short-delay sleep.

## Scenario-to-test mapping

Paths below are relative to `backend/tests/`. “Existing” means unchanged by
this change. Some unchanged scenarios have complementary unit and runner
tests rather than one fixture reproducing every narrative detail.

### Content collection: Gather related context for website items

| Spec scenario | Tests | Provenance |
| --- | --- | --- |
| Short post with linked pages | `test_context_links.py::test_keeps_body_order_and_applies_limit_after_filtering`; `test_context_gather.py::test_runner_stores_three_links_in_order_and_ignores_tags` | Existing |
| Author replies in comments | `test_context_comments.py::test_marked_author_replies_include_parent_text`; `test_context_gather.py::test_author_reply_context_and_disable_switch` | Existing |
| robots.txt disallows a linked page | `test_context_robots.py::test_disallow_for_catchup_and_fetch_once_per_host`; `test_context_gather.py::test_robots_refusal_and_failed_pages_do_not_fail_run` | Existing |
| robots.txt answers a server error | `test_context_gather.py::test_robots_server_error_skips_the_sites_pages` | New, checks one robots request, neither page fetched, successful run, delivered item, and no context rows |
| robots.txt cannot be reached | `test_context_gather.py::test_unreachable_robots_keeps_other_sites` | New, checks no page request to the failed origin and exactly the other origin's context |
| robots.txt missing | `test_context_gather.py::test_runner_stores_three_links_in_order_and_ignores_tags` | Existing, robots 404 and pages read; no duplicate missing-robots test added |
| Per-run fetch limit reached | `test_context_gather.py::test_budget_leaves_unreached_items_ungathered_and_retries_do_not_refetch`; `test_context_gather.py::test_second_item_keeps_partial_context_in_successful_digest` | Existing |
| Article links on the same site | `test_context_links.py::test_taxonomy_is_a_whole_first_segment_and_www_is_same_site` | Existing, explicitly retains `/archives/10000`; runner fetching/storage is exercised by the existing linked-page tests |
| Link redirects to a login page | `test_context_gather.py::test_link_redirecting_to_login_does_not_store_the_final_page` | Existing |
| Context gathered once | `test_digest_runner.py::test_failed_run_reuses_gathered_context_without_fetching_again` | Existing |

Additional robots verification in `test_context_robots.py`:

- `test_unreachable_robots_disallows`: ConnectTimeout, ConnectError,
  ReadTimeout (replacement for the old allow-on-failure test).
- `test_unresolvable_robots_host_disallows`: no HTTP request and unchanged
  budget on DNS failure (new).
- `test_missing_or_restricted_robots`: existing 404/401/403 cases plus new
  410/429/500/502/503 cases.
- `test_rate_limited_server_error_disallows`: 503 with `Retry-After: 120` (new).
- `test_unreadable_robots_response_disallows`: 302 without Location and a
  200 body of 524,289 bytes (new).
- `test_unreachable_robots_is_cached_for_the_run`: two refusals, one robots
  request, budget 5 to 4 (new).

### Digest generation: Include every pending item

| Spec scenario | Tests | Provenance |
| --- | --- | --- |
| Long gap | `test_digest_runner.py::test_long_gap_snapshots_every_item_once_and_delivers_atomically` | Existing, 140 items |
| Run fails before saving | `test_digest_runner.py::test_group_failure_preserves_pending_and_retry_uses_cached_summary`; `test_creator_updates.py::test_failed_save_keeps_expiry_status_pending` | Existing |
| Episode waiting for a transcript | `test_digest_runner.py::test_held_podcast_episode_is_waiting_not_new`; `test_creator_updates.py::test_episode_waits_then_is_delivered_once` | Existing, one-day-old episode remains pending, then expires and is delivered |
| Item never repeated | `test_core_flow.py::test_incremental_api_flow_with_stored_citations`; `test_creator_updates.py::test_episode_waits_then_is_delivered_once` | Existing, summarized items and Creator updates respectively |
| Page saved while linked pages are read | `test_context_gather.py::test_page_saved_during_context_pass_waits_for_next_run` | New, first-run exclusion/pending/no context/no snapshot; next-run reference fetched once, gathered, delivered, exactly one snapshot |

`test_context_gather.py::test_item_recorded_during_source_checks_is_included`
is the new, initially green placement guard: an item committed during source
checking must remain in this run. L3 proves the guard can detect an early cutoff.

## Mutation results from run 1

Each mutation was applied alone to the passing implementation, run, and
restored in a `finally` block before the next mutation. Every invocation below
exited 1 for the named assertion failures. No mutant remains in either
implementation commit. The focused restoration checks above then passed.

Commands are relative to `backend/`; all used `uv run pytest`, with the test
selection shown below followed by `--tb=short -q`.

| Mutation | Test selection | Actual result and failed tests |
| --- | --- | --- |
| R1: restore `exc.status_code not in (401, 403)` | `tests/test_context_robots.py tests/test_context_gather.py` | **13 failed, 41 passed**: `test_missing_or_restricted_robots[500-False]`, `[502-False]`, `[503-False]`; all three `test_unreachable_robots_disallows[side_effect0/1/2]`; `test_unresolvable_robots_host_disallows`; `test_rate_limited_server_error_disallows`; both `test_unreadable_robots_response_disallows[response0/1]`; `test_unreachable_robots_is_cached_for_the_run`; `test_robots_server_error_skips_the_sites_pages`; `test_unreachable_robots_keeps_other_sites`. Refusals became allows or refused pages were requested. |
| R2: allow when status is None, otherwise use the fixed rule | `tests/test_context_robots.py tests/test_context_gather.py` | **5 failed, 49 passed**: all three `test_unreachable_robots_disallows[side_effect0/1/2]`; `test_unresolvable_robots_host_disallows`; `test_unreachable_robots_keeps_other_sites`. |
| R3: drop the 401/403 exception | `tests/test_context_robots.py` | **2 failed, 17 passed**: `test_missing_or_restricted_robots[401-False]` and `[403-False]`, both incorrectly allowed. |
| R4: allow only `code == 404` | `tests/test_context_robots.py` | **2 failed, 17 passed**: `test_missing_or_restricted_robots[410-True]` and `[429-True]`, both incorrectly refused. |
| R5: return False without caching it; still cache allowed errors | `tests/test_context_robots.py::test_unreachable_robots_is_cached_for_the_run` | **1 failed**: robots request count was 2, expected 1. |
| L1: remove `Item.id <= cutoff` | `tests/test_context_gather.py::test_page_saved_during_context_pass_waits_for_next_run` | **1 failed**: first-run digest count was 2, expected 1. |
| L2: read cutoff after `gather_context` | `tests/test_context_gather.py::test_page_saved_during_context_pass_waits_for_next_run` | **1 failed**: first-run digest count was 2, expected 1. |
| L3: read cutoff before source checks, at collecting | `tests/test_context_gather.py::test_item_recorded_during_source_checks_is_included` | **1 failed**: digest count was 1, expected 2. |
| L4: use `<` instead of `<=` | `tests/test_context_gather.py::test_page_saved_during_context_pass_waits_for_next_run` | **1 failed**: first-run status was `no_new_content`, expected `succeeded`, because the seeded item was excluded. |

For the parametrized tests, `side_effect0/1/2` are ConnectTimeout,
ConnectError, and ReadTimeout respectively; `response0/1` are the
destination-less 302 and oversized 200 respectively.

## Diagnosis and preflight notes

Ranked robots hypotheses were: (1) the error rule allows unreadable robots
responses, (2) the fetcher loses status information, (3) gathering bypasses
robots decisions. The red tests and status-preservation probes supported
(1); restricting only the error rule passed the tests, and R1/R2 reintroduced
the failures. Confirmed cause: the old rule allowed every error except
401/403, including missing statuses and 5xx.

Ranked late-item hypotheses were: (1) the post-context pending query admits
items absent from the context plan, (2) gathering includes the capture but
fails extraction, (3) saving duplicates the seeded item. The fixed plan and
unbounded pending query supported (1). The cutoff passed the two-run test;
L1/L2 reintroduced early inclusion. Confirmed cause: the plan and later
selection had different item sets.

Fresh read-only preflights checked each implementation group against code.
Short probes checked HTTPX exception/status behavior, unused respx routes,
oversized response length, extraction fixtures, nested TestClient POSTs,
cross-session visibility, and SQLite ID reuse. An initial in-memory schema
probe lacked the related context table; creating the full metadata corrected
the probe, which then passed. SQLite highest-rowid reuse is the design's
explicit known limit, not a new model/migration change.

## Not performed and retained artifacts

- **Live check not performed.** Claude Code will use a branch-local instance
  on a port other than 8800, a local stub model, and a public feed; save a page
  while linked pages are read, then verify it stays pending until the next
  run reads its context and delivers it. Docker smoke is not this live check.
- Standalone frontend/extension checks were not run: neither area changed.
- Image retained by explicit user instruction: `catchup:fix-robots-local`.
  Claude Code reports no smoke container or volume left over.
- Generated directories retained, with their contents, under the no-deletion
  instruction:
  - `/private/tmp/claude-501/-Users-madivhkassel-Desktop-Stanford-Fall-2026-CS-146S/fecc26ac-03ed-4f62-bdd5-ba35b7996c52/scratchpad/review-robots/backend/.venv/`
  - `/private/tmp/claude-501/-Users-madivhkassel-Desktop-Stanford-Fall-2026-CS-146S/fecc26ac-03ed-4f62-bdd5-ba35b7996c52/scratchpad/review-robots/backend/.pytest_cache/`
