# Research: CatchUp core digest flow

- Date: 2026-10-02
- Query: What do the project materials currently require and decide for the core flow (configure a DeepSeek model → add one RSS/Atom source with preview and confirm → Generate Digest → collect items new since the last successful check → topic-grouped digest with source names and links → save and reopen), and what external facts does the implementation depend on?
- Git ref: main @ 3efdf4b
- Change: `add-core-digest-flow`

## Summary

The repository contains no application code. It holds planning documents, OpenSpec scaffolding with no specs, process logs, and agent instructions. The required core flow is described in `docs/handoff.md` §3 and `docs/proposal.md` "Planned Features". Many details the flow depends on are explicitly open in `docs/handoff.md` §5: time boundaries, checkpoint definition, first-run lookback, and partial-failure handling. The accepted decisions so far are the stack (FastAPI + SQLite + React/Vite/TS, single container) and an OpenAI-compatible model adapter developed against DeepSeek. External checks on 2026-10-02 established three facts the flow depends on. DeepSeek's API is OpenAI-compatible and supports JSON mode, with caveats. feedparser provides entry ids, UTC dates, and conditional GET, but has no id fallback and no timeout. trafilatura's `find_feed_urls` returns article links, not feed URLs.

## Detailed Findings

### Repository state
- Tracked content is planning material only: `AGENTS.md` (with `CLAUDE.md` symlinked to it), `docs/handoff.md`, `docs/proposal.md`, `docs/process/*.md`, `assets/catchup-workflow.png`, the proposal PDF, and OpenSpec/agent skill scaffolding under `openspec/`, `.claude/`, `.factory/`. Commits: `22838a0`, `0dadbb7`, `54294b4`, `3efdf4b`.
- `openspec/config.yaml` has no `context:` or `rules:` set; it only contains the commented template (`openspec/config.yaml:1-30`).
- No package manifests, source directories, tests, CI config, Dockerfile, or `.env.example` exist.
- `.gitignore` already excludes `.env*` (except `.env.example`), `*.db`, `*.sqlite3`, `data/`, `.venv/`, `node_modules/`, `dist/` (`.gitignore:8-29`).
- Local toolchain (checked 2026-10-01): Python 3.11.4, uv 0.11.30, Node 20.19.0, Docker 29.8.0, gh logged in as `Zhuoang2`.

### Required core flow (confirmed requirements)
- Step 1, model configuration: the user configures a supported model API, their own credentials, and a model. The flow is not locked to one model, and the compatible interface is not chosen in the handoff — `docs/handoff.md:37`. The proposal says credentials are provided by the user and managed through the backend of their own instance — `docs/proposal.md:40`.
- Step 2, add source: paste a URL, identify and preview name/address/recent content, save on confirm. Duplicate or unsupported sources must be explained — `docs/handoff.md:38`; `docs/proposal.md:32`.
- Step 3, trigger: the user clicks Generate Digest manually — `docs/handoff.md:39`; `docs/proposal.md:24`.
- Step 4, collection: fetch content between the **last successful request and the current request**. Distinguish a failed check from a successful check with no updates, and avoid duplicate entries — `docs/handoff.md:40`; `docs/proposal.md:34`.
- Step 5, digest: summarize, organize by topic, keep source names and original links — `docs/handoff.md:41`; `docs/proposal.md:38`.
- Step 6, history: save digests for later viewing. Bookmarks, likes, and feedback come after the core flow works — `docs/handoff.md:42`; `docs/proposal.md:42`.
- A single article link and subscribing to its source are different operations. When a single article is recognized, the scope being followed must be made clear — `docs/handoff.md:46`.
- Only new-article discovery is in scope for websites. Support for arbitrary websites is not promised — `docs/handoff.md:45`.
- With a cloud model, content is sent to that model service; "self-hosted" does not mean all processing is local — `docs/handoff.md:33`.
- The workflow figure shows the same five stages: Add Sources (Paste URL · Preview · Confirm) → Generate Digest → Collect Updates (new content since the last successful request) → Summarize by Topic (AI summaries with source links) → Read & Revisit (explore originals · browse history) — `assets/catchup-workflow.png`.

### Suggested acceptance scenarios already in the materials
- No new content → old items are not regenerated; failure and no-update are shown separately; retries neither miss nor duplicate items; history survives an app restart; summary facts trace back to sources; missing captions are reported as unsupported — `docs/handoff.md:113`. The handoff marks these as suggestions with no code or tests yet — `docs/handoff.md:114`.
- The handoff's suggested first end-to-end slice is configure model → add one supported source → collect new content → generate a digest with citations → save and reopen — `docs/handoff.md:109`.

