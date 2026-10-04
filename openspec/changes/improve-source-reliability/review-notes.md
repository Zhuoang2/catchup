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
