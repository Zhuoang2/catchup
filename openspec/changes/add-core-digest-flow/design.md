# Design: add-core-digest-flow

Status: awaiting user choice

## Solution Proposals

Context:
- Request: Build the first working slice of CatchUp: configure a DeepSeek model (OpenAI-compatible), add one RSS/Atom source with preview and confirm, click Generate Digest, collect what is new since the last successful check, produce a topic-grouped digest with source names and original links, then save it and reopen it later.
- Research Source: `research.md` sections "Required core flow", "Open items that touch the core flow", "External facts" (DeepSeek, RSS/Atom, stack libraries, SSRF).

### Shared by both proposals

These follow directly from the research and accepted decisions, so they don't differ between options:

- Layout: `backend/` (FastAPI, sync SQLAlchemy 2.1 + Alembic, SQLite in WAL mode, managed with uv) and `frontend/` (React + Vite + TypeScript, built into static files that FastAPI serves). One process and one container (D-006, `docs/process/decision-log.md:35-40`). Sync endpoints, because SQLAlchemy's SQLite async driver isn't truly non-blocking (research: stack libraries).
- Fetching: httpx with explicit timeouts and a size cap. feedparser parses the downloaded bytes, because it has no timeout and its docstring warns against passing untrusted strings (research: feedparser). An SSRF guard on every user-supplied URL resolves DNS, rejects private, loopback, link-local and metadata IPs, and follows redirects manually with re-checks (research: SSRF).
- Feed discovery on add: if the URL is a feed, use it. If it is an HTML page, read `<link rel="alternate" type="application/rss+xml|atom+xml">`. `trafilatura.find_feed_urls` returns article links, not feed URLs, so it can't be used here (research: trafilatura). A page with no feed is reported as unsupported. When the pasted URL looks like a single article, the preview states that CatchUp will follow the whole site's feed (`docs/handoff.md:46`).
- Item identity for dedupe: `entry.id`, else `link`, else a hash of title + date, unique per source. feedparser has no id fallback (research: feedparser).
- Model config: one stored config with base URL, model ID and API key. The key is encrypted at rest with a key from the `CATCHUP_SECRET_KEY` env var and never returned by the API (only its last 4 characters). "Test connection" calls `GET /models`, which also fills the model picker. Model IDs are never hard-coded, because DeepSeek renamed and retired models in September 2026 (research: DeepSeek).
- LLM calls: `openai` SDK with `base_url`; JSON mode (`json_object`) with "json" plus an example in the prompt. Retry on empty content, 429, 500 and 503 with backoff; 401 and 402 are shown to the user as configuration or balance errors (research: DeepSeek errors). The model returns item IDs only. Links and source names are always rendered from the database, so citations cannot be invented.
- UI pages (minimal styling in this change): Settings, Sources (add → preview → confirm, list, delete), Generate, Digest view, History.
- Tests: pytest with recorded feed fixtures, a fake LLM client and frozen time; Vitest for a few components; GitHub Actions CI running both.

---

### Proposal 1 — Item ledger + background run with progress, two-stage summarization

- Overview: Every check stores the feed's entries as items, deduped by identity. "New content" means confirmed items that no saved digest has included yet. Generation runs as a background task that the UI polls for progress. It summarizes each item once (cached), then makes one call to group the summaries into topics.
- Key Changes:
  - Data model: `sources`, `items` (identity key, title, link, published_at, content excerpt, cached summary, `state`: pending | delivered | baseline), `source_checks` (per run and source: ok_new | ok_empty | failed, error, HTTP status, item counts), `digest_runs` (queued | collecting | summarizing | succeeded | failed, progress, error), `digests`, `digest_items`, `model_config`.
  - Semantics of "since the last successful request" (`docs/handoff.md:40`): each source is checked on every run. Items a failed source couldn't fetch are simply collected on its next successful check, so no global timestamp can hide them (`docs/handoff.md:68`). Publish dates are used only for ordering, display and the first-add lookback, so missing or untrustworthy dates don't lose items (`docs/handoff.md:67`).
  - First add: entries in the feed at confirm time become `pending` if published in the last 7 days (at most 5 per source). The rest become `baseline` and are never digested. Both values are settings.
  - How new vs old is decided: an item is **new the first time its identity key is seen for that source** (identity key, with link as a secondary match in case a site changes its id scheme). Known keys are skipped, and publish dates play no part. A run digests every `pending` item, and the items become `delivered` only once the digest is saved. An entry edited after publication keeps its id, so it counts as old (page-change detection is out of scope).
  - Feed-gap warning: feeds keep only their latest N entries. If a successful check finds no previously seen key among the entries (for a source that already has items), the check is flagged "possible gap", meaning older entries may have dropped off the feed between checks. The UI shows this flag.
  - Backlog (updated 2026-10-02 after user feedback): **no per-run cap.** Every pending item is digested. The UI shows progress as "item x of y". Stage 2 receives only short per-item summaries; if they exceed a safe input size, they are grouped in batches and then merged. Choosing only the most important items is a later feature (`docs/process/requirements-changes.md`).
  - Execution: `POST /api/digest-runs` returns a run ID. Work happens in an in-process background thread, one run at a time. `GET /api/digest-runs/{id}` reports progress and per-source check status. On startup, any run left unfinished is marked failed. Items are marked `delivered` only after the digest is saved, so a failed run leaves them pending for the retry.
  - Summarization: stage 1 summarizes each item and caches the result, so a retry doesn't pay again. Stage 2 sends the item summaries and IDs and gets back topics with overviews and item IDs. The server rejects unknown IDs, and any item the model leaves out goes under "Other".
  - API: `/api/settings/model` (GET, PUT, POST test); `/api/sources` (POST preview, POST confirm, GET, DELETE); `/api/digest-runs` (POST, GET by ID); `/api/digests` (GET list, GET by ID).
  - Spec capabilities (new): `model-settings`, `source-management`, `content-collection`, `digest-generation`, `digest-history`.
