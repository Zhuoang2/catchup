# Review notes: improve-source-reliability

2026-10-04. Implemented tasks 1.1–4.2 in order on `improve-source-reliability` (created from `main` at `8c2ec90`). Groups 1–3: `873a1b2`, `3d75ce9`, `3696790`; group 4 is committed with this report. Planning artifacts (`proposal.md`, `design.md`, spec deltas) were not changed.

| Group | Verification |
| --- | --- |
| 1, User-Agent and retry | `uv run pytest tests/test_safe_fetch.py -q`: 42 passed; exact default/contact/redirect headers, date forms, 429/503, deadline, budget and redirect cases. |
| 2, preview reuse | `uv run pytest tests/test_feed_cache.py tests/test_discovery.py tests/test_sources_api.py -q`: 40 passed; TTL, cap, pop, final URL from direct/declared/probed paths, expiry and no-preview fallback. |
| 3, spacing and rate-limit status | Focused backend checks: 108 passed; focused page tests: 13 passed; `npm run build` passed. Fake clocks verify same-host spacing and no different-host delay; API/UI tests cover rate-limit messages. |
| 4, docs and mapping | `uv run pytest`: 197 passed; `uv run pytest --cov=catchup --cov-report=term`: 197 passed, 96% total coverage; `npm test -- --run`: 22 passed; `npm run build` passed; `openspec validate improve-source-reliability --strict`: valid. The report audit matched 11/11 spec scenarios and checked 28 backend test references. README and commented `.env.example` variable checked. |

All automated tests block unmocked DNS/sockets, use temporary test data and fake model credentials, and avoid real sleeps with patched hooks and injected clocks. The initial asctime parser, zero-delay sleep assertion and old end-to-end request-count assertion failed and were corrected; see `docs/process/test-report-improve-source-reliability.md`.

**Manual verification remaining:** With the reviewer/user, try Reddit preview → confirm and inspect an actual outgoing User-Agent. Live Reddit and provider access were not attempted. Reddit RSS support is expected to end on 2026-11-13.

The GitHub project board was not modified in this implementation session. The issue remains open until the change is reviewed and archived.

## Claude Code review (2026-10-04)

- Re-ran in a fresh worktree:
  - 197 backend tests, 96% coverage; `feed_cache`, `host_spacing`, and `rate_limit` at 100%, `safe_fetch` at 93%
  - 22 frontend tests, build, `npm audit` (0)
  - strict validation; apply state `all_done` (9/9)
  - no `backend/data` created
  - report audit by script: 11/11 scenarios mapped, all 21 cited tests exist
- Code read in full. Confirmed:
  - The rate-limit retry repeats the address check, budget, and spacing, does not consume a redirect hop, and gives up after one retry.
  - `rate_limited` during probing is re-raised instead of falling through to `no_feed`.
  - The cache is keyed by the final feed URL in all discovery paths, locked, capped, and popped on use.
  - One shared `RATE_LIMIT_PREFIX` constant.
  - The conftest makes any real `safe_fetch` sleep fail the test.
  - `Retry-After` parsing checked by hand for seconds, IMF-fixdate, RFC 850, asctime, past dates, and invalid values.
- The end-to-end assertion change (feed requests 5 → 4) is legitimate: it verifies the new reuse-on-confirm requirement.
- Verdict: **no required fixes.** Low-severity notes, not fixed:
  1. `user_agent()` reads `CATCHUP_USER_AGENT_CONTACT` from the environment on each call instead of using the app's `Settings`. Startup validation still runs, but a contact passed only through `Settings` (e.g. in tests) does not reach the header.
  2. `HostSpacer.wait` sleeps while holding its lock, which would serialize waits for different hosts if several threads shared one spacer. Today only the runner thread, or a single confirm request, uses each spacer.
- Manual verification passed (see the test report).
