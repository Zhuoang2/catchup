# Test report: refactor-context-fetch-budget-and-robots

Date: 2026-11-16. Issues: #90 and #60. Runner: Factory Droid, GPT-6.1 Sol.
Starting commit: `7d9c934`. All five task groups are complete.

Implementation commits: `668e404` (group 1), `b6e8f6a` (group 2),
`00c2627` (group 3), and `ebbdd11` (group 4).

## Final checks

| Directory | Command | Actual result |
| --- | --- | --- |
| `backend/` | `uv run pytest` (environment below) | Exit 0, **958 passed in 29.75s**. Python 3.12.13, pytest 9.1.1, respx 0.23.1. |
| Repository root | `DO_NOT_TRACK=1 openspec validate refactor-context-fetch-budget-and-robots --strict` | Exit 0, change is valid. |
| Repository root | `DO_NOT_TRACK=1 openspec list --json` | Exit 0, this worktree is the OpenSpec root; 8/9 tasks complete before writing this final report. |
| Repository root | `DO_NOT_TRACK=1 openspec instructions apply --change refactor-context-fetch-budget-and-robots --json` | Exit 0, final progress **9/9**, state `all_done`. |

All final checks passed. The planned red tests and mutation failures below
are intentional verification outcomes, not outstanding failures.

The change adds **17 test functions / 18 collected cases**: six safe-fetch
cases, four robots cases, five gather cases, and three comments cases.
Only the existing `test_robots_request_uses_shared_budget` changes its
expectation; the safe-fetch import also adds the new error as task 1.2 requires.
Every other existing test remains unchanged and passes.
All **17 named mutations** fail their required tests in **18 isolated runs**
(O3 has both required forms), and the implementation is restored.

## Environment and commands

All pytest commands run from this worktree's `backend/`. No dependencies
are installed or changed. Commands reuse the existing Python environment
with these environment variables:

```sh
UV_PROJECT_ENVIRONMENT="<existing checkout>/backend/.venv"
UV_NO_SYNC=1 UV_OFFLINE=1 PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$PWD/src"
```

`PYTHONPATH` selects this worktree's source, not the environment's editable
installation. Syncing is disabled. HTTP/DNS routes in the new tests are mocked;
clocks and waits are virtual. The existing safe-fetch transport regression
includes a loopback-only socket test. No external source requests are made.

The plan's AI-log entry records Claude Code's fresh-agent preflight
and library probes before this run.

## Scenario-to-test mapping

Modified requirement: **Gather related context for website items**.
Paths below are relative to `backend/tests/`. “Existing” means unchanged
by this change. Complementary unit and runner tests cover some narratives
rather than one fixture reproducing every narrative detail.

| Spec scenario | Tests | Provenance |
| --- | --- | --- |
| Short post with linked pages | `test_context_links.py::test_keeps_body_order_and_applies_limit_after_filtering`; `test_context_gather.py::test_runner_stores_three_links_in_order_and_ignores_tags` | Existing |
| Author replies in comments | `test_context_comments.py::test_marked_author_replies_include_parent_text`; `test_context_gather.py::test_author_reply_context_and_disable_switch` | Existing |
| robots.txt disallows a linked page | `test_context_robots.py::test_disallow_for_catchup_and_fetch_once_per_host`; `test_context_gather.py::test_robots_refusal_and_failed_pages_do_not_fail_run` | Existing |
| robots.txt answers a server error | `test_context_gather.py::test_robots_server_error_skips_the_sites_pages` | Existing |
| robots.txt cannot be reached | `test_context_gather.py::test_unreachable_robots_keeps_other_sites` | Existing |
| Link redirects to a disallowed page | `test_context_gather.py::test_redirect_to_disallowed_page_is_not_requested` | New: no target request, no stored context, successful run, one completed fetch |
| Link redirects to a site whose robots.txt cannot be read | `test_context_gather.py::test_redirect_to_site_with_unreadable_robots_is_not_requested` | New: no target request; exactly the other site's context retained |
| One site written three ways | `test_context_gather.py::test_three_spellings_of_one_site_share_robots`; `test_context_robots.py::test_one_robots_read_for_three_spellings` | New: one robots read; rules apply to all three links; only `/a` and `/c` stored |
| robots.txt missing | `test_context_gather.py::test_runner_stores_three_links_in_order_and_ignores_tags`; `test_context_robots.py::test_missing_or_restricted_robots[404-True]` | Existing |
| Per-run fetch limit reached | `test_context_gather.py::test_budget_leaves_unreached_items_ungathered_and_retries_do_not_refetch`; `test_context_gather.py::test_second_item_keeps_partial_context_in_successful_digest` | Existing |
| Article links on the same site | `test_context_links.py::test_taxonomy_is_a_whole_first_segment_and_www_is_same_site` | Existing, explicitly retains `/archives/10000`; runner storage is covered by existing linked-page tests |
| Link redirects to a login page | `test_context_gather.py::test_link_redirecting_to_login_does_not_store_the_final_page` | Existing |
| Context gathered once | `test_digest_runner.py::test_failed_run_reuses_gathered_context_without_fetching_again` | Existing |

