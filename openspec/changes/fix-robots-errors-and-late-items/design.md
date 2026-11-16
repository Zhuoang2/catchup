# Design

## Context

The motivation is in proposal.md ("Why"). The code today:

- **Robots.**
  - `RobotsCache` (`backend/src/catchup/context/robots.py`) is created once per run in `gather_context` (`context/gather.py:23`). It is the only user of robots.txt.
  - `allowed(url)` fetches `<origin>/robots.txt` through `safe_fetch` once per origin, and caches the parsed rules or a boolean for that origin.
  - On `FetchError`, it caches `exc.status_code not in (401, 403)` (`robots.py:29-30`). So a 5xx answer, or an error with no status (DNS, connection, timeout), allows every path.
- **The robots fetch can fail in these ways.** All of them raise `FetchError` from `safe_fetch` (`backend/src/catchup/net/safe_fetch.py`):
  - a 4xx answer: `raise_for_status` raises before the body is read, with that status;
  - 429, or 503 with `Retry-After`: `rate_limited`, with that status;
  - a 5xx answer: with that status;
  - a timeout, DNS failure, or connection error: no status, or the status line already received when the deadline passed;
  - a redirect without a destination, or too many redirects: the 3xx status;
  - a response over the 512 KiB limit, or an invalid size: status 200;
  - a blocked address, or an invalid URL: no status.
- **`gather.fetch`** (`gather.py:53-69`) calls `robots.allowed(url)` first. When it is `False`, it returns `EXHAUSTED` if the run's budget is used up, and `None` otherwise. `None` means "skipped, counted as done".
- **Runs.**
  - `run_digest` (`backend/src/catchup/digest/runner.py:208`) checks the sources, runs `caption_pass`, then calls `gather_context` (`:297`).
  - Then it selects every pending item again (`:299-303`). `select_pending`, the source outcomes (`included_by_source`), the waiting and deferred counts, the summary inputs, and the save all come from that one query's `rows`.
  - The save marks items delivered by id (`:453`, `:482`), not by state.
- **Items can be recorded while a run is active.**
  - `POST /api/captures` (`backend/src/catchup/api/extension.py:132`) creates a new pending item. It refuses (409) only when it would update an already waiting capture during a run.
  - Confirming a source (`backend/src/catchup/api/sources.py:198`, items at `:251`) records its recent entries as pending, with no run check.
- **`Item.id`** is an `INTEGER PRIMARY KEY` without `AUTOINCREMENT` (`backend/src/catchup/models.py:112`).

A probe on 2026-11-16 on main `3b3713e`, in a scratch worktree:
- **Robots rule.** The rule in D1 was put into `robots.py`, and the backend suite was run. Only `test_failed_robots_request_allows` failed (921 passed).
- **Late item.** A respx side effect saved a capture through `POST /api/captures` while the pass fetched a linked page.
  - On main, the capture was delivered in that run, with `context_status` empty, and its link was never requested.
  - With the cutoff in D2, the capture stayed pending, and the next run fetched its link and delivered it, with its context `gathered`.
  - The rest of the backend suite was unchanged.

## Goals / Non-Goals

**Goals:**
- A robots.txt that cannot be read refuses every page of its origin for the rest of the run, as RFC 9309 section 2.3.1.4 requires. 4xx answers keep today's meaning.
- An item is summarized only by a run whose context pass could plan it.
- One change in each file, with no new state, no migration, and no API change.

