# Tasks

Implementer notes:
- Read `proposal.md`, `design.md`, and the five files under `specs/` first. `design.md` holds the data model, API table, defaults, and layout. Follow them; if something there looks wrong, stop and report rather than redesigning.
- Tests must run without network access and without a real API key (respx for HTTP, monkeypatched DNS, a fake LLM client).
- Backend commands run from `backend/` with uv; frontend commands run from `frontend/` with npm.
- Commit after each task group. Do not edit `proposal.md`, `design.md`, or `specs/`.

## 1. Project scaffolding and CI

- [x] 1.1 Create the backend uv project: `backend/pyproject.toml` (Python ≥3.11; FastAPI, uvicorn, SQLAlchemy 2.1, Alembic, Pydantic v2, httpx, feedparser, trafilatura, openai, cryptography; dev: pytest, pytest-cov, respx), `backend/src/catchup/{__init__,main,config}.py` with env-based settings (all `CATCHUP_*` variables and defaults from design.md), an app factory, `GET /api/health`, and the shared error shape. Verify: `uv run pytest` passes a test that calls `/api/health` and a test that a raised app error returns `{"error": {"code", "message"}}`.
- [x] 1.2 Add the database layer: `backend/src/catchup/{db,models}.py` with the engine (WAL, busy_timeout, foreign_keys pragmas), per-request sessions, and every table from design.md "Data Model". Add `backend/alembic/` with the initial migration, applied automatically on startup. Verify: a test runs startup against a temp data dir and asserts all tables exist and `PRAGMA journal_mode` returns `wal`.
- [x] 1.3 Scaffold the frontend in `frontend/` (Vite + React + TypeScript): React Router with routes `/` (Generate), `/sources`, `/settings`, `/digests`, and `/digests/:id` using placeholder pages and a nav bar; `src/api/client.ts` that parses the error shape; a Vite dev proxy from `/api` to `http://127.0.0.1:8000`; Vitest + Testing Library. Verify: `npm test -- --run` passes a test that the nav renders all links, and `npm run build` succeeds.
- [x] 1.4 Serve the built frontend from FastAPI: mount `frontend/dist` when it exists, with an SPA fallback to `index.html` for non-`/api` paths. Verify: a backend test with a temp dist directory gets `index.html` for `/digests/3` and JSON for `/api/health`.
- [x] 1.5 Add `.env.example`, a README "Development setup" section (install, generating `CATCHUP_SECRET_KEY`, running backend and frontend, running tests, and a note that collected content is sent to the configured model provider), a README "Supported sources" section (RSS/Atom feeds and sites that declare a feed or expose one at a common path, e.g. blogs, Bluesky and Mastodon profiles, Reddit subreddits. Not supported yet: X, pages without feeds, podcasts/YouTube, and content behind a login or paywall), a "Commands" section in `AGENTS.md`, and `.github/workflows/ci.yml` running backend pytest and frontend test + build on push and pull request. Verify: the exact commands in the workflow pass locally.

## 2. Model settings