Additional new tests pin per-request checking order and callback deadline
exclusion, shared budget exception type/propagation, scheme/port separation,
IPv6 brackets, last-unit failure progress, lazy comment-feed fetching,
empty-page fallback, and skipping only an unparseable feed entry.
Existing tests still pin reply ordering, parent selection, reply/text caps,
linked-text caps, audio/YouTube exclusion, captured replies, partial context,
and cached-summary invalidation.

## Test-first results

Commands below use `uv run pytest`, with the listed selection and
`--tb=short -q`.

| Stage | Selection | Actual result |
| --- | --- | --- |
| Group 1 baseline | `tests/test_safe_fetch.py` | 62 passed in 2.51s |
| 1.1 red | `tests/test_safe_fetch.py` | 6 failed, 62 passed in 1.85s. Missing `BudgetExhausted` import and unknown `allow` argument, as planned. |
| 1.2 green | `tests/test_safe_fetch.py` | 68 passed in 1.65s |
| 1.2 regression | Full suite | 946 passed in 33.49s |
| Group 1 restored | `tests/test_safe_fetch.py` | 68 passed in 5.99s |
| 2.1 red | `tests/test_context_robots.py` | 5 failed, 20 passed in 0.18s. Both budget cases returned instead of raising; three robots reads for three spellings; two HTTP reads with explicit `:80`; uppercase IPv6 missed the lowercase route. |
| 2.2 green | `tests/test_context_robots.py` | 25 passed in 0.11s |
| 2.2 regression | Full suite | 950 passed in 27.18s |
| Group 2 restored | `tests/test_context_robots.py` | 25 passed in 0.12s |
| 3.1 red | `tests/test_context_gather.py` | 3 failed, 38 passed in 4.26s. Both refused redirect targets were requested; last-unit failure counted 0, expected 1. The three-spellings test and all existing tests passed. |
| 3.2 green | `tests/test_context_gather.py` | 41 passed in 4.38s |
| 3.2 regression | Full suite | 954 passed in 25.26s |
| Group 3 restored, README updated | `tests/test_context_gather.py tests/test_readme_context.py` | 42 passed in 4.57s |
| 4.1 red | `tests/test_context_comments.py tests/test_context_gather.py` | 4 failed, 58 passed in 4.54s. Unknown `fetch_feed`, feed-entry `ParserError`, empty-page `AttributeError`, and no feed request for empty post, as planned. |
| 4.2 callback/parser green, before set | Same selection | 62 passed in 5.25s |
| 4.2 set green | Same selection | 62 passed in 6.00s |
| 4.2 regression | Full suite | 958 passed in 30.01s |
| Group 4 restored | Same two-module selection | 62 passed in 4.48s |

Group 3's structural search (`EXHAUSTED|attempted|exhausted|budget\[0\]`
in `context/gather.py`) returned exactly one line: the unreached-item skip
at line 72.
After group 4, the structural search for `comment ')` in `context/gather.py`
returned no matches: only `author_replies` checks comment markup.

## Mutations

Each mutation is applied alone, run, and immediately restored. The batch
mutation runners use a `finally` block; the separate O1 run restored its
patch immediately after the observed failure.
Source equality with the pre-mutation content is checked after each group.
Every mutation below exited 1. Selections use `uv run pytest` with
`--tb=short -q`; test names are node IDs in the stated test module.

### Group 1: `tests/test_safe_fetch.py`

| Mutation | Selection / failed tests | Actual result |
| --- | --- | --- |
| S1: `allow` only on hop 0 | `test_refused_redirect_target_is_not_requested` | 1 failed in 3.14s: no `FetchError` raised. |
| S2: take budget before `allow` | `test_refused_redirect_target_is_not_requested`; `test_allow_runs_after_the_address_check_and_before_budget_and_spacing` | 2 failed, 1 passed in 2.03s. Redirect budget `[3]`, expected `[4]`; allowed-address refusal budget `[0]`, expected `[1]`. Blocked-address case passes. |
| S3: do not extend deadline | `test_time_in_allow_does_not_count_against_the_deadline` | 1 failed in 2.35s: fetch timed out. |
| S4: raise plain `FetchError` | `test_budget_exhausted_is_a_fetch_error` | 1 failed in 2.14s: wrong exception type. |

