# Design

## Context

See `proposal.md`, "Why". Facts on main `64973c0` that the decisions below depend on:

- **Run order** (`backend/src/catchup/digest/runner.py:208-489`):
  1. one session reads the model settings and the source ids (`:213-239`);
  2. the feed, podcast, and YouTube checks (`:265-266`), then the X checks and their counters (`:267-295`);
  3. `caption_pass` (`:296`);
  4. `gather_context` (`:299`);
  5. `select_pending` and the check-rewrite step (`:301-348`);
  6. `summarize_items` (`:388-389`), which runs model calls in a pool of 4 (`digest/summarize.py:150`), and writes to the database only on the runner thread through `record` (`:364-379`);
  7. `group_items` (`:390-399`);
  8. the save (`:403-489`).
- **Context pass** (`context/gather.py:20-153`). One session builds the plan in item-id order: `(item_id, site_url, links, comments, captured_replies)` (`:23-50`). Then each item, one after another, runs in its own session:
  - its links in body order, until the item's linked text reaches 16,000 characters (`:82-109`);
  - the post page when it gets author replies, and the comment feed when the post page shows no replies (`:110-134`);
  - its captured replies (`:137-143`);
  - a deletion check in a second session (`:144-147`), then `context_status` and the summary invalidation (`:148-153`).

  An item is skipped, keeping `context_status` NULL, when the limit is used up and it has no captured replies (`:72-73`). A `BudgetExhausted` inside the item ends its links and its author replies, and keeps what it gathered (`:135-136`).
- **Progress today.** `progress()` commits `context_done` and `context_total` in a fresh session after every read (`:64-69`). A test pins that the next request already sees the commit (`tests/test_context_gather.py:998-1017`).
- **Shared state is not thread-safe:**
  - `safe_fetch` checks and takes a budget unit in two statements (`net/safe_fetch.py:170-173`);
  - `RobotsCache.allowed` checks its dict, then reads robots.txt, with no lock (`context/robots.py:23-37`);
  - `HostSpacer.wait` holds one lock for every host while it sleeps (`net/host_spacing.py:18-27`).
- **The database.** SQLite in WAL mode with `busy_timeout=5000` (`db.py:24-25`). Tests use a file database in a temporary directory, through the same engine. Worker threads may open their own sessions: API threads and the runner thread already do.
- **The source outcome.** `check_source` and `check_x_account` save `new_items` only when the check records new entries (`collection.py:166`, `sources/x_check.py:119`). `check_one_source` runs one source's check in its own session (`runner.py:126-150`).
- **Logging.** The app installs no handler for its own `catchup.*` loggers, so INFO lines do not reach `docker logs`.

## Goals / Non-Goals

**Goals:**
- Measure each stage of a run, and keep the measurement with the run.
- Read the linked pages of several items at the same time, without breaking per-host spacing, the robots.txt rules, or the per-run limit.
- A linked-page total that the bar actually reaches.
- Source counts and outcomes during a run that match what the run does.

