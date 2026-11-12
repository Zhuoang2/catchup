# Pin fetch connections: implementation checks

2026-11-09, branch `pin-fetch-connections`, starting commit `d356464`.
Group 1 implementation commit: `933a98c`.
All commands ran in the isolated worktree, not the user's running instance.
Backend commands used Python **3.12.13**. Tests and probes used no external
network or real sleeps; the response test connected only to its loopback listener.

## Commands and actual results

Backend commands ran from `backend/`; OpenSpec and Docker commands ran from
the repository root.

| Command / stage | Actual result |
| --- | --- |
| `UV_PYTHON=3.12 uv sync --offline --frozen` | Passed; installed 60 packages from the local cache, without changing dependency files. |
| `DO_NOT_TRACK=1 openspec status --change pin-fetch-connections --json` | Ready planning artifacts, `spec-driven` schema. |
| `DO_NOT_TRACK=1 openspec instructions apply --change pin-fetch-connections --json` | Ready; initially 0/4 implementation tasks complete. |
| `DO_NOT_TRACK=1 openspec list --json` | Confirmed this worktree's OpenSpec root. |
| `UV_PYTHON=3.12 uv run --offline pytest tests/test_safe_fetch.py -k test_connection_ -q`, before implementation | Expected red: **7 failed, 51 deselected**. Tests 2–5 recorded the hostname instead of the IP. Tests 1 and 7 reported `fetch_failed` and attempted the connection. Test 6 reported the generic fetch message and attempted the connection. No mock errors. |
| `UV_PYTHON=3.12 uv run --offline pytest tests/test_safe_fetch.py -k "not test_connection_" -q`, before implementation | **51 passed, 7 deselected**; all existing tests unchanged. |
| `UV_PYTHON=3.12 uv run --offline pytest tests/test_safe_fetch.py -q`, after implementation | **58 passed**. |
| `UV_PYTHON=3.12 uv run --offline pytest`, group 1 | **892 passed in 23.79s**. |
| `UV_PYTHON=3.12 uv run --offline pytest tests/test_safe_fetch.py -q`, after all mutations were restored | **58 passed in 1.37s**. |
| `git diff --check` | Passed. |
| `docker info --format '{{.ServerVersion}}'` | Local Docker daemon available, **29.8.0**. |
| Fetching-line check, before/after task 2.1 | Expected red before editing; passed afterward. Compared the entire document with the expected single-line replacement; all other text unchanged. |
| `UV_PYTHON=3.12 uv run --offline pytest`, group 2 final integration | **892 passed in 21.95s**. |
| `DO_NOT_TRACK=1 openspec validate pin-fetch-connections --strict` | Passed: change is valid. |
| `docker build -t catchup:pin-fetch-connections-local .` | Passed; built the updated backend with Python 3.12; unchanged frontend layers were cached. |
| `PATH="$PWD/backend/.venv/bin:$PATH" scripts/docker-smoke.sh catchup:pin-fetch-connections-local` | Passed **12/12** reported checks: health, API, HTML, manifest, service worker, offline page, preference write, framing headers, non-root process, database volume, excluded source/secrets, and persistence after restart. Only local loopback HTTP was used. The script cleaned up its container and volume. |

No frontend or extension source changed, and their standalone suites were not
run. No new statement-coverage measurement was made; the coverage summary
records the test counts without claiming a new percentage.

## Diagnosis and library probes

Ranked hypotheses, recorded after the seven tests went red:

1. **Unchecked hostname delegation:** the backend receives the hostname instead
   of a checked IP. Rechecking in the backend and delegating checked IPs should
   turn the connection tests green. **Confirmed.**
2. **Faulty pre-request address rule:** existing private/mixed-address tests
   would also fail. Rejected by the 51 passing baseline tests.
3. **Exception translation hides refusal:** a backend `FetchError` would lose
   its code or message. Rejected by a network-free probe.

A fresh read-only Droid preflight saw only the code and tasks, not the design,
proposal, or spec deltas. It found no concrete contradictions and identified
library assumptions to probe. A `UV_PYTHON=3.12 uv run --offline python` probe,
with DNS and socket connections blocked, confirmed `OSError` → `ConnectError`,
`TimeoutError` → `ConnectTimeout`, private backend wiring, unchanged `FetchError`
propagation, and `respx` interception before the backend. The TLS test exercises
the installed library's wrap signature and verification settings.

## Required mutations

Each mutation ran alone with:

`UV_PYTHON=3.12 uv run --offline pytest tests/test_safe_fetch.py -k test_connection_ -vv --tb=short`

Test numbers below match task 1.1:

