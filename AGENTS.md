# CatchUp — project entry point

This folder is the CatchUp CS146S project workspace. It currently contains planning materials; no application has been implemented.

Before planning or implementing, read:
1. `docs/handoff.md` — confirmed scope, superseded ideas, open decisions, course obligations, next steps.
2. `docs/proposal.md` — current proposal text snapshot.
3. `docs/course-requirements.pdf` — original course brief when checking deliverables.

The existing proposal PDF in this folder preserves the user's layout. `assets/catchup-workflow.png` is the compact workflow figure.

Project constraints: self-hosted web application; user-owned model API; manual, incremental digest generation; public sources and accessible transcripts first. Browser extensions, authenticated content, existing-page change detection, and automatic scheduling are not initial-release requirements.

No stack, supported-source list, provider matrix, or implementation/test commands have been selected yet. Do not infer those decisions from the proposal. Proposed and accepted decisions are tracked in `docs/process/decision-log.md`.

`CLAUDE.md` is a symlink to this file so Claude Code and Factory Droid read the same project context. Edit `AGENTS.md` only.

## Development workflow (decided 2026-10-01)

This supersedes the note in `docs/handoff.md` §9 that OpenSpec/RePPIT are not the established workflow.

- OpenSpec (`openspec/`) manages requirements. Every feature or substantial change is an OpenSpec change under `openspec/changes/<change-name>/`.
- Each change goes: research (`research.md`) → two proposals in `design.md`, user picks one → plan (`proposal.md`, spec deltas, final `design.md`, `tasks.md`), user approves → Factory Droid implements `tasks.md` in a git worktree → Claude Code reviews the diff, tests, and `openspec validate` → user approves merge → `openspec archive`.
- Small fixes may skip research and proposals, but still get a short `tasks.md` or a clear commit message.
- Implementers follow `tasks.md` in order, check off a task only after its verification passes, and do not edit `proposal.md`, `design.md`, or spec deltas. If the plan looks wrong, stop and report.

## Process evidence (course requirement)

The course grades evidence of how requirements and context were communicated to people and AI tools. Keep these up to date as part of the work, not afterwards:

- `docs/process/decision-log.md` — design and technical decisions with alternatives and reasons.
- `docs/process/requirements-changes.md` — requirement changes and why they happened.
- `docs/process/ai-usage-log.md` — real AI tool usage: the actual prompt (verbatim or a faithful excerpt), the tool and model, the outcome, what failed, and how the prompt or instructions were adjusted.
- Test results go into the relevant change's review notes and, once a suite exists, a coverage summary in `docs/process/`.

Never record API keys, tokens, or passwords in these files.

This file contains only project-specific context. Personal global agent rules are maintained separately in the user's existing `~/.codex/AGENTS.md`; do not duplicate them here.