**Non-Goals:**
- Retrying robots.txt within a run, or keeping robots rules across runs.
- Changing `gather.fetch`, `EXHAUSTED`, or the budget handling (#60 covers that cleanup).
- Showing late items in the run page or in the "no new content" message. The popup's waiting count already includes saved pages.
- Refusing saves or source confirms during a run.

## Decisions

### D1. Allow only when robots.txt was read, or the server answered a 4xx other than 401 and 403

In the `FetchError` branch of `RobotsCache.allowed`, cache `True` only when `exc.status_code` is in 400–499 and is not 401 or 403. Cache `False` in every other case. The successful branch is unchanged: CatchUp parses the rules and uses `can_fetch("CatchUp", url)`.

- **Why the status code, not the error code.** `fetch_failed` covers both a 404 and a timeout, so the error code cannot tell them apart.
  - A `FetchError` with a 4xx status always means that the server answered with that status. `raise_for_status` raises before any body is read. 429 comes from the rate-limit branch. The only other source is the deadline check right after the status line, which also comes after a real answer.
  - Every other status (200, 3xx, 5xx, none) means that the rules could not be read.
- **Why everything else disallows.** RFC 9309 requires complete disallow for server and network errors. For the remaining failures the RFC either says nothing or permits disallow: too many redirects "MAY" count as unavailable. A response over the 512 KiB limit is not parsed at all. Fail-closed keeps the rule to one line, and the user's 2026-11-01 decision covers the two cases that matter in practice.
- **429.** It stays "allow", as today and as RFC section 2.3.1.3 says for 4xx. The linked pages on that host are then likely to get 429 too. They are skipped one by one, which is today's behavior.
- **Effect in `gather.fetch`.** A refused origin makes `fetch` return `None`, which means skipped and counted as done, as with a robots.txt `Disallow`. When the failed robots.txt request used up the last budget unit, `fetch` returns `EXHAUSTED`, as today.
- **Alternative: disallow only for 5xx and network errors, and keep "allow" for the other failures.** Rejected. To say "network error", the code would need a list of error messages, which are user-facing text that can change.
- **Alternative: retry robots.txt once before disallowing.** Rejected. A 503 with a short `Retry-After` is already retried once by `safe_fetch`. Another retry costs budget, and the next run reads robots.txt again anyway.

### D2. Record the highest item id before the context pass, and select up to it

In `run_digest`, immediately before `gather_context(...)`, read `max(Item.id)` in a short session, using `0` when there are no items. Add `Item.id <= cutoff` to the pending query at `runner.py:299-303`. Nothing else changes, because every later step uses that query's rows.

- **Why before the pass, not inside it.** The window that matters is between `gather_context`'s plan query and the pending query.
  - Items recorded during the source checks or the caption pass get ids below the cutoff, and the pass plans them, as today.
  - An item recorded after the cutoff is read, but before the plan query, is planned and gets context, but waits for the next run. That is harmless: stored context is reused by later runs.
  - Reading the cutoff after the plan would reopen the defect.
- **Why in `run_digest`.** The cutoff belongs to item selection, which `run_digest` owns, and `gather_context` keeps one job. The cutoff is not stored on `DigestRun`: an interrupted run is marked failed by `recover_runs`, never resumed (`runner.py:157-164`).
- **Alternative: summarize only items whose `context_status` is set.** Rejected. Items that the per-run fetch limit left unreached keep `context_status` empty, and they must still be summarized in this run (content-collection, "Per-run fetch limit reached").
- **Alternative: let `gather_context` return the set of planned ids.** Rejected. Podcast episodes without text, YouTube videos, and items gathered in earlier runs are not in the plan, but they must be included. The set would need a second query, and it gives nothing more than the id bound.
- **Alternative: refuse saves and confirms while a run is active.** Rejected. The pass can take minutes (#64), and the extension would refuse pages for the whole time.

## Risks / Trade-offs

- [A site whose robots.txt fails for a moment loses its linked pages for that run. Those items are delivered without that context and are not gathered again.] → This is what the RFC requires, and what the user decided. Other sites in the run are not affected. The next run reads robots.txt again.
- [SQLite reuses the highest rowid after that row is deleted. Suppose the newest item is deleted during the pass (by deleting its source, or by removing a saved page in the popup), and a new item is then recorded. The new item can get an id at or below the cutoff, and is then summarized without context, as today.] → Recorded as a known limit. It needs a delete of the newest item and a new item inside one pass. `gather_context` already has the same exposure for planned ids. `AUTOINCREMENT` would need a table rebuild migration, which is out of proportion for this change.
- [A run whose only pending items are late ones ends with "no new content".] → The items appear in the next run. See Non-Goals.

## Migration Plan

Backend only. No data migration. Roll back by reverting the commit.

At review, Claude Code runs:
- the Docker smoke script (`scripts/docker-smoke.sh`);
- a live check on a local test instance from the branch (not 8800), with a local stub model server and a public feed:
  1. Start a run whose items have linked pages.
  2. While the run page shows "Linked pages read", save a page through `POST /api/captures` with a test extension token.
  3. Check that the digest leaves the page out, that it stays waiting, and that the next run includes it with its linked context.

The robots.txt cases (5xx, network error, 404, 401/403) are checked by the tests only. No public host has a robots.txt that fails on demand.
