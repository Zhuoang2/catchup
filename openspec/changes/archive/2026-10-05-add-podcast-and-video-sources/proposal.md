# Proposal

## Why

The first release promises podcasts and long videos "where captions or transcripts are obtainable" (`docs/handoff.md:44-47`). Today CatchUp treats both as generic feeds, and three things go wrong:
- YouTube videos and podcast episodes are summarized from their descriptions and web pages, so a digest claims to cover content it never processed.
- Apple Podcasts URLs and podcast feeds above 5 MB fail.
- Any text over 20,000 characters is silently cut, which keeps about 12% of a 3.6-hour episode (`research.md`).

Issues #5 and #6 are merged here because both need the same transcript rule, item states, and long-text handling.

## What Changes

- **Sources:**
  - Podcast and YouTube sources are recognized when added, and the preview shows how transcripts will be obtained.
  - Apple Podcasts show and episode URLs resolve to the show's RSS feed through the iTunes Lookup API.
  - Feed responses may be up to 32 MB (configurable); articles and transcripts keep 5 MB.
- **Podcast transcripts:**
  - Episodes are summarized from the transcripts their feeds publish (`<podcast:transcript>`). Every listed format is considered, and plain text, WebVTT, SRT, JSON, and HTML are converted to plain text with speaker names kept.
  - An episode without a transcript waits up to `CATCHUP_TRANSCRIPT_WAIT_DAYS` (default 7) and is re-checked on every run.
- **YouTube captions:**
  - Captions are fetched only when the user turns on "fetch captions locally" (default off; the setting states the conflict with YouTube's Terms of Service).
  - Only captions in the video's original language are used, manual before auto-generated, never machine-translated.
  - A video without captions yet (just uploaded, or an upcoming premiere) waits up to `CATCHUP_CAPTION_WAIT_HOURS` (default 24) and is retried on every run.
  - Requests are sequential, spaced per host, and capped at `CATCHUP_CAPTIONS_PER_RUN` (default 20) videos per run. A block from YouTube stops further caption requests in that run.
  - YouTube Shorts are skipped by default.
- **Creator updates:** a new digest section after the topic summaries, grouped by creator or show. It lists each item that cannot be summarized (title, time, link, reason) once, with no model call. The reasons are:
  - caption fetching off
  - video has no captions
  - blocked by YouTube
  - captions could not be fetched
  - no podcast transcript within N days
- **Long texts:**
  - The single-call budget is derived from the model's `context_window` reported by `/models`, with a 60,000-character fallback. Longer texts are summarized in chunks and combined.
  - Long transcripts get an overview plus key points.
  - **BREAKING** (configuration): `CATCHUP_MAX_ITEM_CHARS` is removed. The optional override is `CATCHUP_SINGLE_CALL_CHARS`.
- **Usage:** each run records the model tokens it used. The run and the saved digest show the total.

## Capabilities

### New Capabilities
- `transcripts`: how podcast and YouTube items obtain transcripts. It covers source recognition, published podcast transcripts and the wait for late ones, opt-in YouTube captions with language rules and request limits, Shorts, and recorded reasons when no transcript is available.

### Modified Capabilities
- `source-management`: preview recognizes Apple Podcasts URLs and shows the source kind; feeds have a larger size limit than other fetches.
- `content-collection`: article extraction applies to website feeds; podcast and YouTube items use transcripts instead.
- `digest-generation`:
  - pending-item rules for waiting podcast episodes
  - the Creator updates section
  - summarizing long texts in full
  - long-transcript summary shape
  - token usage
  - the "no new content" message
- `model-settings`: the system learns the selected model's context window from the provider.
- `digest-history`: reopening a saved digest shows its Creator updates as saved.

## Impact

- Backend:
  - Fetching and sources: `net/safe_fetch.py`, `sources/discovery.py`, `sources/feeds.py`, `collection.py`, `api/sources.py`.
  - Digest and model: `digest/runner.py`, `digest/summarize.py`, `llm/client.py`, `llm/prompts.py`, `api/settings.py`, `api/runs.py`, `api/digests.py`.
  - Data and config: `models.py`, `config.py`, one Alembic migration (`0002`), and a new transcript module.
- Frontend: `Sources.tsx` (kind in preview), `Settings.tsx` (YouTube options), `Generate.tsx` (waiting/deferred counts, tokens), `DigestView.tsx` (Creator updates, tokens).
- Dependencies: `youtube-transcript-api` (1.2.x; brings `requests`). lxml is already installed through trafilatura and becomes a direct dependency.
- Configuration: new `CATCHUP_MAX_FEED_BYTES`, `CATCHUP_TRANSCRIPT_WAIT_DAYS`, `CATCHUP_CAPTION_WAIT_HOURS`, `CATCHUP_CAPTIONS_PER_RUN`, `CATCHUP_LONG_ITEM_CHARS`, `CATCHUP_SINGLE_CALL_CHARS`. Removed: `CATCHUP_MAX_ITEM_CHARS`. Update `.env.example` and the README.
- External services: iTunes Lookup API (about 20 calls/minute), podcast transcript hosts, YouTube (opt-in only).
- Not included: speech-to-text, YouTube audio download, per-channel settings, cost in currency.
