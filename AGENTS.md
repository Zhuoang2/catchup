# CatchUp — project entry point

This folder is the CatchUp CS146S project workspace. The core flow (model settings, RSS/Atom sources, digest generation, history) is implemented: `backend/` (FastAPI) and `frontend/` (React). Current requirements are in `openspec/specs/`; completed changes are in `openspec/changes/archive/`.

Before planning or implementing, read:
1. `docs/handoff.md` — confirmed scope, superseded ideas, open decisions, course obligations, next steps.
2. `docs/proposal.md` — current proposal text snapshot.
3. `docs/course-requirements.pdf` — original course brief when checking deliverables. It is gitignored (course staff material), so it exists only in the main local checkout, not in worktrees or clones.

The existing proposal PDF in this folder preserves the user's layout. `assets/catchup-workflow.png` is the compact workflow figure.

Project constraints: self-hosted web application; user-owned model API; manual, incremental digest generation; public sources and accessible transcripts first. Browser extensions, authenticated content, existing-page change detection, and automatic scheduling are not initial-release requirements.

Accepted so far: stack is FastAPI + SQLite + React/Vite/TypeScript, served as a single container (D-006); the first model adapter is OpenAI-compatible, developed against DeepSeek (D-004). Still open: supported-source list beyond RSS/Atom and further model providers. Deployment is local only, from source or a Docker image; there is no hosted instance (D-011). Commands are listed under "Commands" below. Do not infer open decisions from the proposal. All decisions are tracked in `docs/process/decision-log.md`.

`CLAUDE.md` is a symlink to this file so Claude Code and Factory Droid read the same project context. Edit `AGENTS.md` only.

## Development workflow (decided 2026-10-01)

This supersedes the note in `docs/handoff.md` §9 that OpenSpec/RePPIT are not the established workflow.

- OpenSpec (`openspec/`) manages requirements. Every feature or substantial change is an OpenSpec change under `openspec/changes/<change-name>/`.
- Each change goes: research (`research.md`) → two proposals in `design.md`, user picks one → plan (`proposal.md`, spec deltas, final `design.md`, `tasks.md`), user approves → Factory Droid implements `tasks.md` in a git worktree → Claude Code reviews the diff, tests, and `openspec validate` → user approves merge → `openspec archive`.
- Which commands to use:
  - New features and substantial changes: the RePPIT skills (`/reppit-research` → `/reppit-proposal` → `/reppit-plan`), which write into the OpenSpec change folder. Do not use `/opsx:propose` or `/opsx:explore` for these.
  - Small changes (bug fixes, styling, narrow adjustments): `/opsx:propose` for a lean proposal and `tasks.md` in one step.
  - Implementation: Factory Droid runs `/opsx-apply` (its `openspec-apply-change` skill).
  - Closing: Claude Code reviews; after the user approves the merge, Claude Code runs `openspec archive <change-name>`.
- Keep full RePPIT changes coarse: about 6–8 for the whole course. Everything else uses the lean path.
- Implementers follow `tasks.md` in order, check off a task only after its verification passes, and do not edit `proposal.md`, `design.md`, or spec deltas. If the plan looks wrong, stop and report.

## Process evidence (course requirement)

The course grades evidence of how requirements and context were communicated to people and AI tools. Keep these up to date as part of the work, not afterwards:

- Backlog: GitHub issues in `Zhuoang2/catchup`, shown on the project board https://github.com/users/Zhuoang2/projects/1. Move the issue for the current change to In Progress, and close it when its change is archived.
- `docs/process/decision-log.md` — design and technical decisions with alternatives and reasons.
- `docs/process/requirements-changes.md` — requirement changes and why they happened.
- `docs/process/ai-usage-log.md` — real AI tool usage: the actual prompt (verbatim or a faithful excerpt), the tool and model, the outcome, what failed, and how the prompt or instructions were adjusted.
- Test results go into the relevant change's review notes and, once a suite exists, a coverage summary in `docs/process/`.

Never record API keys, tokens, or passwords in these files.

This file contains only project-specific context. Personal global agent rules are maintained separately in the user's existing `~/.codex/AGENTS.md`; do not duplicate them here.

## Commands

Run backend commands from `backend/` and frontend commands from `frontend/`:

- Install: `uv sync` (backend), `npm ci` (frontend).
- Backend dev server: `uv run uvicorn catchup.main:app --reload`.
- Backend CLI alternative: `uv run catchup serve` (or `uv run catchup serve --help`).
- Frontend dev server: `npm run dev` (proxies `/api` to port 8000).
- Checks: `uv run pytest`, `npm test -- --run`, `npm run build`.
- See `README.md` for environment setup; `CATCHUP_SECRET_KEY` is required before saving a model key.
