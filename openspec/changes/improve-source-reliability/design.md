# Design

Status: Proposal 1 chosen by the user on 2026-10-04 (in-process handling). Defaults accepted: retry once when `Retry-After` ≤ 10 s; treat 503 with `Retry-After` like 429; preview cache of 10 minutes with at most 50 entries; ≥ 1 s per-host spacing within a run.

## Context

See `proposal.md` for motivation and `research.md` for the current code. All source fetching goes through `safe_fetch` (`backend/src/catchup/net/safe_fetch.py:60-137`), which today:
- sends httpx's default User-Agent
- turns every non-2xx response into a generic `fetch_failed` without reading headers
- keeps no state between calls

Preview (`sources/discovery.py:49-90`) and confirm (`api/sources.py:86`) fetch the same feed back-to-back. The runner checks sources sequentially (`digest/runner.py:89-94`). Reddit's rules ask for a descriptive User-Agent; it returned 403 to a default UA and 429 without `Retry-After` under repeated requests (`research.md`, "External facts").

## Goals / Non-Goals

**Goals:**
- Every request identifies CatchUp.
- Short server-requested waits are honored once; long or unknown waits fail fast with a clear "rate limited" message.
- Preview → confirm makes one feed request, not two.
- Requests to one host within a run are spaced out.
- The README is honest about Reddit's RSS end date.