- [x] 2.1 Implement `backend/src/catchup/crypto.py` (Fernet using a key derived from `CATCHUP_SECRET_KEY`). Verify: tests for encrypt/decrypt round trip, and a clear error when the secret is missing.
- [x] 2.2 Implement `backend/src/catchup/llm/client.py`: openai SDK client from `base_url`/key/model; `list_models()`; `chat_json(messages, max_tokens)` using `response_format={"type": "json_object"}`; bounded retries with backoff on empty content, 429, 500, and 503; typed errors `AuthFailed`, `InsufficientBalance`, `RateLimited`, `ProviderError`, `ConnectionFailed`. Make sure HTTP logging never includes the key. Verify: respx-mocked tests for success, empty-then-valid, 401, 402, 429-then-success, 503 exhausting retries, and connection timeout.
- [x] 2.3 Implement `backend/src/catchup/api/settings.py`: `GET` and `PUT /api/settings/model`, `POST /api/settings/model/test`, and `GET` and `PUT /api/settings/preferences` (digest language: `en`, `zh-Hans`, `original`, or free text ≤ 40 chars) per design.md. Verify: tests for every scenario in `specs/model-settings/spec.md` (including that no response body contains the full key), plus preference save/read and `invalid_language` for empty or overlong text.
- [x] 2.4 Build `frontend/src/pages/Settings.tsx`: base URL (default `https://api.deepseek.com`), password-type key field showing `•••• last4` when set, a Test button that fills a model dropdown from the returned list, a digest language selector (English, 简体中文, Same as original, Other with a text field), Save, and error messages per error code. Verify: Vitest tests for the initial load, a successful test populating models, an auth error message, and choosing "Other" showing the text field.
- [x] 2.5 Review fixes (design.md D9):
  - stored key reused only with the unchanged stored `base_url` in `PUT /api/settings/model` and `POST /api/settings/model/test`; otherwise `422 api_key_required`
  - Host allowlist middleware driven by `CATCHUP_ALLOWED_HOSTS` (add it to config, `.env.example`, and README)
  - explicit timeouts in `llm/client.py`: 15 s total for `list_models`; connect 10 s / read 300 s for chat
  - an empty `choices` list treated as empty content and retried
  - `httpx2` declared explicitly in `backend/pyproject.toml`

  Verify: tests for every new scenario in `specs/model-settings/spec.md`, including that no request reaches a changed base URL without a key and that a foreign Host header gets 400 while `localhost` and `127.0.0.1` work; a test that the client passes the configured timeouts; a test for the empty-`choices` retry.

## 3. Source management

- [x] 3.1 Implement `backend/src/catchup/net/safe_fetch.py` per design.md D4 (scheme check, DNS resolution with address checks, manual redirects up to 5 with re-checks, timeouts, 5 MB cap). Verify: tests with monkeypatched DNS for loopback, private, link-local/metadata, a redirect to a private address, timeout, oversize, and an allowed public address.
- [x] 3.2 Implement `backend/src/catchup/sources/{discovery,feeds}.py`: feed-vs-HTML detection, `<link rel="alternate">` discovery with relative URL resolution, common-path probing when no feed is declared (candidate order and limits in design.md D5), single-article detection (D5), and feed parsing from bytes into normalized entries (identity key rules, link, title, UTC `published_at`, plain text from content/summary). Add fixtures in `backend/tests/fixtures/`: RSS 2.0, Atom, entries without ids, entries without dates, malformed-but-parsable XML, HTML with a feed link, HTML article page, and HTML without a feed. Verify: unit tests over all fixtures, plus respx-mocked probing tests:
  - a Reddit-style page whose feed is only at `<path>/.rss`
  - a site whose feed is only at `/feed`
  - no candidate succeeding → `no_feed`
  - probing never exceeding 8 requests or leaving the origin
- [x] 3.3 Implement `backend/src/catchup/api/sources.py`: preview, confirm (re-fetch, duplicate check, first-add marking using `CATCHUP_FIRST_ADD_DAYS`/`MAX`, a confirm-time `source_checks` row), list with last check, and delete. Verify: tests for every scenario in `specs/source-management/spec.md`, including 2 recent + 10 old entries and 8 recent entries giving exactly 5 pending.
- [x] 3.4 Build `frontend/src/pages/Sources.tsx`: URL input → preview card (title, feed URL, up to 5 entries, the follow-the-site notice when present) → Confirm; error messages per code; source list with last check status and possible-gap badge; delete with confirmation. Verify: Vitest tests for the preview, a duplicate error, and list rendering.
- [x] 3.5 Review fixes (design.md D4): a 30 s wall-clock deadline for the whole `safe_fetch`, so slow-drip responses abort, and the NAT64 `64:ff9b::/96` embedded-IPv4 check. Verify: a test with a mocked response that streams slowly past the deadline fails with a timeout error, and a test that `64:ff9b::7f00:1` is blocked.

## 4. Content collection

