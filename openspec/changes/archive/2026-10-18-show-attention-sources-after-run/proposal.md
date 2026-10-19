# Proposal

## Why

After a run ends, the main screen lists every source with its check outcome: "New items", "No new items", "Failed", "Rate limited · try later", and "Possible gap" (issue #38, found while the user was testing on 2026-10-17). With three sources that were all fine, the list pushed the digest down and told the user nothing to act on.
- `RunStateContent` in `frontend/src/pages/Home.tsx` renders `SourceChecks` with all of `run.source_checks` for every run state: running, succeeded, no new content, and failed (`Home.tsx:71`, `:92`, `:105`).
- The `user-interface` spec, "Main screen shows the latest digest", requires "each source's check outcome" after a run ends. The `digest-generation` spec, "No digest when nothing is new", requires the same for a run with no new content.
- Every source's last outcome is already on the Sources page (`user-interface`, "Sources show their kind and confirm deletion inline"; `frontend/src/pages/Sources.tsx:90-96`), including "Rate limited" and "Possible gap".

## What Changes

- **After a run ends, list only the sources that need attention.** These are the sources whose check failed (including rate limited) or flagged a possible gap. The user decided this on 2026-10-18. It applies to every ended state on the main screen: a saved digest, no new content, and a failed run. It also applies whether the result is shown in the run bar above a digest or in the result card of the no-digest layout. Each listed source keeps today's chips and error text.
- **When every source is fine, show no source list** and no label. The result line still gives the number of sources, and the Sources page still shows every outcome.
- **Label.** The shortened list is labeled "Needs attention", not "Sources", so that a list of one source does not read as if the user has only one. This wording was chosen during planning; the user did not specify it.
- **Unchanged:**
  - During a run, every checked source is listed as its outcome becomes known, as today.
  - The Sources page.
  - The status-region announcements.
  - The run API: `source_checks` still has every source; only the main screen filters it.
- **Out of scope:** a link from the list to the Sources page. The run bar already links to the sources.

## Capabilities

### New Capabilities
- None.

### Modified Capabilities
- `user-interface`, "Main screen shows the latest digest":
  - After a run ends, the run bar shows the sources that need attention, not every source's outcome.
  - The "Run finds no new content" scenario changes to match.
  - New scenarios cover all sources fine, and only some needing attention.
- `digest-generation`, "No digest when nothing is new": the user sees "no new content" together with the sources that need attention, not every source's outcome. The existing scenarios still hold.

## Impact

- `frontend/src/pages/Home.tsx`:
  - `RunStateContent` passes only the sources that need attention to `SourceChecks` for ended runs.
  - `SourceChecks` takes the label to show.
- `frontend/src/pages/Home.test.tsx`: new tests for the filtered list, the empty case, the label, and the unchanged in-run list. Existing after-run tests use a failed source, and are kept or adjusted.
- No backend, API, Sources page, or CSS change.