### Group 2: `tests/test_context_robots.py`

| Mutation | Selection / failed test | Actual result |
| --- | --- | --- |
| O1: raw `netloc` origin | `test_one_robots_read_for_three_spellings` | 1 failed in 0.05s: 3 reads, expected 1. |
| O2: hostname-only cache key, preserving normalized fetch URL | `test_scheme_and_other_ports_stay_separate_origins` | 1 failed in 0.18s: route counts `[1, 0, 0]`, expected `[1, 1, 1]`. |
| O3-return: cache `False` and return on budget error | `test_budget_running_out_in_a_robots_redirect_propagates` | 1 failed in 0.04s: first call did not raise. |
| O3-reraise: cache `False` and re-raise on budget error | Same test | 1 failed in 0.03s: second call did not raise. |
| O4: omit IPv6 brackets | `test_ipv6_host_keeps_its_brackets` | 1 failed in 0.04s: returned `False`, expected `True`. |

An initial mutation patch was rejected before any source changed or test ran.
The corrected patch then ran as O1 above.

### Group 3: `tests/test_context_gather.py`

| Mutation | Selection / failed tests | Actual result |
| --- | --- | --- |
| G1: return `None` for budget exhaustion | `test_comment_feed_budget_cutoff_keeps_link` | 1 failed in 1.89s: progress `(3, 3)`, expected `(3, 2)`. |
| G2: translate every last-unit fetch failure into exhaustion | `test_failed_request_on_last_budget_unit_counts_as_read` | 1 failed in 1.51s: progress `(2, 0)`, expected `(2, 1)`. |
| G3: remove unreached-item skip | `test_budget_leaves_unreached_items_ungathered_and_retries_do_not_refetch` | 1 failed in 1.48s: second item's status `none`, expected `None`. |
| G4: check robots only before `safe_fetch`, without `allow` | `test_redirect_to_disallowed_page_is_not_requested`; `test_redirect_to_site_with_unreadable_robots_is_not_requested` | 2 failed in 1.64s: both forbidden targets requested. |

### Group 4

| Mutation | Selection / failed tests | Actual result |
| --- | --- | --- |
| C1: fetch feed despite comment markup | `tests/test_context_comments.py::test_feed_function_is_called_only_without_comment_markup` | 1 failed in 0.05s: callback called, expected no call. |
| C2: omit feed's total increase | `tests/test_context_gather.py::test_comment_feed_fallback_counts_extra_fetch_and_saves_named_reply` | 1 failed in 1.65s: progress `(1, 2)`, expected `(2, 2)`. |
| C4: restore missing `html.ParserError` | `tests/test_context_comments.py::test_empty_page_counts_as_no_comment_markup`; `tests/test_context_gather.py::test_unparseable_post_page_falls_back_to_comment_feed` | 2 failed in 1.91s: `AttributeError` and no feed request. |
| C3: require author before invoking feed callback | `tests/test_context_gather.py::test_comment_feed_budget_cutoff_keeps_link` | 1 failed in 1.66s: progress `(2, 2)`, expected `(3, 2)`. |
| C5: re-raise unparseable feed-entry error | `tests/test_context_comments.py::test_unparseable_feed_entry_is_skipped` | 1 failed in 0.07s: `ParserError` instead of retaining the real reply. |

## Timing: 2,000 sibling comments

Scratch Python ran as `uv run python /dev/stdin` with a heredoc, so its script
path was outside the repository without creating a file to delete outside
the worktree. No scratch file is committed or left behind.

The identical 261,815-byte page has 2,000 sibling `li.comment.bypostauthor`
nodes, each with a `span.fn` containing Writer and a `div.comment-content`
containing `Reply {i}.`. Both implementations return replies 0 through 9
in order. After one checked warmup, `timeit.repeat` ran five single calls.
D4 was present on both sides; only D5's set change differed.

| Version | Five seconds-per-call measurements | Median |
| --- | --- | --- |
| List lookup, before D5 | 0.107799, 0.111862, 0.112295, 0.115756, 0.117328 | 0.112295s |
| Set lookup, initial measurement overlapping the narrow test suite | 0.036641, 0.038851, 0.040037, 0.039697, 0.039149 | 0.039149s |
| Set lookup, repeated without concurrent tests for a comparable measurement | 0.034347, 0.034937, 0.033448, 0.034083, 0.033588 | 0.034083s |

The serial medians show about 3.29x faster extraction on this synthetic page.
This is a local timing observation, not a performance guarantee or test threshold.

## Review-only checks

- Docker build and `scripts/docker-smoke.sh`: not performed. Task 5.1 assigns
  these to Claude Code at review.
- Live comparison from design Migration Plan: not performed. Claude Code
  runs it at review on fresh instances, neither on port 8800.
