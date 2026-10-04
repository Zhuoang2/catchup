# Proposal

## Why

The first real test of CatchUp found three fetch-reliability problems (`docs/process/test-report-add-core-digest-flow.md`):
- Adding a Reddit source failed when confirm re-fetched the feed seconds after preview (HTTP 429).
- A check during a run hit 429 and was shown only as a generic failure.
- Requests carry httpx's default User-Agent, which sites such as Reddit "drastically limit" or block (research: default UA got 403, descriptive UA got 200).

These affect every source, not only Reddit. Separately, Reddit will stop serving RSS on 2026-11-13, so users need to know its support is temporary. Scope was set by the user on 2026-10-04 after research (issue #3; #2 closed). The chosen approach is Proposal 1, handling everything in-process (see `design.md`).

## What Changes

- Every outgoing request identifies CatchUp with a descriptive User-Agent that includes the project URL. An optional contact can be added through configuration.
- On HTTP 429, or 503 with `Retry-After`, CatchUp waits and retries once when the requested delay is short (≤ 10 s) and fits the fetch deadline. Otherwise it stops and reports the source as rate limited, with the suggested wait when known.
- "Rate limited" is shown as its own message in preview, confirm, the source list, and run progress, separate from other failures. The stored check outcome stays `failed`.
- Confirm reuses the feed fetched by a recent preview (within 10 minutes) instead of fetching it again.
- During a digest run, requests to the same host are spaced at least 1 s apart.
- The README states that Reddit support ends on 2026-11-13 because Reddit is discontinuing RSS.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `source-management`: adds requirements for identifying the client, honoring rate limits during preview and confirm, and reusing a recent preview on confirm.
- `content-collection`: adds requirements for identifying rate-limited checks and spacing requests to the same host during a run.

## Impact

- Code:
  - `backend/src/catchup/net/safe_fetch.py` (User-Agent, `Retry-After`, retry, `rate_limited` error)
  - new `backend/src/catchup/net/feed_cache.py` and `backend/src/catchup/net/host_spacing.py`
  - `sources/discovery.py`, `api/sources.py`, `collection.py`, `digest/runner.py` (run-detail fields)
  - `config.py` (`CATCHUP_USER_AGENT_CONTACT`)
  - frontend Sources and Generate pages, README, `.env.example`
- No database migration and no new dependencies.
- Behavior: a fetch may now take up to ~10 s longer when a server asks for a short wait, still bounded by the existing 30 s deadline.