**Non-Goals:**
- Persistent cooldowns across restarts, draft sources, or a fourth check outcome. These were Proposal 2, rejected.
- Reddit link-post extraction (#2, closed: Reddit RSS ends 2026-11-13).
- OAuth access to Reddit's API.
- Global rate limiting across concurrent runs. Only one run is active at a time (D2 of `add-core-digest-flow`).

## Decisions

### D1. In-process handling (chosen over persistent politeness)
- Rate-limit handling, the preview cache, and host spacing all live in memory. There is no migration.
- **Alternative considered (Proposal 2):**
  - What it was: per-host cooldowns and draft sources stored in SQLite, plus a new `rate_limited` check outcome.
  - Why it was rejected:
    - It needs a migration, two tables, and shared writes between API and run threads under SQLite's single writer.
    - The outcome set would change across runner, API, UI, and tests.
    - Its main beneficiary, Reddit, stops serving RSS on 2026-11-13.
  - Persistent cooldowns can be added later if deployment shows a need.

### D2. User-Agent
- Value: `CatchUp/<version> (+https://github.com/Zhuoang2/catchup)`. `<version>` is the installed package version (`importlib.metadata`, falling back to `0.0.0`).
- If `CATCHUP_USER_AGENT_CONTACT` is set, `; <contact>` is appended inside the parentheses, e.g. `CatchUp/0.1.0 (+https://github.com/Zhuoang2/catchup; by /u/example)`.
- The contact must be printable ASCII without CR/LF and at most 100 characters. Otherwise startup fails with a clear configuration error, which prevents header injection.
- The header is set on the `httpx.Client` in `safe_fetch`, so it covers all 6 call sites and every redirect hop and retry.

### D3. `Retry-After` and retry policy
- Parsing (RFC 9110 §10.2.3):
  - delay-seconds is `1*DIGIT`.
  - HTTP-date is accepted in IMF-fixdate, RFC 850, and asctime formats, all in UTC.
  - A date in the past means 0.
  - Anything else counts as unknown (`None`).
- Policy inside one `safe_fetch` call:
  - On **429**, or **503 with a parseable `Retry-After`**: if no retry has happened yet, `retry_after` is known and ≤ 10 s, and the remaining deadline exceeds `retry_after` + 1 s, then sleep `retry_after` and repeat the same request once.
  - Otherwise raise `FetchError("rate_limited", message, status_code, retry_after=…)`.
  - Message: "The source is rate limiting requests. Try again in about N seconds." when N is known; "…Try again later." otherwise.
  - A 503 without `Retry-After` keeps today's `fetch_failed`.
  - A retry counts against the probing `budget` like any request.
- `FetchError` gains an optional `retry_after: int | None`.
- The sleep function is a module-level hook (default `time.sleep`) so tests can patch it and never sleep for real.

### D4. Preview cache reused by confirm
- New `net/feed_cache.py`, a `FeedCache` class with these properties:
  - It is thread-safe (lock).
  - It holds at most 50 entries, evicting the oldest.
  - Its TTL is 600 s, measured with an injectable monotonic clock.
- The cache lives on `app.state.feed_cache`, created in `create_app`, so tests get a fresh one per app.
- `discover(url, cache=None)` stores the final feed `FetchResponse` under its final URL (`response.url`, which is what preview returns as `feed_url`).
- `confirm` pops a fresh entry for `feed_url` and parses it. If there is none, it fetches as before.
- The entry is popped, so a second confirm, which is refused as a duplicate anyway, would fetch again.

### D5. Per-host spacing within a run
- New `net/host_spacing.py`, a `HostSpacer` class:
  - Its configuration is `min_interval=1.0` with injectable clock and sleep.
  - `wait(url)` sleeps just enough so that consecutive requests to the same host (case-insensitive hostname) are at least 1 s apart.
  - It is thread-safe.
- `safe_fetch(..., spacer=None)` calls `spacer.wait(current_url)` before every request, including redirect hops and the rate-limit retry.
- The runner creates one `HostSpacer` per run and passes it through:
  - `check_source(..., spacer=)`
  - `article_text(..., spacer=)`
- `confirm` also uses a fresh `HostSpacer` for its up-to-5 article fetches. This is not required by the spec, but it prevents the same back-to-back pattern when the source is added.

### D6. Showing "rate limited"
- A single helper decides whether a stored check is rate limited:
  - `http_status == 429`, or
  - `http_status == 503` and the stored `error` starts with the rate-limit message prefix.
- `api/sources.py` list and `digest/runner.run_detail` include `http_status` and `rate_limited` for each check.
- Preview and confirm map `FetchError("rate_limited")` to `422` with code `rate_limited` and `retry_after`.
- Frontend:
  - The Sources page shows a "Rate limited — try again later" error for preview/confirm and a "Rate limited" badge in the list.
  - The Generate page labels such checks "rate limited (try later)" instead of the raw error.

## Risks / Trade-offs

- [Cooldowns and the preview cache are lost on restart] → After a restart, a rate-limited source is fetched again on the next run, and confirm fetches again. This is accepted (D1).
- [A retry adds up to 10 s to one fetch] → The wait is bounded by the 30 s `safe_fetch` deadline, and only one retry happens per call.
- [Spacing slows runs with many same-host sources] → It adds 1 s per extra request to the same host. That is negligible for personal use.
- [Hosts that rate limit without `Retry-After` (Reddit)] → They fail fast with "rate limited", and the next run retries. Items already recorded are not lost (ledger, `add-core-digest-flow` D1).
- [Rate-limited detection relies on a message prefix for 503] → The prefix is one constant shared by writer and reader, and a test covers it.

## Migration Plan

No schema change. Deploy by updating the code. `CATCHUP_USER_AGENT_CONTACT` is optional. Roll back by reverting the commits.

## Testing Plan

- Unit tests:
  - User-Agent value with and without a contact; invalid contacts rejected.
  - `Retry-After` parsing for all three date formats, seconds, past dates, and garbage.
  - `FeedCache` TTL, cap, and pop semantics with an injected clock.
  - `HostSpacer` behavior for same and different hosts with an injected clock and sleep.
- respx tests through `safe_fetch`:
  - the User-Agent on every request type (page, probe, declared feed, confirm, check, article)
  - 429 + `Retry-After: 3` → one retry, then success (sleep patched)
  - 429 + 120 s → `rate_limited` and no second request
  - 429 without the header → `rate_limited`
  - 503 + `Retry-After` handled like 429; 503 without it → `fetch_failed`
  - the deadline respected
- API tests:
  - preview → confirm makes exactly one feed request (respx call count)
  - confirm after cache expiry fetches
  - `rate_limited` 422 on preview and confirm
  - run detail and source list expose `rate_limited` and `http_status`
- Runner test: two same-host sources spaced ≥ 1 s (injected clock); different hosts not delayed.
- Frontend: Vitest tests for the rate-limited messages on the Sources and Generate pages.
- Manual verification by Claude Code with the user: add a Reddit source (preview → confirm) without the 15 s wait seen before, and confirm the User-Agent with a local request log or `httpbin`-style echo if available.

## Open Questions

- None blocking.
