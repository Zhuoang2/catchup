# Proposal

## Why

Two defects in the linked-page pass came from the system review on 2026-11-01:

- **#76.** When a site's robots.txt answers 5xx, or cannot be reached, `RobotsCache.allowed` treats the site as allowing every path (`backend/src/catchup/context/robots.py:29-30`). A test pins this behavior (`backend/tests/test_context_robots.py:45-48`). RFC 9309, section 2.3.1.4, says that a crawler must assume complete disallow when robots.txt is unreachable because of server or network errors. On 2026-11-01 the user decided that CatchUp follows the RFC.
- **#70.** The context pass plans its items once, at its start (`backend/src/catchup/context/gather.py:25-30`). The summary stage then selects every pending item again (`backend/src/catchup/digest/runner.py:299-303`). An item recorded while the pass runs therefore goes into the same run's digest without linked pages or author replies. Such an item can be a page saved with the extension, or the recent entries of a feed confirmed on the Sources page. The pass can take minutes (#64). A probe on main reproduced this. A page saved during the pass was delivered in the same run, its `context_status` was still empty, and its link was never requested. Delivered items are never gathered again.

## What Changes

- **Unreachable robots.txt means disallow, for the rest of the run.** When the robots.txt request fails, CatchUp fetches no linked page or post page from that origin (the same scheme, host, and port) in this run. This applies to:
  - an HTTP 5xx answer, including 503 with `Retry-After`;
  - a network error: a timeout, a refused or reset connection, or a host that cannot be resolved;
  - any other failure in which no 4xx status came back: a redirect without a destination, too many redirects, a response over the 512 KiB limit, or a blocked address.
- **4xx answers keep their current meaning.** 404, 410, 429, and other 4xx answers allow every path, as today. 401 and 403 still disallow, as today.
- **Late items wait for the next run.** A run records the highest item id just before its context pass starts. It summarizes, and lists under Creator updates, only pending items up to that id. Items recorded later stay pending. They get their context in the next run and appear in that run's digest. They are not counted in this run's source outcomes or waiting counts.
- No API, data model, or UI change. No migration.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `content-collection`: "Gather related context for website items" states what an unreachable robots.txt means, and adds scenarios for a 5xx answer and for a network error.
- `digest-generation`: "Include every pending item" adds an exception for items recorded after the run's context pass started, with a scenario for a page saved during the pass.

## Impact

- Code:
  - `backend/src/catchup/context/robots.py` (one rule);
  - `backend/src/catchup/digest/runner.py` (record the highest item id before `gather_context`, and filter the pending query by it).
- Tests: `backend/tests/test_context_robots.py` and `backend/tests/test_context_gather.py`. One existing test, `test_failed_robots_request_allows`, pins the old behavior. It is replaced, not kept (probe: no other backend test depends on the old rule).
- Docs:
  - `README.md` (the linked-pages paragraph);
  - the decision log (D-030);
  - the requirements-changes table;
  - a test report;
  - the AI usage log.
- Out of scope:
  - the source check's own feed fetch (robots.txt is not used for feeds, as today);
  - re-reading robots.txt in later runs (each run has its own cache, as today);
  - showing late items in the run's "no new content" message;
  - SQLite reusing the id of a deleted highest item (design, Risks).
