# Proposal

## Why

One malformed address in one feed entry fails every digest run (#66). For example, an image `https://[object Object]` raises `ValueError` while the feed is parsed. The run then stops with "Digest generation failed": that source records no outcome, and the sources after it are not checked. Every later run fails the same way while the entry stays in the feed. Deleting a source while a run checks it fails the run too. The spec already says that when one source fails, "other sources are still checked"; the code does not keep that promise for errors it did not expect.

## What Changes

- **Parsing an address never raises.** Where feeds, discovery, linked-page selection, and saved pages turn text into an address, an address that cannot be parsed is skipped, and everything else in the entry or page is kept. `safe_fetch` reports an address `httpx` rejects as `invalid_url`, like one it rejects itself.
- **One source's unexpected error stays with that source.** During a run, if checking one source (its feed, its YouTube captions, or an X account) raises an error nobody expected, that source's work is rolled back and recorded as `failed` with a fixed message, and the run goes on to the next source. Only the exception's class is logged.
- **Deleting a source during a run** no longer fails the run: the deleted source is skipped.
- **Preview and saving a page** answer with an error the page can show, instead of 500, for such input.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `content-collection`: "Check every source on each run" — a check that fails for an unexpected reason is `failed` too; new scenarios for a malformed address in one entry, an unexpected error in one source, and a source deleted during a run.

## Impact

- **Backend:**
  - `sources/feeds.py` (image and link helpers, entry and channel links), `sources/discovery.py`, and `context/links.py`;
  - `net/safe_fetch.py` (`httpx.InvalidURL`);
  - `digest/runner.py` (the source, caption, and X loops);
  - `api/sources.py` and `api/extension.py` (preview and captures).
- **Tests:** backend only. No API shape changes, no migration, no frontend change.
- **Closes** #66.