| Number | New test in `backend/tests/test_safe_fetch.py` |
| --- | --- |
| 1 | `test_connection_rejects_dns_rebinding` |
| 2 | `test_connection_uses_checked_address` |
| 3 | `test_connection_tries_checked_answers_in_order` |
| 4 | `test_connection_https_keeps_hostname_and_certificate_checks` |
| 5 | `test_connection_response_through_checked_address_keeps_host` |
| 6 | `test_connection_reports_unresolvable_host` |
| 7 | `test_connection_rejects_mixed_dns_answers` |

| Mutation | Tests that failed | Actual result / reason |
| --- | --- | --- |
| M1: delegate `host` instead of the checked IP | 2, 3, 4, 5 | **4 failed, 3 passed**; recorded hostname instead of checked addresses. |
| M2: resolve in the backend without applying the address rule | 1, 6, 7 | **3 failed, 4 passed**; connections attempted for blocked/mixed answers; raw `gaierror` escaped for test 6. |
| M3: leave `_pool._network_backend` unchanged | 1–7 | **7 failed**; hostname delegation and original generic errors returned. |
| M4: raise immediately after the first failed answer | 3 | **1 failed, 6 passed**; second checked IP never attempted. |
| M5: catch only `httpcore.ConnectError` | 3 | **1 failed, 6 passed**; timeout prevented trying the second checked IP. |
| M6: call `socket.create_connection` and return `SyncStream` directly | 2, 3 | **2 failed, 5 passed**; raw `OSError` and `TimeoutError` escaped rather than becoming `FetchError`. |
| M7: build the transport with `verify=False` | 4 | **1 failed, 6 passed**; certificate verification and hostname checking were both off. |

All seven final mutation runs exited 1 for the intended behavior, with 51
existing tests deselected. The source was compared with its baseline after
each restoration and matched exactly.

Harness retries, excluded from these results: the first M1 patch lost
indentation and failed collection. A later M2 inverse patch matched the shared
helper instead of the backend, invalidating subsequent runs with recursion.
Both harness mistakes were corrected, a green seven-test baseline was observed,
and all seven mutations were rerun with unique anchors and exact restoration
checks. No production workaround or plan change was made.

## Modified requirement: scenario mapping

There are **seven new tests**. Every existing test remains unchanged.

| Scenario / contract | Tests / evidence |
| --- | --- |
| Internal address | Existing `test_rejects_non_public_addresses`, `test_rejects_mixed_dns_results`, `test_nat64_embedded_private_address_blocked`; public NAT64 guard `test_nat64_embedded_public_address_allowed`. |
| Redirect to an internal address | Existing `test_redirect_to_metadata_is_blocked_before_request`. |
| DNS answer changes after the check | New tests 1 and 7 verify refusal without a connect attempt; test 6 verifies connect-time resolution failure. |
| Slow or oversized response | Existing `test_timeout`, `test_slow_drip_aborts_after_wall_clock_deadline`, `test_oversized_stream`, and both `test_six_mb_feed_allowed_with_feed_limit` cases. |
| Large podcast feed | Existing `test_six_mb_feed_allowed_with_feed_limit` exercises exactly 6 MB with/without Content-Length, 32 MB acceptance, and 5 MB/4 MB rejection. Existing `test_sources_api.py::test_large_feed_preview_and_cache_miss_confirm` verifies oversized-feed preview and confirmation at the API seam. |
| Confirm a large feed after the preview expired | Existing `test_sources_api.py::test_expired_preview_refetches_feed` covers expiration/refetch; `test_large_feed_preview_and_cache_miss_confirm` covers large-feed cache-miss refetch/save. These are separate existing checks, not one combined 6 MB expiration test. |
| Connect only to checked addresses, preserving the request host and HTTPS verification | New tests 2–5; mutations M1 and M7. Test 3 verifies fallback after timeout followed by connection failure; test 5 reads the actual HTTP Host header and response body. |

## Checks left to Claude Code review

**Not performed:** the design's live check on a throwaway test container,
not port 8800: preview a public HTTPS feed and a redirecting feed, then verify
that `http://127.0.0.1/` is refused. This requires external network and is left
to review, as specified. DNS rebinding itself is tested only with mocked DNS.
Connect-time NAT64 is not tested, as explicitly deferred by the task plan.


## Claude Code review (2026-11-09)

Review of `d356464..24f561b` in a separate worktree.

### Checks re-run by Claude

| Command | Result |
| --- | --- |
| `UV_PYTHON=3.12 uv run pytest -q` (before the review tests) | **892 passed** |
| `DO_NOT_TRACK=1 openspec validate pin-fetch-connections --strict` | valid |
| `docker build -t catchup:review-68 .` and `scripts/docker-smoke.sh catchup:review-68` | **12/12** passed |