**Non-Goals:**
- Faster source checks, caption pass, or model calls.
- A setting for the number of items read at once, or for the depth (#54).
- Showing durations on screen.
- At most one request in flight per host: the 1-second spacing between request starts stays the rule.

## Decisions

### D1. Stage durations go into the run record

- **New column.** `digest_runs.stage_seconds` (JSON, nullable). The keys are `checks`, `captions`, `context`, `summaries`, and `grouping`. Each value is seconds rounded to one decimal place.
- **The clock.** `runner.py` imports `monotonic` from `time` at module level, so a test can replace `catchup.digest.runner.monotonic`. It reads the clock only at stage boundaries.
- **The stages:**
  - `checks`: from just before the first source check to after the X counters are committed (`:265-295`);
  - `captions`: `caption_pass`;
  - `context`: `gather_context`;
  - `summaries`: `summarize_items`;
  - `grouping`: `group_items`.
- **When each is saved.** A helper commits each duration right after its stage returns, in a short session on the runner thread. It assigns a new dict (`{**(run.stage_seconds or {}), name: value}`), so SQLAlchemy sees the change. A stage that raises records nothing, so a failed run keeps the stages it finished. A run with nothing to summarize has no `summaries` or `grouping`.
- **The API.** `run_detail` returns `"stage_seconds": run.stage_seconds or {}`.
- **Alternative: log lines.** Rejected. INFO lines from `catchup.*` reach no handler today, and a log line cannot be compared after the fact the way a stored run can.

### D2. The number of sources is stored when the run starts

- **New column.** `digest_runs.sources_total` (Integer, NOT NULL, server default `0`).
- **Set twice, before any check:**
  - `start_run` sets it to the number of sources that are not captures, the same count as today;
  - `run_digest` sets it to `len(source_ids) + len(x_source_ids)` in its first session, and commits. This is the number of sources the run will check, even when one is added between the two steps.
- **The API.** `run_detail` returns `run.sources_total`.
- **Migration `0008_run_progress`:**
  - adds both columns;
  - sets `sources_total` of every existing run to the number of its rows in `source_checks`;
  - its downgrade drops both columns with `batch_alter_table(..., recreate="never")`, as `0007` does.
- **The run bar.** `Home.tsx` shows the linked-page line when the run is `collecting` and `context_total > 0`. It no longer waits for `source_checks.length === sources_total`. The backend writes `context_total` only in the context pass, which starts after every check, so the line cannot appear early. A source deleted during the checks, which loses its check row or never gets one, no longer hides it.
- **Unchanged.** The status-region text during the context pass stays "Checking sources, N of M": an existing test pins it (`Home.test.tsx:270-279`), and announcing every page read is a separate decision.
- **Alternative: count the live sources minus those added after `started_at`.** Rejected: it still breaks when a source is deleted, and it needs a query on every poll.

### D3. The linked-page total is what the run can still read

- **The unit is a read,** as today:
  - one per related link;
  - one for the post page when the item gets author replies;
  - one for the comment feed, added when it is needed;
  - one for an item's captured replies, which needs no request.
- **A read is done** when its fetch returns a response or `None`: failed, refused by robots.txt, or not related after a redirect. That is the same as today.
- **A read is dropped** (it leaves the plan without counting as done) in these cases:
  - `BudgetExhausted` ends the item, so its remaining network reads are dropped;
  - the 16,000-character cap ends its links, so its remaining links are dropped and its post page stays;
  - the item is deleted, or is skipped because the limit is used up.
- **Progress object.** `ContextProgress` in `gather.py` holds:
  - the plan's remaining reads, item by item, in plan order;
  - the reads in progress;
  - `done`.

  Its operations are:
  - `start(item_id)`: the item's next read begins;
  - `finish(item_id)`: that read is done;
  - `drop_links(item_id)`;
  - `drop(item_id)`: drops every remaining network read of the item;
  - `add(item_id, url)`: the comment feed;
  - `replies(item_id)`: the captured replies were stored.
- **Each operation recomputes and commits.** Except `start`, every operation recomputes the total and commits `context_done` and `context_total` in a short session. It does this while holding the object's lock, so the two numbers always move together, whichever thread calls it. `start` only moves a read into the "in progress" set.
- **The total:**
  `total = done + in_progress + captured_replies_left + reachable_reads(not_started_urls, robots.verdict, budget_left)`
- **`reachable_reads(urls, verdict, units)`** is a pure function. It walks the URLs in order, and keeps a set of the origins it has charged:
  - when `verdict(url)` is `False`, robots.txt is known to refuse the URL: the read counts, and costs no unit;
  - when `verdict(url)` is `True`, or the origin was already charged in this walk: the read costs 1 unit;
  - otherwise it costs 2 units, for robots.txt and the page, and the origin is marked charged;
  - an address that `safe_fetch` refuses before it takes a unit (not `http` or `https`, no host, a user name or password, or a bad port) counts, and costs no unit. `origin(url)` raises `ValueError` for it. Added in fix round 1, after the review found that such an address failed the run;
  - the walk stops at the first read whose cost exceeds the units left. When the limit runs out, the run stops making requests (`BudgetExhausted`), so later reads are not reached either.

  It returns the number of reads counted.
- **The initial total.** `ContextProgress` computes it on the runner thread, and commits it before the first read. It replaces `run.context_total = sum(...)` (`gather.py:46-49`).
- **`RobotsCache.verdict(url)`** returns `None` while the URL's origin has no stored rule. Otherwise it returns the stored bool, or `can_fetch("CatchUp", url)`. It never makes a request. The origin key moves into a module-level `origin(url)` function in `robots.py`. `allowed` and `verdict` both use it, and the walk uses it for "charged".
- **Exactness.** The total is exact while every robots.txt allows the pages and no page redirects. Otherwise, the next operation corrects it:
  - a redirect hop and a robots.txt redirect each cost an extra unit;
  - a read in progress whose robots.txt is not read yet is counted as already paid.

  It is never below `done`. When the pass ends, nothing remains, so `total == done`.
- **Alternatives:**
  - **`done + min(units left, reads left)`.** Rejected: robots.txt requests take about a third of the limit in a run like the one in #64 (39 pages from 60 units), so the total would fall from 60 to 39 during the pass.
  - **Count robots.txt requests as reads.** Rejected: the label says "Linked pages read", and robots.txt is not a linked page.
  - **Show robots.txt requests on a second line.** Rejected: a second number that users do not need.

### D4. Up to 4 items at the same time

- **The pool.** `CONTEXT_WORKERS = 4` in `gather.py`, the same size as the summary pool. A `ThreadPoolExecutor(max_workers=CONTEXT_WORKERS)` gets one task per planned item, submitted in plan order. The executor's queue is first-in, first-out, so items start in plan order.
- **Each task runs today's per-item steps** in its own session, with no change of order inside the item:
  1. the skip check (limit used up and no captured replies: `drop`, keep NULL);
  2. links in body order with the cap;
  3. author replies;
  4. captured replies;
  5. the deletion check;
  6. `context_status` and the summary invalidation.
- **Failures.** The runner thread waits for the futures in submission order. If one raises an unexpected exception, it calls `shutdown(cancel_futures=True)`, waits for the running tasks, and re-raises, so the run fails as it does today. Every expected failure is still caught inside the task, as today.
- **Thread-safe shared state:**
  - **`HostSpacer`** keeps a lock per host, created under a small lock for the dict. `wait` holds the host's lock while it computes the delay, sleeps, and stores the new time stamp. So waits for one host stay exact and in order, and different hosts never wait for each other. With one thread, the behavior is the same as today.
  - **The budget.** `safe_fetch` takes a unit under a module-level `threading.Lock`, with the check and the decrement in one block. Probe P3 shows that the unlocked form exceeds the limit under threads.
  - **`RobotsCache`** keeps a lock per origin. `allowed` checks its dict without a lock, and returns the stored rule when there is one. Otherwise it takes the origin's lock, checks again, and only then checks the limit and reads robots.txt. A second caller for that origin waits, then uses the stored rule.
- **Tests that need a fixed order.** Some existing tests start two or more items while the limit is nearly used up, and assert which item got context. They set `CONTEXT_WORKERS` to 1 with `monkeypatch`. Each one is listed in the test report, with the reason.
- **Alternatives:**
  - **Fetch each item's links in parallel.** Rejected: the 16,000-character cap and the body order need the earlier pages' text, and parallel fetches would spend units on pages the cap then drops.
  - **One flat queue of URLs.** Rejected for the same reason, and it would split one item's session and status across threads.
  - **Async I/O with `httpx.AsyncClient`.** Rejected: `safe_fetch`'s connect-time address check is built on the sync backend (`safe_fetch.py:112-135`).
  - **Workers return results, and only the runner thread writes.** Rejected: the pinned rule that progress is committed before the next request (`test_context_gather.py:998`) would need a queue and polling. SQLite in WAL mode already serves several writer threads.
  - **A setting for the number of items.** Deferred to #54.

### D5. Held items show "New items" when their source is checked

- **A helper.** `_show_held_items(factory, run_id, source_id, settings)` in `runner.py` runs after each `check_one_source` call, in both the feed loop and the X loop.
- **What it does.** In one session, it reads that source's latest `SourceCheck` for this run. When the status is `no_new_items`, it loads the source's pending items with their source, and calls `select_pending(rows, utc_now(), settings.transcript_wait_days, settings.caption_wait_hours)`. If that returns any summary or creator update, the helper sets the check's status and the source's `last_check_status` to `new_items`, and commits. `new_count` is left alone. The check-rewrite step after the context pass stays the final word, and sets both.
- **Missing rows.** A source deleted during its check has no rows, and the helper does nothing. The helper writes with `update()` statements, as the check-rewrite step does, so a source deleted after it read its rows is not an error either (fix round 1).
- **YouTube.** New videos are `to_fetch` until the caption pass, so `select_pending` does not count them yet. Such a source keeps its check's own outcome until the rewrite step, as today.
- **Alternative: change `check_source` and `check_x_account`.** Rejected: both would need `select_pending` from `runner.py`, which imports them. That is a cycle, and the rule would live in two places.

### D6. README

The context paragraph (`README.md:581-590`) gains, after "(including robots.txt).":

```
CatchUp reads linked pages for up to 4 items at the same time, and keeps
requests to one host at least 1 second apart. While it reads them, the run
shows how many pages it has read, out of the pages it can still read within
that limit.
```

`backend/tests/test_readme_context.py` checks for:
- "up to 4 items at the same time";
- "at least 1 second apart";
- "can still read within".

## Risks / Trade-offs

- **[Items at the limit's edge are marked `none`.]** Today, an item that the pass reaches after the limit is used up keeps `context_status` NULL, and a later run plans it again. With 4 workers, up to 3 items can start while units remain, lose the race for the last ones, and end as `none`. This matters only when the run then fails before its save. In a successful run, every pending item is delivered either way. → Accepted and recorded in D-036. Telling these items apart would need per-item budget accounting in `safe_fetch` and `RobotsCache`. The test that pins the NULL status runs with one worker.
- **[Which items get context depends on timing.]** When the limit runs out, it is spread over the items in progress, not given strictly in plan order. → Spec text says so. Items still start in plan order.
- **[More load on a host shared by several items.]** Two items can each have a request open to one host, when the first takes longer than 1 second. Requests still start at least 1 second apart, which is the existing rule. → Kept as a non-goal.
- **[SQLite writes from 4 threads.]** → WAL and `busy_timeout=5000`. The writes are short: progress rows and one commit per item. The per-item session reads the item and writes only at its end, as today.
- **[The total moves after a redirect, or with reads in progress.]** → It corrects itself at the next operation, and it equals `done` at the end.
- **[Threads and test libraries.]** → Probes P1 and P2 show that trafilatura, lxml, and respx work across worker threads.
- **[Stage durations add commits.]** Five short commits per run. → Negligible.

## Migration Plan

- `0008_run_progress` runs at startup like the earlier migrations. It adds two columns, and fills `sources_total` from `source_checks`. Its downgrade drops both columns.
- No setting changes. Rollback is the previous image, after a downgrade to `0007_x_accounts`.

## Evidence (probes on main `64973c0`)

These were run with the backend's locked environment (`uv run --offline python -I`). The script is `p64/probe_threads.py` in Claude's session scratchpad, and is not committed.

- **P1. trafilatura 2.3.0 and lxml 6.1.3 across threads.** `extract` and `html.fromstring(...).xpath("//title/text()")` ran on 200 invented article pages, sequentially and through `ThreadPoolExecutor` with 4 and 16 workers, three times each. The outputs were identical every time.
- **P2. respx 0.23.1 across threads.** 40 `httpx.Client` requests from 4 worker threads hit one regex route, whose side effect sleeps 50 ms. Every request returned 200, `call_count` was 40, and the peak in-flight count measured in the side effect was 4. So concurrency tests can count requests and measure overlap with respx.
- **P3. Unlocked list budget.** Four threads took units from `[50]` with the check and the decrement separated by `time.sleep(0)`. In 163 of 200 trials, they took more than 50 units. Without the yield, the window is smaller, but it is not closed.

## Testing

- **Seams:**
  - `execute(environment)`, `seed`, `setup`, `stub_collection(monkeypatch, on_check=…)`, `seed_x_accounts`, and `x_timeline` from `tests/test_digest_runner.py` and `tests/test_context_gather.py`;
  - respx routes with `side_effect` functions;
  - `HostSpacer(min_interval=…, clock=…, sleep=…)`;
  - `RobotsCache`, `origin`, and `reachable_reads`;
  - `catchup.digest.runner.monotonic`;
  - `catchup.context.gather.CONTEXT_WORKERS`;
  - `catchup.digest.runner.caption_pass`, wrapped to look at the database between the checks and the context pass;
  - `mockPage` in `frontend/src/pages/Home.test.tsx`.
- **Concurrency tests measure overlap in respx side effects,** with a lock and short real sleeps (50–200 ms). They do not compare wall-clock totals. Each concurrency test file is run five times in a row in task 7.1.
- **Named mutations** are listed in each task group. The budget lock (D4) cannot be killed reliably by a test, because the race window is a few bytecodes. It is verified by review and by probe P3, and recorded as such.
- **At review, Claude Code:**
  - **Benchmark.** Runs the same invented workload through main's and the branch's `gather_context`: 50 items, 178 related links over about 100 hosts, the limit at 60, and an invented latency per host of 0.3–2.0 s. A local server serves the pages, and DNS and the public-address check are patched in the benchmark script only. Claude reports the context pass's wall time and the final total and done for both.
  - **Docker smoke.** Runs `scripts/docker-smoke.sh`.
  - **Browser check.** Starts a scratch instance from the branch with a scratch data directory. After startup, it writes an active run row into that database, with fewer check rows than its `sources_total`, and with `context_total > 0`. `recover_runs` only touches rows that exist at startup. Claude then checks the run bar's linked-page line and the status text in the browser pane.
- **Real stage durations.** A real run needs the user's sources and model key, so real durations come from the user's next run after the merge. It is the user's choice.