- [x] 4.1 Implement `backend/src/catchup/collection.py`: check one source (safe fetch → parse → record unseen entries by identity key with a secondary link match), set the outcome (`new_items` / `no_new_items` / `failed` with error) and `possible_gap`, and for new entries with text shorter than `CATCHUP_SHORT_TEXT_CHARS`, fetch the article via `safe_fetch` and extract it with `trafilatura.extract`, falling back to the feed text. Verify: tests for every scenario in `specs/content-collection/spec.md` (repeated entries, late entry with old date, id change with same link, failure then success, possible gap, failure never reported as no new items, short-text extraction and fallback).

## 5. Digest generation

- [ ] 5.1 Implement `backend/src/catchup/llm/prompts.py` and `backend/src/catchup/digest/summarize.py`: per-item summary prompt (contains "json" and an example; follows the `digest_language` setting read at run start, including the `original` rule from design.md D3), truncation to `CATCHUP_MAX_ITEM_CHARS`, reusing a stored summary only when its `summary_language` matches the current setting, 4-way concurrency, and marking `summary_unavailable` after retries are exhausted. Verify: fake-LLM tests counting calls (cached same-language items are not re-summarized; a language change triggers re-summarization), checking that the prompt carries the chosen language, truncation, and the unavailable marking.
- [ ] 5.2 Implement `backend/src/catchup/digest/group.py`: build short refs, call the model, validate output (discard unknown refs, keep the first placement of duplicates, put unplaced items under "Other"), and batch above `CATCHUP_GROUPING_BATCH_CHARS` with a merge call. Verify: fake-LLM tests for unknown refs, omitted items, duplicates, and a forced small batch threshold producing a merged result that contains every item exactly once.
- [ ] 5.3 Implement `backend/src/catchup/digest/runner.py`: run lifecycle and statuses from design.md, a single active run lock, progress counters, collection of every source, summarize → group, saving digest + topics + snapshot `digest_items` and marking items `delivered` in one transaction, immediate failure on `AuthFailed`/`InsufficientBalance`, the `no_new_content` outcome, and startup recovery of unfinished runs. Verify: tests for every scenario in `specs/digest-generation/spec.md` (including a 140-item run fully included, a failure before save leaving items pending, a retry not re-summarizing, and restart recovery).
- [ ] 5.4 Implement `backend/src/catchup/api/runs.py` (`POST /api/digest-runs`, `GET /api/digest-runs/active`, `GET /api/digest-runs/{id}`) and `frontend/src/pages/Generate.tsx`: a Generate button, stage and "x of y" progress via 1-second polling, per-source outcomes with failed and possible-gap indicators, a "no new content" message, a link to the digest on success, and a prompt linking to Settings when the model is not configured; resume showing an active run after a page reload. Verify: API tests for 202, 409 with `active_run_id`, 409 `model_not_configured`, and run details; Vitest tests for progress, no-new-content, not-configured, and failure states.

## 6. Digest history

- [ ] 6.1 Implement `backend/src/catchup/api/digests.py` (list newest first; detail from snapshot tables). Verify: tests for every scenario in `specs/digest-history/spec.md`, including a digest that still opens after its source is deleted and after re-creating the app on the same data directory.
- [ ] 6.2 Build `frontend/src/pages/History.tsx` and `frontend/src/pages/DigestView.tsx`: a list with time, item count, and source count; a digest view with topics, overviews, and items (summary or "summary unavailable", title, source name, date, and a link that opens the original in a new tab). Verify: Vitest tests for the list and digest view rendering.

## 7. Integration and test report

- [ ] 7.1 Add an end-to-end API test: configure settings (mocked provider) → preview and confirm a fixture feed → run → digest saved → second run gives `no_new_content` → fixture feed gains one entry → third run's digest contains only that entry. Verify: the test passes in `uv run pytest`.
- [ ] 7.2 Write `docs/process/test-report-add-core-digest-flow.md` with the commands run, the pass/fail counts, backend coverage from `uv run pytest --cov=catchup`, the frontend test count, and a table mapping each spec scenario to its test(s). Verify: every scenario in the five spec files appears in the table.

Manual verification with a real feed and a real DeepSeek key is done during review by Claude Code with the user, not by the implementer.