- No pushes, tags, releases, PRs, Docker cleanup, or requests to port 8800.
- Frontend and extension checks: not run; neither area changed.
- Statement coverage: not remeasured; the coverage summary distinguishes
  this run's test counts from the earlier measured percentage.

## Review by Claude Code

Date: 2026-11-16. Range reviewed: `7d9c934..f7254bf`, in a separate review
worktree. Review method: D-016 (`/code-review` at high effort, an independent
spec sub-agent with mutations, Claude Code's own checks).

### Checks

| Check | Result |
| --- | --- |
| `uv run pytest` in `backend/`, at `f7254bf` | **958 passed**. |
| `uv run pytest` in `backend/`, with the review edits | **961 passed** (three new test cases). |
| `DO_NOT_TRACK=1 openspec validate refactor-context-fetch-budget-and-robots --strict` | Valid. |
| `docker build -t catchup:refactor90-local .` at `f7254bf` | Passed. |
| `scripts/docker-smoke.sh catchup:refactor90-local` | Passed all **12 checks**; no container or volume left. |

### Live comparison

- **Setup.** Two images, one built from a clean `main` worktree at `9d6866a`
  and one from the branch at `f7254bf`. Each ran in its own container, on a
  local port (not 8800), with a fresh volume. Both used a local
  OpenAI-compatible stub model, and the same public feed (Simon Willison's
  Weblog).
- **Run.** One digest on each, one after the other.
- **Result.** Both runs succeeded with 5 items, and "Linked pages read" ended
  at 20 of 22 on both. The 45 stored rows (item link, `context_status`,
  context kind, URL, and text length) were identical. So no redirect target in
  that feed was refused, and the refactor changed nothing observable on it.
- Both containers and their volumes were removed, and the stub was stopped.

The redirect and spelling cases are covered by the tests only, as the design
says.

### Findings

`/code-review` (high) reported 5 findings:

| Finding | Decision |
| --- | --- |
| Droid's log entry has no session id | Confirmed; added to the log. |
| `RobotsCache.allowed` raises on a URL without a host or with another scheme | Latent: its only caller, `safe_fetch`, checks the address first. Recorded. |
| `except BudgetExhausted: raise` in the link-extraction handler is dead code | Confirmed; removed (two lines). |
| The feed-entry parse catches only `ParserError` | Rejected: a probe showed that feedparser removes the encoding declaration that would raise `ValueError`. |
| `fetch_feed` is a closure defined for each item | Churn (D-023 d); recorded. |

The spec sub-agent found no defect. It re-ran the planned red stages, which
matched this report. Of its 36 mutations, 23 were caught. Survivors and decisions:

| Mutation | Decision |
| --- | --- |
| S8: treat an error raised by `allow` as a refusal | Test gap (c). `test_comment_budget_cutoff_keeps_link_without_requesting_post` now also checks `(context_total, context_done) == (2, 1)`. |
| G8: put back the in-loop budget `break` | Test gap (c). New `test_refused_links_count_as_read_once_budget_is_used`, first case: a link refused by cached rules after the budget is used is counted, `(3, 2)`. |
| G9: turn a refusal on the last unit into `BudgetExhausted` | Test gap (c). Second case of the same test: `(1, 1)`. |
| S7: skip `allow` on the retry, and on later hops | Test gap (c): it would also skip robots.txt for a redirect after a retry. New `test_allow_runs_again_on_retry_and_later_hops`. |
| S5, S12: reset the deadline, or shift it twice as far | Marginal: a redirect chain could get more than 30 seconds. Recorded. |
| C8: drop the check for an entry without a summary | Marginal, and older than this change. Recorded. |
| S9, R1, G5, G6, G13, C11 | Equivalent. G5's code was removed. |

The sub-agent also noted:
- robots.txt refusals are now logged at INFO ("Context fetch skipped
  (robots_disallowed)"). This is harmless, and recorded;
- the D3 progress effect also applies to an item's post page, and to items
  with captured replies. design D3 now says so;
- one IPv6 address written two ways still reads robots.txt twice. It is now
  a Non-Goal;
- Droid's `coverage-summary.md` entry is accurate.

### Review mutations

| Mutation | Result with the review edits |
| --- | --- |
| S7 | Fails `test_allow_runs_again_on_retry_and_later_hops`. |
| S8 | Fails `test_comment_budget_cutoff_keeps_link_without_requesting_post`. |
| G8 | Fails the first case of `test_refused_links_count_as_read_once_budget_is_used`. |
| G9 | Fails both cases of `test_refused_links_count_as_read_once_budget_is_used`. |

All four passed the full suite before the review edits (the sub-agent's run).
