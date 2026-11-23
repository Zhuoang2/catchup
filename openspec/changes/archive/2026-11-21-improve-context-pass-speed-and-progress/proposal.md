# Proposal

## Why

In the user's live check on 2026-11-01, a run over 50 new items took about 4 min 20 s. The run bar read "Linked pages read: 6 of 178" for a long time, and the run read only 39 linked pages (#64). Checked on main `64973c0`:

- **The total counts every candidate link.** `context_total` is the sum of the planned links, post pages, and captured replies over all items (`backend/src/catchup/context/gather.py:46-49`). A run makes at most `CATCHUP_CONTEXT_FETCHES_PER_RUN` requests (default 60, `config.py:61,81`), and robots.txt requests take units from the same limit (`context/robots.py:27-30`; README: "limits requests per run (including robots.txt)"). Links that the limit or the 16,000-character cap stops are never counted as read, so the bar never reaches its total.
- **Linked pages are read one at a time.** The context pass reads one item after another, one request at a time (`gather.py:71-153`). Each request can take up to 15 s to read and 30 s in all (`net/safe_fetch.py:24,179-182`). `HostSpacer` holds one lock for all hosts while it sleeps (`net/host_spacing.py:18-27`), so requests to different hosts cannot run at the same time even from several threads.
- **A followed source looks wrong during the run.** Following a source records its recent entries as pending items, and sets its status to "New items" (`api/sources.py:133,261`). The run's check then finds no new entries and saves "No new items" (`collection.py:166`, `sources/x_check.py:119`). The status becomes "New items" only after the context pass, in the check-rewrite step (`digest/runner.py:328-347`). This happens for feeds and for X accounts.
- **The number of sources is counted live.** `sources_total` counts the sources at each request (`runner.py:527`). When a source is added during a run, the bar reads "Sources checked: N of N+1", and the linked-page line never appears, because it waits until every source is checked (`frontend/src/pages/Home.tsx:70-71`). The same happens when a source is deleted during a run.
- **No run records how long its stages take,** so the slow stage of a run like the one above cannot be measured.

## What Changes

- **Stage durations.** Each run records how many seconds its source checks, caption pass, context pass, summaries, and grouping took. The run API returns them. The screen does not show them.
- **Sources total fixed at the start.** A run stores the number of sources it will check when it starts. The run bar and the result use that number.
- **Linked-page total.** While the context pass runs, the total is the pages read so far plus the pages the run can still read within the remaining per-run limit. The total counts one robots.txt request for each site that the run has not asked yet. Pages that the limit, the 16,000-character cap, or a deleted item rules out leave the total. When the pass ends, the bar shows the same number read and in total.
- **Linked-page progress starts with the context pass.** The run bar shows the linked-page line from the start of the context pass, even when a source was deleted during the checks.
- **Several items at once.** The context pass reads linked pages for up to 4 items at the same time:
  - requests to one host stay at least 1 second apart, across items;
  - robots.txt is still read once per site;
  - the per-run limit is never exceeded;
  - each item's own pages are still read in body order, with the same caps.
- **Held items during the run.** When a source's check finds no new entries but the source has pending items that the run will include, the check shows "New items" as soon as it is saved.
- **README.** The context section says that the run reads pages for up to 4 items at once, and what the progress total counts.
- No change to the per-run limit, the per-item caps, the 1-second spacing, or the robots.txt rules.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `digest-generation`: "Show run progress and per-source outcomes" now states:
  - the fixed number of sources;
  - how the linked-page total is counted, and that it equals the number read when the pass ends;
  - that a source with held items shows "New items" when it is checked.

  A new requirement, "Record how long each run stage takes", records the stage durations.
- `content-collection`: a new requirement, "Read linked pages for several items at the same time", sets the limit of 4 items, and states that host spacing, robots.txt, and the per-run limit still hold.

## Impact

- Code:
  - `backend/src/catchup/context/gather.py` and `context/robots.py`;
  - `backend/src/catchup/net/host_spacing.py` and `net/safe_fetch.py`;
  - `backend/src/catchup/digest/runner.py`;
  - `backend/src/catchup/models.py`, and a new migration `0008_run_progress`, which adds two columns to `digest_runs`;
  - `frontend/src/pages/Home.tsx`.
- API: `GET /api/digest-runs/{id}` and `/active` gain `stage_seconds`. `sources_total` keeps its name and meaning, and is now stored.
- Tests:
  - `backend/tests/test_context_gather.py`, `test_host_spacing.py`, `test_context_robots.py`, `test_safe_fetch.py`, `test_digest_runner.py`, `test_db.py`, and `test_readme_context.py`;
  - `frontend/src/pages/Home.test.tsx`.
- Docs:
  - `README.md`;
  - the decision log (D-036);
  - the requirements-changes table;
  - a test report;
  - the AI usage log.
- Out of scope:
  - letting users choose the depth or the limit (#54);
  - showing stage durations on screen;
  - changing what the status region announces during the context pass;
  - other stages' speed: the source checks, the caption pass, and the model calls.
