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