### Open items that touch the core flow (from the handoff, unresolved)
- First-generation lookback, and how much history to backfill when a source is first added — `docs/handoff.md:66`.
- Precise definition of a successful request; partial-failure re-check and retry; timezones and time boundaries; missing or untrustworthy publish dates — `docs/handoff.md:67`.
- Per-source success checkpoints are a suggestion, not a decision. A global success time must not hide content a failed source didn't collect — `docs/handoff.md:68`.
- Large backlogs after long inactivity: batching, length, API cost, progress indication — `docs/handoff.md:69`.
- Personal vs shared instance; credential and data isolation for a demo site — `docs/handoff.md:70`.
- Summary-quality evaluation samples and criteria — `docs/handoff.md:71`.
- The handoff prefers simple solutions proportionate to the course; no multi-agent setup, microservices, or plugins just to look substantial — `docs/handoff.md:73`.

### Accepted decisions relevant to the flow
- D-004: The first adapter is OpenAI-compatible Chat Completions with configurable base URL, model, and key, developed against DeepSeek. Setup docs must say that content is sent to the provider — `docs/process/decision-log.md:24-28`.
- D-006: FastAPI + SQLite (SQLAlchemy) JSON API; React + Vite + TypeScript built to static files and served by FastAPI; single container — `docs/process/decision-log.md:35-40`.
- D-001 / D-007: Workflow is RePPIT → Droid implements `tasks.md` in a worktree → Claude Code reviews → archive. Plans must be committed before Droid runs — `docs/process/decision-log.md:5-11`, `docs/process/decision-log.md:42-46`; `AGENTS.md:18-30`.
- The AGENTS.md summary of accepted and open decisions is at `AGENTS.md:14`.

### Process-evidence obligations that apply while building
- Decisions, requirement changes, and real AI usage (prompts, outcomes, failures, adjustments) are logged in `docs/process/`. Test results go into change review notes and later a coverage summary. No secrets go in these files — `AGENTS.md:32-41`.
- The course brief requires automated tests with documented coverage and an evaluation of AI-assisted QA; the handoff summarizes this at `docs/handoff.md:88`. The brief itself is gitignored (`.gitignore:2-3`).

### External facts: DeepSeek API (checked 2026-10-02)
- OpenAI-format base URL `https://api.deepseek.com`, `Authorization: Bearer <key>`, `POST /chat/completions`. The official OpenAI SDK works by setting `base_url`. Source: https://api-docs.deepseek.com/
- Current model IDs: `deepseek-flash` (V4.1-Flash; 1M context; max output 384K; JSON output, tool calls, vision) and `deepseek-v4-pro`, which still appears on the pricing and API pages. A 2026-09-10 notice says V4-Pro is being phased out, and since 2026-09-14 its requests route to V4.1-Flash. The older names `deepseek-v4-flash*` are still accepted. Whether `deepseek-chat` and `deepseek-reasoner` still work is unverified. Sources: https://api-docs.deepseek.com/quick_start/pricing, https://api-docs.deepseek.com/news/news260910
- `max_tokens` range is 1–393,216; the default is 8K (64K in thinking mode). Source: https://api-docs.deepseek.com/api/create-chat-completion
- JSON mode: `response_format={"type":"json_object"}` (only `text` and `json_object` are allowed). The prompt must contain the word "json", ideally with an example. `max_tokens` must be large enough to avoid truncation. The API "may occasionally return empty content". `json_schema` is not documented. Source: https://api-docs.deepseek.com/guides/json_mode
- Tool calls are supported. Strict tool schemas are beta (`/beta` base URL; all properties required; `additionalProperties: false`; no min/max length or items). Source: https://api-docs.deepseek.com/guides/tool_calls
- Errors: 400 bad format, 401 wrong key, 402 insufficient balance, 422 bad parameters, 429 rate limit, 500 server error, 503 overloaded. 500 and 503 are documented as "retry after a short wait". Per-account concurrency limits apply. The connection is closed if inference hasn't started within 10 minutes; non-streaming requests receive blank keep-alive lines while waiting. Sources: https://api-docs.deepseek.com/quick_start/error_codes, https://api-docs.deepseek.com/quick_start/rate_limit
- Key checks: `GET /models` returns models with `context_window` and `max_output_tokens`; `GET /user/balance` returns `is_available` and `balance_infos`. Whether these calls are free is unverified. Sources: https://api-docs.deepseek.com/api/list-models, https://api-docs.deepseek.com/api/get-user-balance
- `openai` Python SDK latest: 3.23.0 (2026-10-01), Python ≥3.10. Source: https://pypi.org/project/openai/