- Trade-offs:
  - Benefits:
    - Partial failures, retries and missing dates are handled by construction, which directly covers the acceptance scenarios: no repeats, failure shown separately from no-updates, retry neither misses nor duplicates (`docs/handoff.md:113`).
    - Progress display keeps long gaps understandable, and per-item summaries prepare for a later "most important items" feature.
    - Cached per-item summaries cut retry cost.
    - The run and check records are good material for the tech spec and the demo.
  - Costs:
    - More tables and states, and a background thread whose state must be recovered on restart.
    - N+1 model calls per run, so it is slower than one call (mitigated by caching and by running stage-1 calls with small concurrency).
    - "Since the last successful request" becomes "everything not yet delivered since each source's last successful check". The meaning is the same, but the wording shifts from a time window to a ledger. See Open Questions.
- Validation:
  - Unit tests: item identity fallbacks; SSRF guard (private, loopback, metadata and redirect cases); feed discovery from fixture HTML.
  - Collection tests with fixtures:
    - a second run with no new entries produces no new digest items
    - a feed whose entries are all unseen (after earlier items exist) is flagged "possible gap"
    - a site that changes an entry's id but keeps its link does not produce a duplicate
    - a failing source shows `failed`, not `ok_empty`
    - after a failed run, the retry delivers exactly the previously pending items once
    - an entry with a missing or old publish date added later is still collected
  - LLM tests with a fake client: empty-content retry; unknown IDs rejected; omitted items appear under "Other".
  - Restart test: a run left "summarizing" is marked failed on startup, and its items are still pending.
  - Manual end-to-end run against a real feed and DeepSeek; record the result in the change's review notes.
- Open Questions:
  - Do you accept the ledger meaning of "since the last successful request"?
  - First-add defaults (7 days, 5 per source): OK as starting values? (The backlog cap was dropped at the user's request.)

---

### Proposal 2 — Per-source time checkpoints + synchronous generation, single-pass summarization

- Overview: Each source keeps a `last_success_at` checkpoint. Generate Digest runs inside the HTTP request. For each source it collects entries published after the checkpoint and up to the run start, advancing the checkpoint only if that source succeeded. One model call turns all collected items into the topic-grouped digest.
- Key Changes:
  - Data model: `sources` (with `last_success_at`), `items` (unique identity key, to guard against duplicates), `digests` (with per-source check results stored as JSON), `digest_items`, `model_config`.
  - Semantics: a literal time window `(last_success_at, run_started_at]` per source, using `published_parsed` or `updated_parsed` (UTC per feedparser). Entries with no date are treated as new if their identity is unseen. First add sets the checkpoint to confirm time minus 7 days.
  - Execution: `POST /api/digests` blocks until done. The UI shows a spinner, and there is no run resource or progress.
  - Summarization: one JSON-mode call with all items (truncated content) returns topics, item summaries and item IDs. DeepSeek's 1M context makes this possible (research: DeepSeek models), but `max_tokens` must be raised well above the 8K default.
  - API: `/api/settings/model`, `/api/sources` (same as Proposal 1); `/api/digests` (POST generate, GET list, GET by ID).
  - Spec capabilities (new): `model-settings`, `source-management`, `digest-generation`, `digest-history`. Collection rules live inside `digest-generation`.
- Trade-offs:
  - Benefits:
    - Fewer tables and no background-execution or restart-recovery logic, so it is faster to build.
    - Matches the proposal's wording literally (`docs/proposal.md:24`).
    - One model call per run.
  - Costs:
    - Correctness depends on publish dates: an entry backdated or published late, after the checkpoint already moved past its date, is missed (`docs/handoff.md:67`).
    - A long request (many sources, long content) risks browser or proxy timeouts and gives no progress.
    - One model failure loses the whole run, and the retry pays the full cost again.
    - A large single output risks truncated JSON, and there is no natural backlog cap.
    - It would likely need reworking into Proposal 1's shape once podcasts or videos (slow transcript fetches) arrive in P2.
- Validation:
  - Unit tests: window boundaries (exactly at the checkpoint, timezone offsets, missing dates); checkpoint advances only for successful sources.
  - Same fixture tests for "no new entries → nothing new" and "failed vs empty".
  - Fake-LLM tests for truncated or empty JSON.
  - Manual end-to-end run with a real feed and DeepSeek, timing a run with several sources.
- Open Questions:
  - What request timeout is acceptable before the UI should show an error?
  - How should a backdated entry be handled (accept misses, or add an identity-based catch-up, which moves this toward Proposal 1)?

---

Recommendation: **Proposal 1.** The hardest confirmed requirements are no duplicates, failure shown separately from no updates, partial failure without lost items, and missing or untrustworthy dates (`docs/handoff.md:40`, `docs/handoff.md:67-68`, `docs/handoff.md:113`). Proposal 1 meets these by construction, while Proposal 2 depends on publish dates and would need rework when slower source types arrive in the next phase. The extra complexity (run state, two-stage summarization) is modest and well covered by tests.