### Live check (performed)

A throwaway container from `catchup:review-68` ran on `127.0.0.1:8787` with its own volume, not port 8800. Each URL went through `POST /api/sources/preview`:

| URL | Result |
| --- | --- |
| `https://simonwillison.net/atom/everything/` | previewed, 5 items |
| `http://simonwillison.net/` | redirected to HTTPS and found `https://simonwillison.net/atom/everything/`, 5 items |
| `https://terrytao.wordpress.com/` | found `https://terrytao.wordpress.com/feed/`, 5 items |
| `http://127.0.0.1/` | `blocked_address`, "The source address is not allowed." |
| `http://localhost:8000/` | `blocked_address`, "The source address is not allowed." |

Real HTTPS fetches still pass certificate checks when the connection goes to the checked IP. The container logs had no errors. DNS rebinding itself is checked only by the unit tests.

### Findings and outcomes

- **`/code-review` (high): no real defect.** All five findings are recorded, not fixed:
  - **Fails open on an `httpx` rename.** If `httpx` renamed `_pool._network_backend`, the assignment would do nothing at runtime. The connection tests would fail, and `uv.lock` pins the checked versions. A runtime guard would change source code, so it is left to the user.
  - **`assert` under `python -O`.** `assert last_error is not None` cannot fail: the helper never returns an empty list.
  - **Last error hides a timeout.** When an earlier answer times out and a later one is refused, the fetch reports "The source could not be fetched." instead of "The source fetch timed out." The code stays `fetch_failed`. Marginal.
  - **Full connect timeout per answer.** Each answer gets the full connect timeout. `socket.create_connection` did the same before the change.
  - **Duplicated test helper.** Churn.
- **Independent spec review: no missing or wrong behavior.**
  - M1–M7 were killed as reported above.
  - Of its 28 own mutations, these survived:
    - equivalent: A5 `except Exception`, A11 dropping `local_address`/`socket_options`, A14 the client without `trust_env=False`, A24 the port taken from the answer;
    - marginal, recorded: A13 the transport without `trust_env=False` (only `SSL_CERT_FILE`/`SSL_CERT_DIR` from the environment), A15 NAT64 at connect time (deferred by the plan), A16–A18 the helper's lookup-error branches (untested before the change too);
    - real test gaps, fixed below: A20, A21, A12, A9, A26.

### Tests added in the review commit

Each test passes on the implementation. Each named mutation made it fail and was then restored.

| Test | Gap | Mutation that now fails it |
| --- | --- | --- |
| `test_connection_uses_the_answer_it_checked` (DNS answers public, public, then `127.0.0.1`) | checking one lookup but connecting to a later one | A20: check `_public_answers`, then connect to a fresh `getaddrinfo` → connected to `127.0.0.1` |
| `test_connection_tries_next_answer_after_refusal_with_connect_timeout` (first answer refused, second times out) | the next answer after a refusal; the connect timeout passed through; the message of a final connect timeout | A21: fall through only on `ConnectTimeout`; A12: pass `timeout=None`; A9: raise a fresh `ConnectError` |
| `test_address_check_runs_before_budget_and_spacing` | the address check runs before the fetch budget and host spacing (design D1; no test protected it before) | A26: move `_check_address` after the budget and spacing |

After the review commit: `tests/test_safe_fetch.py` **61 passed**; the full backend suite (`UV_PYTHON=3.12 uv run pytest -q`) **895 passed**; strict validation passed.

### Runtime check added on the user's decision (2026-11-12)

The user approved the merge and asked for the optional runtime check from the `/code-review` finding "Fails open on an `httpx` rename". The fix is in Claude's review commit, a user-approved exception to D-023 (about 3 source lines):
- `_client()` raises `RuntimeError("Cannot install the connect-time address check; refusing to fetch.")` when the transport's pool has no `httpcore.SyncBackend` under `_network_backend`.
- Test `test_refuses_to_fetch_when_the_connect_check_cannot_be_installed` replaces the pool with an empty object. It expects that error and no connection attempt.
- Mutation G1 (guard removed) made the test fail. After restoring the guard: `tests/test_safe_fetch.py` **62 passed**, and the full backend suite **896 passed**.
- After the guard, Claude rebuilt `catchup:review-68`. The smoke script passed **12/12**. A new test container on port 8787 previewed `https://simonwillison.net/atom/everything/` and `http://simonwillison.net/` (5 entries each), and refused `http://127.0.0.1/` as `blocked_address`. The logs had no `RuntimeError`.