### External facts: RSS/Atom handling (checked 2026-10-02)
- feedparser 6.0.14 (2026-07-30, Python ≥3.10).
  - `entry.id` comes from Atom `<id>`, RSS 1.0 `rdf:about`, or RSS 2.0 `<guid>`; `entry.guid` is an alias. There is **no fallback** when the element is missing: `e.get('id')` returns None (tested locally). A `<guid>` with isPermaLink missing or "true" is copied into `link` when no link exists. Source: https://github.com/kurtmckee/feedparser/blob/v6.0.14/docs/reference-entry-id.rst
  - `published_parsed` and `updated_parsed` are `time.struct_time` in UTC, with offsets converted. Source: https://github.com/kurtmckee/feedparser/blob/v6.0.14/docs/date-parsing.rst
  - `bozo=1` means the XML is not well-formed (parsing still proceeds) or the URL fetch failed; details are in `bozo_exception`. Source: https://github.com/kurtmckee/feedparser/blob/v6.0.14/docs/bozo.rst
  - feedparser can fetch URLs itself via urllib, with `etag=` and `modified=` for conditional GET. A 304 gives `status == 304` with no entries; 301 means update the URL, 410 means stop polling. No timeout parameter was found in the source. `parse()` also accepts bytes or a stream plus `response_headers=`. Its docstring warns that untrusted strings may trigger network or filesystem access and says to wrap content in `io.BytesIO`. HTML sanitizing is on by default. Sources: https://github.com/kurtmckee/feedparser/blob/v6.0.14/docs/http-etag.rst, feedparser `api.py`
- trafilatura 2.2.0 (2026-07-31, Python ≥3.10).
  - `trafilatura.feeds.find_feed_urls(url, target_lang=None, external=False, sleep_time=2.0) -> list[str]` returns the **article links inside the discovered feeds**, not the feed URLs. The docs example is misleading on this point.
  - `fetch_url()` returns the HTML string or None.
  - `extract()` returns text in txt, markdown, json, and other formats, or None.
  - Sources: trafilatura `feeds.py`, `downloads.py`, `core.py`; https://trafilatura.readthedocs.io/en/latest/usage-python.html
- Earlier feasibility research (2026-10-01) on YouTube RSS, YouTube transcripts, and podcast transcripts is recorded in `docs/process/ai-usage-log.md:33-42`. Those source types are outside this change's scope (RSS/Atom only).

### External facts: stack libraries (checked 2026-10-02)
- Latest stable versions:

  | Package | Version | Notes |
  | --- | --- | --- |
  | FastAPI | 0.142.2 | Python ≥3.10 |
  | SQLAlchemy | 2.1.2 | **Python ≥3.11** |
  | Alembic | 1.20.0 | |
  | Pydantic | 2.13.5 | |
  | httpx | 0.28.1 | released 2024-12, still the latest |
  | uvicorn | 0.54.0 | |
  | pytest | 9.1.1 | |
  | react | 19.3.0 | npm |
  | vite | 8.3.2 | npm |
  | typescript | 7.0.2 | npm |

  Sources: PyPI and npm registry JSON.
- FastAPI's SQL tutorial uses a sync engine with `check_same_thread=False`. FastAPI runs plain `def` endpoints in a threadpool and advises `def` for blocking DB libraries. Sources: https://fastapi.tiangolo.com/tutorial/sql-databases/, https://fastapi.tiangolo.com/async/
- SQLAlchemy 2.1 SQLite docs: aiosqlite "does not actually use non-blocking IO" (it uses a thread per connection). "Database is locked" errors are common, especially without WAL. Source: https://docs.sqlalchemy.org/en/21/dialects/sqlite.html
- SQLite WAL (`PRAGMA journal_mode=WAL`, persistent): readers and writers don't block each other, and there is one writer at a time. All processes must be on the same host (no network filesystems). Source: https://www.sqlite.org/wal.html

### External facts: fetching user-supplied URLs (SSRF)
- OWASP SSRF cheat sheet:
  - Prefer allowlists over denylists.
  - Validate IPs with tested libraries, watching for encoding tricks.
  - Block private, loopback, and link-local ranges.
  - Resolve DNS and check the resulting IP (DNS rebinding).
  - Disable automatic redirects.
  - Block cloud metadata addresses such as 169.254.169.254.
  - The fetch tool summarized this source; it is not quoted verbatim. https://cheatsheetseries.owasp.org/cheatsheets/Server_Side_Request_Forgery_Prevention_Cheat_Sheet.html

## Code References
- No application code exists yet.
- `docs/handoff.md:35-47` — confirmed core flow and source scope
- `docs/handoff.md:59-73` — open implementation questions
- `docs/handoff.md:105-114` — suggested build order and acceptance scenarios
- `docs/proposal.md:28-46` — planned features (core and stretch)
- `docs/process/decision-log.md:24-46` — D-004 to D-007
- `AGENTS.md:12-14` — project constraints and decision status
- `openspec/config.yaml` — empty project context
- `assets/catchup-workflow.png` — five-stage workflow figure

## Current Specs (OpenSpec mode only)
- None. `openspec list --specs` returns "No specs found." This change would introduce the first capabilities.

## Related History
- `22838a0` initial planning commit; `0dadbb7` stack decision; `54294b4` RePPIT/OpenSpec split; `3efdf4b` AGENTS.md decision status updated.
- Before 2026-10-01, the automatic daily digest was replaced by manual generation — `docs/process/requirements-changes.md:7`.
