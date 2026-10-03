# Design

Status: Proposal 1 chosen by the user on 2026-10-02 (item ledger + background run + two-stage summarization). Defaults accepted: first add keeps entries from the last 7 days, at most 5 per source; no per-run item cap.

## Context

This is the first code in the repository (`research.md`, "Repository state"). See `proposal.md` for the motivation. The hard parts of the confirmed requirements are:
- no duplicates
- failure shown separately from "no updates"
- no lost items when a source fails
- correct behavior when publish dates are missing or untrustworthy

Sources: `docs/handoff.md:40`, `docs/handoff.md:67-68`, `docs/handoff.md:113`.

External constraints from research:
- DeepSeek is OpenAI-compatible, offers only `json_object` JSON mode, may return empty content, and recently renamed and retired models.
- feedparser has no entry-id fallback and no timeout, and warns against untrusted strings.
- `trafilatura.find_feed_urls` returns article links, not feed URLs.
- SQLAlchemy 2.1 needs Python ≥3.11. Its async SQLite driver isn't truly non-blocking, and SQLite needs WAL to avoid lock errors.
- User-supplied URLs need SSRF protection.

## Goals / Non-Goals

**Goals:**
- A runnable app, both as a dev setup and as one built process, covering: model settings → add an RSS/Atom source → Generate Digest → saved digest → reopen from history.
- Every scenario in the five spec deltas covered by automated tests that run without network access or a real API key.
- A structure that later source types (podcasts, YouTube) plug into without changing the ledger or run model.

**Non-Goals:**
- Podcasts, YouTube, and pages without feeds.
- Deployment and Docker. These belong to a later change; this one only makes FastAPI able to serve the built frontend.
- Authentication and multi-user support. The instance is single-user and local.
- Bookmarks, likes, feedback, "top N" selection, scheduling.
- Visual polish beyond clean, usable layouts.

## Decisions

### D1. Item ledger decides what is new (chosen over per-source time checkpoints)
- An entry is new the first time its identity key is seen for its source. The identity key is the feed id, else the link, else sha256(title + date). A secondary link match catches sites that change their id scheme.
- Items carry `state`: `pending`, `delivered`, or `baseline`. A run digests every `pending` item. Items become `delivered` in the same transaction that saves the digest.
- **Alternative considered (Proposal 2):** a `last_success_at` checkpoint per source, collecting entries whose publish dates fall in `(checkpoint, run_start]`. It was rejected because it depends on publish dates and misses backdated or late entries (`docs/handoff.md:67`). It also runs generation synchronously, with no progress and a single failure point, and would need rework once slower source types arrive.

### D2. Background run in-process (chosen over synchronous request or a job queue)
- `POST /api/digest-runs` creates a `digest_runs` row and starts a daemon thread.
- A module-level lock enforces a single active run; a second request gets a 409 response that names the active run.
- The UI polls the run once per second.
- On startup, runs in `queued`, `collecting`, `summarizing`, or `grouping` are marked `failed` with error kind `interrupted`.
- **Alternatives:** a synchronous request (timeouts, no progress), or Celery/RQ (needs Redis, which is out of proportion for a single-user app, `docs/handoff.md:73`).

### D3. Two-stage summarization
- **Stage 1:** one JSON call per item that has no summary in the current digest language. Input text is truncated to `CATCHUP_MAX_ITEM_CHARS` (default 20000). Up to 4 calls run concurrently. The summary is stored on the item together with `summary_language` and reused by later runs only while the language setting matches. If an item still fails after retries, it is marked `summary_unavailable` for that run.
- **Language:** prompts take the user's `digest_language` setting. Its value is `en`, `zh-Hans`, `original`, or free text for another language, and it is read once at run start. With `original`, each item summary uses the item's own language, and topic titles and overviews use the language most items are written in.
- **Stage 2:** one JSON call groups items into topics. The input is short refs (`i1`, `i2`, ...), titles, source names, and summaries. The output is `{"topics": [{"title", "overview", "item_refs": [...]}]}`.
- Validation of the stage 2 output:
  - Unknown refs are discarded.
  - An item listed twice keeps its first placement.
  - Unplaced items go to "Other".
