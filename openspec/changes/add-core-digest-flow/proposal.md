# Proposal

## Why

CatchUp has planning documents but no application yet. The core promise is this: add the sources you follow, click once, and get a digest of everything new, grouped by topic and linked to the originals. That promise needs a working end-to-end slice before anything else can be built, tested with real sources, or described in the October 15 technical spec. This change builds that slice for RSS/Atom sources and an OpenAI-compatible model (DeepSeek first), using the design the user chose: an item ledger, a background run with progress, and two-stage summarization (see `design.md`).

## What Changes

- New FastAPI backend (SQLite, migrations) and React/Vite/TypeScript frontend, served together as one process. Includes dev tooling, tests, and CI.
- Model settings: the user enters an OpenAI-compatible base URL and API key, tests the connection, and picks a model from the provider's list. The key is stored encrypted and never returned.
- Source management: the user pastes a website or feed URL and sees a preview of the identified feed (name, address, recent entries). On confirm, the source is saved. Duplicates and unsupported URLs are explained. User-supplied URLs are fetched through a guard that blocks internal network addresses.
- Content collection: on each Generate Digest run, every source is checked, and each entry is recorded the first time it is seen. Each check reports one of: new items found, no new items, or failed. A possible gap is flagged when older entries may have dropped off a feed between checks.
- Digest generation: a background run with progress summarizes each new item once (cached) and groups the summaries into topics. Links and source names come from stored data, never from model output. There is no limit on the number of items per run.
- Digest history: saved digests can be listed and reopened after a restart.

## Capabilities

### New Capabilities
- `model-settings`: Configuring an OpenAI-compatible model provider (base URL, API key, model), testing the connection, and protecting the stored key.
- `source-management`: Adding a source from a pasted URL with preview and confirmation, rejecting duplicates and unsupported URLs, listing and deleting sources, and safe fetching of user-supplied URLs.
- `content-collection`: Checking sources on each run, recording entries the first time they are seen, deciding what counts as new, and reporting per-source check outcomes, including failure vs no updates and possible gaps.
- `digest-generation`: Running digest generation in the background with progress, summarizing new items, grouping them by topic with citations to stored items, and handling model errors and retries.
- `digest-history`: Saving digests and letting the user list and reopen past digests.

### Modified Capabilities
- None (no existing specs).

## Impact

- New code: `backend/` (FastAPI app, SQLAlchemy models, Alembic migrations, services, tests) and `frontend/` (React app, Vitest tests). New CI workflow in `.github/workflows/`.
- New dependencies:
  - Backend: FastAPI, uvicorn, SQLAlchemy 2.1, Alembic, Pydantic v2, httpx, feedparser, trafilatura, openai, cryptography, pytest, respx.
  - Frontend: React, React Router, Vite, TypeScript, Vitest.
- Configuration: `CATCHUP_SECRET_KEY` (required to store an API key) and `CATCHUP_DATA_DIR` (SQLite location), documented in `.env.example`.
- Privacy: collected content is sent to the configured model provider. Setup docs must say so (D-004).
- Out of scope: podcasts/YouTube, deployment, access control for shared instances, bookmarks/likes/feedback, a "top N items" selection, scheduling.
