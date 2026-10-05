# Podcast and video sources verification (2026-10-05)

Change: `add-podcast-and-video-sources` (#5 and #6). Tests used hand-written
fixture feeds/transcripts and fake model clients. DNS and unmocked connections
are blocked by the backend test fixture. No test contacted YouTube, Apple,
podcast hosts, or a model provider; no real keys were used. Timed tests use
injected clocks, spacer sleeps, and fake caption clients.

| Check | Result |
| --- | --- |
| `cd backend && uv run pytest --cov=catchup --cov-report=term` | **327 passed**, 96% statement coverage (1708/1782); `runner.py` 99%, `convert.py` 91%, `youtube.py` 98% |
| `cd frontend && npm test -- --run` | **34 passed** |
| `cd frontend && npm run build` | TypeScript and Vite build passed |
| `openspec validate add-podcast-and-video-sources --strict` | Passed |
| `docker build -t catchup:podcast-video-local .` | Passed on Docker Desktop 29.8.0 |
| `scripts/docker-smoke.sh catchup:podcast-video-local` | Passed: healthy container, API/UI, preferences persisted across restart, non-root process, database on throwaway volume, no `.env` or source tree in image |

The smoke script's preference assertion was updated for the two new response
fields without dropping its saved-language and restart assertions. Its
throwaway container and volume were removed by its cleanup trap. The image
was not pushed or tagged as a release; CI job names were not changed.

## Requirement checks

- **Source recognition / limits / Apple:** `test_sources_api.py`,
  `test_safe_fetch.py` and `test_feed_cache.py` check majority-audio and
  YouTube host classification, non-audio podcast posts, larger feeds without
  an enlarged preview cache, the unchanged article cap, and Apple show and
  episode lookup including missing/invalid feed metadata.
- **Podcast transcripts:** `test_feed_transcripts.py`,
  `test_transcript_convert.py` and `test_podcast_collection.py` check
  candidate ranking, nonstandard namespace/SRT types, malformed entity
  recovery, no DTD entity expansion, feedparser fallback, five conversions,
  fallback fetches, delayed transcripts, summary invalidation, and per-item
  error containment.
- **Creator updates / delivery:** `test_creator_updates.py` checks waits,
  expiry after failed feed checks, failed-save rollback, only-updates digests,
  ordering/grouping, once-only delivery, and the saved wait value.
  `DigestView.test.tsx` and `Generate.test.tsx` check labels, counts and order.
- **YouTube:** `test_youtube_captions.py`, `test_youtube_shorts.py` and
  `test_caption_pass.py` check opt-in defaults, original-language track
  selection without translation, spaced requests with `trust_env=False`,
  every mapped exception, Short skipping, the 20-video cap, stop-on-block,
  retries, deferral and recovery. `Settings.test.tsx` checks the toggles and
  Terms of Service notice.
- **Long text / usage:** `test_llm_client.py`, `test_digest_stages.py`,
  `test_long_summaries.py`, `test_digest_runner.py`, and the digest/run UI
  tests check context-window parsing and caching, complete text in one or
  three parts, long-transcript shape, concurrent token accounting and the
  run/digest totals (including missing usage and failed runs).

**Not attempted here:** live requests to Apple, YouTube, podcast hosts or
DeepSeek, and manual evaluation of a real digest. Those live checks belong
to reviewer/user verification with their own credentials, not automated
tests. No CI workflow ran locally; the existing `backend`, `frontend`, and
`docker` job names were left unchanged.
