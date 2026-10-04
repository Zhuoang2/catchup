# Design: improve-source-reliability

Status: awaiting user choice

## Solution Proposals

Context:
- Request (scope decided 2026-10-04): generic fetch reliability.
  - Send a descriptive User-Agent on every request.
  - Handle 429 with bounded `Retry-After` backoff, and show "rate limited" as its own state.
  - Reuse the preview's fetch on confirm.
  - Have the README state that Reddit support ends 2026-11-13.
  - Out of scope: the Reddit link-post extractor (#2, closed).
- Research Source: `research.md` sections "Fetching (`safe_fetch`)", "Confirm", "Collection during runs", "Evidence from manual verification", and "External facts" (Reddit rules, observed 403/429, RFC 6585 / RFC 9110 `Retry-After`).

### Shared by both proposals

- **User-Agent:** every request from `safe_fetch` (`backend/src/catchup/net/safe_fetch.py:70`) sends `CatchUp/<version> (+https://github.com/Zhuoang2/catchup)`. It is defined once and applies to all 6 call sites (`research.md`, "Fetching"). An optional `CATCHUP_USER_AGENT_CONTACT` env var appends a contact (e.g. `by /u/name` or an email), because Reddit's rules ask for one. Research observed that curl's default UA got 403 where a descriptive UA got 200.
- **`Retry-After` parsing:** both forms in RFC 9110 §10.2.3 (delay-seconds and HTTP-date in IMF-fixdate, RFC 850, or asctime) are parsed. A missing or invalid value counts as unknown. Reddit's 429 carried no `Retry-After` (research).
- **Rate limits as their own state:** a 429 becomes `FetchError("rate_limited", …, status_code=429, retry_after=…)` instead of the generic `fetch_failed` (`safe_fetch.py:131-134`). Preview and confirm return a 422 with code `rate_limited` and a "try again in about N seconds" message. The source list and run detail show "rate limited" for checks with HTTP 429 (`collection.py:35-46` already records `http_status`). The check outcome stays `failed` in the data, so the existing rule "a failed check is never `no_new_items`" holds (`openspec/specs/content-collection/spec.md:8-18`).
- **README:** the Supported sources section states that Reddit RSS support ends 2026-11-13 because Reddit is discontinuing RSS, citing the TechCrunch report.

---

### Proposal 1 — In-process handling: retry-once, short-lived preview cache, per-host spacing within a run

- Overview: Everything lives in the running process, with no schema change.
  - `safe_fetch` waits and retries once when a 429's `Retry-After` is short enough to fit its deadline.
  - Preview keeps the fetched feed in a small in-memory cache that confirm reads.
  - During a run, requests to the same host are spaced out.
- Key Changes:
  - `net/safe_fetch.py`:
    - User-Agent header and `Retry-After` parsing.
    - On 429, if `Retry-After` ≤ 10 s and the 30 s deadline allows, sleep and retry once; otherwise raise `rate_limited` with `retry_after`.
    - `FetchError` gains `retry_after`.
  - New `net/feed_cache.py`: a thread-safe dict mapping each feed URL to its fetched response. Entries expire after 10 minutes, the cache is capped at 50 entries, and it is lost on restart.
    - `discover` (`sources/discovery.py:49-90`) stores the final feed response.
    - `confirm` (`api/sources.py:86`) uses a fresh cache entry, if present, instead of re-fetching.
  - Per-host spacing within a run: a small in-memory limiter keeps at least 1 s between requests to the same host. It covers `check_source` and article extraction during runs (`runner.py:89-94`, `collection.py:13-33`), so several sources or articles on one host are not fetched back-to-back.
  - API and UI: `rate_limited` error code for preview and confirm; run detail and source list expose `http_status`. The Sources and Generate pages show "rate limited, try later".
  - Spec capabilities modified: `source-management`:
    - "Confirm and save a source" (confirm reuses a recent preview)
    - "Fetch user-supplied URLs safely" (identify the client; honor `Retry-After`)
  - Also modified: `content-collection` "Check every source on each run" (a rate-limited check is shown as rate limited).
  - No migration.
- Trade-offs:
  - Benefits:
    - Directly fixes both observed failures: confirm right after preview, and the default-UA block.
    - Small and contained: one new module, no schema change.
    - Fits the single-process, single-user design (D2).
  - Costs:
    - Cooldowns and the preview cache vanish on restart. After a restart, a source that was rate-limited is fetched again on the next run. Harmless, but not "polite memory".
    - A retry can add up to 10 s to one fetch.
    - The spacing is within one run only.
- Validation:
  - respx tests:
    - The User-Agent is on every request type (page, probe, declared feed, confirm, check, article).
    - `Retry-After: 3` → one retry, then success.
    - An HTTP-date `Retry-After` is parsed.
    - `Retry-After: 120` → no wait, `rate_limited` with `retry_after=120`.
    - No header → no retry, `rate_limited`.
    - The deadline is never exceeded (with injected time).
    - Preview then confirm → exactly one feed request.
    - Confirm after cache expiry → fetches again.
    - Two sources on one host in a run are spaced at least 1 s apart (injected clock).
  - UI: Vitest tests for the "rate limited" messages.
  - Manual: Reddit preview → confirm succeeds without the 15 s wait observed in the re-test (`test-report-add-core-digest-flow.md:172`).
- Open Questions:
  - Retry cap (10 s) and host spacing (1 s): acceptable defaults?
  - Should a 503 with `Retry-After` be treated like 429?

---

### Proposal 2 — Persistent politeness: stored per-host cooldowns, draft sources, and a `rate_limited` outcome

- Overview: Rate-limit state and previews are kept in the database.
  - A host that answered 429 is in cooldown until its `Retry-After` time (or a default backoff when there is none). Checks during the cooldown are skipped without contacting the server, even across restarts.
  - Preview saves a draft source with the fetched feed, and confirm promotes it.
  - A new check outcome, `rate_limited`, joins `new_items`, `no_new_items`, and `failed`.
- Key Changes:
  - Migration `0002`:
    - `host_cooldowns` table (host, `blocked_until`, last status, `X-Ratelimit-*` values).
    - `source_drafts` table (feed URL, fetched bytes, created at, expires at).
    - `source_checks.status` gains `rate_limited`.
  - `net/safe_fetch.py`:
    - User-Agent and `Retry-After` parsing, with no in-call retry.
    - Before each request, consult `host_cooldowns`.
    - After a 429, write the cooldown; default backoff without a header is 60 s, doubling up to 30 min.
    - Also record `X-Ratelimit-Remaining` and `X-Ratelimit-Reset` when present.
  - `api/sources.py`: preview writes a draft; confirm reads and deletes it, and falls back to fetching when it is missing or expired. Expired drafts are cleaned up on startup.
  - `collection.py` / `runner.py`: a source whose host is cooling down gets a `rate_limited` check without a request; the UI shows when it will be retried.
  - Spec capabilities modified:
    - `content-collection` "Check every source on each run" (a fourth outcome, `rate_limited`, which is neither `failed` nor `no_new_items`)
    - `source-management` "Confirm and save a source" and "Fetch user-supplied URLs safely"
- Trade-offs:
  - Benefits:
    - Remembers to be polite across restarts.
    - Never hammers a host that asked it to wait.
    - Scales better when many sources share a host (e.g. Substack or Medium publications).
    - A distinct `rate_limited` outcome is clearer in data and reports.
  - Costs:
    - A migration and two tables.
    - Sharing cooldown state between the API and run threads under SQLite's single writer.
    - Changing the outcome set touches the runner, run detail, the UI, and existing tests that assume three outcomes.
    - The main beneficiary of persistent cooldowns, Reddit, stops serving RSS on 2026-11-13 (research).
- Validation:
  - Migration test.
  - Cooldown honored across an app restart, and no request sent during the cooldown (respx call count).
  - Exponential default backoff without `Retry-After`.
  - Draft promoted on confirm; expired draft falls back to a fetch; startup cleanup.
  - The `rate_limited` outcome flows through run detail and the UI.
  - Existing three-outcome tests updated.
  - Manual: the same Reddit scenario as Proposal 1, plus a restart during a cooldown.
- Open Questions:
  - The default backoff schedule when no `Retry-After` is sent.
  - Whether `rate_limited` checks should count toward the possible-gap logic.

---

Recommendation: **Proposal 1.** It fixes both failures actually observed (the duplicate fetch on preview → confirm, and blocks against the default User-Agent) with one small module and no schema change, which fits the single-user, single-process design. Proposal 2's main payoff is persistent cooldowns for hosts that rate-limit often, and the host that did, Reddit, stops serving RSS in six weeks. Persistent cooldowns can be added later if deployment or real use shows the need.