- Batching: if the stage 2 input exceeds `CATCHUP_GROUPING_BATCH_CHARS` (default 200000), items are grouped in batches. A merge call then combines the batch topics, using topic titles and overviews only, into a final list that maps batch topics to final topics.
- Prompts always contain the word "json" and an example output, as DeepSeek requires. Empty content is retried.
- **Alternative:** a single call for everything. It was rejected because the retry cost and the truncation risk are both higher, and it gives no per-item reuse for a later "most important items" feature.

### D4. Fetching and SSRF guard
- All user-supplied URLs go through `safe_fetch`, which works as follows:
  - Allow only the `http` and `https` schemes.
  - Resolve the host with `getaddrinfo`.
  - Reject the request if any resolved address is private, loopback, link-local (including 169.254.169.254), reserved, multicast, or unspecified.
  - Follow at most 5 redirects manually, re-checking each hop.
  - Apply timeouts of 5 s to connect and 15 s to read.
  - Stop reading after 5 MB.
- feedparser always receives bytes, never a URL or an untrusted string.
- **Alternative:** letting feedparser fetch. It was rejected because it has no timeout and its own docstring warns against untrusted strings.

### D5. Feed discovery
- If the response parses as a feed with entries, or is served with an RSS/Atom content type, it is used as the feed.
- Otherwise, the HTML is searched for `<link rel="alternate" type="application/rss+xml|application/atom+xml">`. Relative URLs are resolved, and the first candidate that parses is used.
- Common-path probing (added 2026-10-02 at the user's request): if the page declares no feed, try these same-origin candidates in order and stop at the first that parses as a feed with entries:
  1. the page URL with `.rss` appended to its path, both without and with a trailing slash. This covers Mastodon `@user.rss` and Reddit `/r/x/.rss`.
  2. `/feed`, `/rss`, `/rss.xml`, `/feed.xml`, `/atom.xml`, `/index.xml` at the origin.
- Probing rules:
  - At most 8 requests, each through `safe_fetch`, all on the same origin.
  - The preview shows the feed URL that was found.
  - When an origin-level path is used for a deeper page, the "whole site" notice is shown.
- Platforms verified on 2026-10-02 to work through this logic:
  - Bluesky and Mastodon profiles declare RSS links.
  - A Reddit subreddit page declares none, but `/.rss` returned a feed when tested from a residential IP. Whether Reddit blocks cloud IPs is unverified.
  - X is not supported. Reading it requires login or the paid X API, so it is deferred (`docs/process/requirements-changes.md`).
- "Single article" detection (`docs/handoff.md:46`):
  - The page has `og:type=article`.
  - Or the page's path is not the site root and the page declares a feed.
  - If either holds, the preview shows a notice that the whole site's feed will be followed.

### D6. Synchronous SQLAlchemy with SQLite WAL
- Connection setup: `PRAGMA journal_mode=WAL`, `busy_timeout=5000`, `foreign_keys=ON` on connect.
- Each thread uses its own session, and writes are kept short.
- Endpoints are plain `def`, so FastAPI runs them in its threadpool.
- Alembic manages the schema from the first migration.

### D7. API key protection
- The key is encrypted with Fernet, using a key derived from `CATCHUP_SECRET_KEY`. Only `key_set` and `api_key_last4` are ever returned.
- The key is never logged. HTTP client logging is configured so that it doesn't log headers.
- Saving a key without `CATCHUP_SECRET_KEY` fails with instructions for generating one.

### D8. Digest content is snapshotted
- Digest items copy the title, link, source name, publish date, and summary at save time.
- This lets a saved digest reopen unchanged even after its source is deleted, as the source-management spec requires.

## Architecture

```
React SPA (Settings · Sources · Generate · History · Digest)
        │  JSON over /api (polling for runs)
FastAPI app ── api/ (settings, sources, runs, digests)
        │
        ├── services: sources (discovery, feeds) · collection · digest (runner, summarize, group)
        ├── net/safe_fetch (httpx + SSRF guard)     ├── llm/client (openai SDK, base_url)
        └── db (SQLAlchemy models, Alembic) ── SQLite file in CATCHUP_DATA_DIR (WAL)
```

In production, FastAPI serves `frontend/dist` as static files with an SPA fallback; `/api/*` is excluded from the fallback. In development, Vite runs on its own server and proxies `/api` to uvicorn.

Backend layout: `backend/pyproject.toml` (Python ≥3.11, uv) and `backend/src/catchup/`:
- `main.py`, `config.py`, `db.py`, `models.py`, `schemas.py`, `crypto.py`
- `net/safe_fetch.py`
- `sources/discovery.py`, `sources/feeds.py`
- `collection.py`
- `llm/client.py`, `llm/prompts.py`
- `digest/runner.py`, `digest/summarize.py`, `digest/group.py`
- `api/{settings,sources,runs,digests}.py`

Supporting directories: `backend/alembic/` and `backend/tests/` (with `tests/fixtures/`).

Frontend layout: `frontend/` (Vite React TS):
- `src/api/client.ts` and typed endpoint functions
- `src/pages/{Settings,Sources,Generate,History,DigestView}.tsx`
- a small shared component set

## Data Model

| Table | Key columns |
| --- | --- |
| `model_config` | `id` (single row), `base_url`, `model_id`, `api_key_encrypted`, `api_key_last4`, `updated_at` |
| `app_settings` | `id` (single row), `digest_language` (default `en`), `updated_at` |
| `sources` | `id`, `title`, `site_url`, `feed_url` (unique), `input_url`, `created_at`, `last_check_at`, `last_check_status` |
| `items` | `id`, `source_id` (FK, cascade delete), `identity_key`, `link`, `title`, `published_at` (UTC, nullable), `discovered_at`, `content_text`, `content_origin` (`feed` \| `article`), `summary` (nullable), `summary_language` (nullable), `state` (`pending` \| `delivered` \| `baseline`); unique (`source_id`, `identity_key`); index (`source_id`, `link`) |
| `source_checks` | `id`, `run_id` (nullable; null for the confirm-time check), `source_id` (FK, cascade), `status` (`new_items` \| `no_new_items` \| `failed`), `possible_gap`, `error`, `http_status`, `entries_seen`, `new_count`, `checked_at` |
| `digest_runs` | `id`, `status` (`queued` \| `collecting` \| `summarizing` \| `grouping` \| `succeeded` \| `no_new_content` \| `failed`), `items_total`, `items_done`, `error_kind`, `error_message`, `digest_id` (nullable), `started_at`, `finished_at` |
| `digests` | `id`, `run_id`, `created_at`, `model_id`, `item_count`, `source_count` |
| `digest_topics` | `id`, `digest_id` (FK), `position`, `title`, `overview` |
| `digest_items` | `id`, `digest_id` (FK), `topic_id` (FK), `position`, `item_id` (nullable, FK set null), `title`, `link`, `source_name`, `published_at`, `summary`, `summary_unavailable` |

Instance settings (environment variables):

| Variable | Default | Purpose |
| --- | --- | --- |
| `CATCHUP_DATA_DIR` | `./data` | SQLite location |
| `CATCHUP_SECRET_KEY` | none (required to save a key) | API key encryption |
| `CATCHUP_FIRST_ADD_DAYS` | 7 | First-add lookback window |
| `CATCHUP_FIRST_ADD_MAX` | 5 | First-add item limit per source |
| `CATCHUP_SHORT_TEXT_CHARS` | 500 | Below this, fetch the article page for its text |
| `CATCHUP_MAX_ITEM_CHARS` | 20000 | Item text truncation for stage 1 |
| `CATCHUP_GROUPING_BATCH_CHARS` | 200000 | Stage 2 batching threshold |

The digest language is a user setting stored in `app_settings`, not an environment variable. The user picks it in Settings during initial setup.

## API

All errors use the shape `{"error": {"code": str, "message": str, ...}}`.

| Method & path | Request | Response |
| --- | --- | --- |
| `GET /api/health` | — | `{"status": "ok"}` |
| `GET /api/settings/model` | — | `{base_url, model_id, key_set, api_key_last4}` |
| `PUT /api/settings/model` | `{base_url, model_id, api_key?}` (empty key keeps the stored one) | same as GET; `400 secret_not_configured` |
| `POST /api/settings/model/test` | `{base_url?, api_key?}` (missing fields fall back to stored values) | `{ok: true, models: [str]}`; errors `auth_failed`, `connection_failed`, `insufficient_balance`, `provider_error` |
| `GET /api/settings/preferences` | — | `{digest_language}` |
| `PUT /api/settings/preferences` | `{digest_language}` (`en`, `zh-Hans`, `original`, or free text ≤ 40 chars) | `{digest_language}`; `422 invalid_language` for empty or overlong text |
| `POST /api/sources/preview` | `{url}` | `{feed_url, site_url, title, follows_site_feed_notice, entries: [{title, link, published_at}] (≤5)}`; `422` with `invalid_url`, `fetch_failed`, `blocked_address`, `no_feed`, `not_a_feed`, or `duplicate` (+`existing_source`) |
| `POST /api/sources` | `{feed_url}` | `201` source; `409 duplicate` |
| `GET /api/sources` | — | `[{id, title, feed_url, site_url, last_check_at, last_check_status, possible_gap}]` |
| `DELETE /api/sources/{id}` | — | `204` |
| `POST /api/digest-runs` | — | `202` run; `409 run_active` (+`active_run_id`); `409 model_not_configured` |
| `GET /api/digest-runs/active` | — | run, or `null` |
| `GET /api/digest-runs/{id}` | — | `{id, status, items_total, items_done, error_kind, error_message, digest_id, source_checks: [{source_id, source_title, status, possible_gap, error}]}` |
| `GET /api/digests` | — | `[{id, created_at, item_count, source_count}]` newest first |
| `GET /api/digests/{id}` | — | `{id, created_at, model_id, topics: [{title, overview, items: [{title, link, source_name, published_at, summary, summary_unavailable}]}]}` |

## Risks / Trade-offs

- [The feed drops entries between checks] → Possible-gap flag, shown in the UI. Not recoverable without archives; documented.
- [DNS rebinding between the check and the connect (TOCTOU) in `safe_fetch`] → The single-user, self-hosted setting lowers the risk. The residual risk is documented, and pinning the connection to the resolved IP is a later hardening task.
- [A large backlog makes many stage 1 calls, which costs time and money] → Cached summaries, 4-way concurrency, and an "x of y" progress display. The user explicitly chose no cap.
- [In-process thread state is lost on restart] → Startup recovery marks the run failed, and items stay pending.
- [The model ignores the JSON format or returns empty content] → JSON mode, an example in the prompt, bounded retries, and validation with the "Other" fallback.
- [SQLite write contention between run threads and API requests] → WAL, `busy_timeout`, short transactions.
- [Collected content is sent to the provider] → Stated in the README setup section (D-004).

## Migration Plan

- This is a new application, so there is no existing data. The initial Alembic migration creates all tables. Startup runs `alembic upgrade head` automatically, which keeps local setup to one step.
- No feature flags. Rollback means reverting the change's commits and deleting the local data directory.

## Testing Plan

- Backend: pytest with no network access.
  - httpx traffic is mocked with respx.
  - DNS resolution is monkeypatched for the SSRF tests.
  - A fake LLM client is injected through FastAPI dependency overrides.
  - Time is frozen, or passed in explicitly.
  - Feed and HTML fixtures live in `backend/tests/fixtures/`.
  - Every spec scenario maps to at least one test. The mapping is recorded in the test report.
- Frontend: Vitest with Testing Library for page states (loading, error, empty, populated).
- End-to-end: an API-level test runs the whole flow, including the repeat-run and new-entry cases.
- Coverage: `pytest --cov`, summarized in `docs/process/test-report-add-core-digest-flow.md`.
- Manual verification during review (not by the implementer): a real feed and a real DeepSeek key, run by Claude Code with the user. Results are recorded in the test report.

## Open Questions

- None blocking. (Resolved 2026-10-02: the digest language is chosen by the user in Settings during initial setup rather than through an environment variable.)
