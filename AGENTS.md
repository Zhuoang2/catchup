# CatchUp — project entry point

This folder is the CatchUp CS146S project workspace. The core flow (model settings, RSS/Atom sources, digest generation, history) is implemented: `backend/` (FastAPI) and `frontend/` (React). Current requirements are in `openspec/specs/`; completed changes are in `openspec/changes/archive/`.

Before planning or implementing, read:
1. `docs/handoff.md` — confirmed scope, superseded ideas, open decisions, course obligations, next steps.
2. `docs/proposal.md` — current proposal text snapshot.
3. `docs/course-requirements.pdf` — original course brief when checking deliverables. It is gitignored (course staff material), so it exists only in the main local checkout, not in worktrees or clones.

The existing proposal PDF in this folder preserves the user's layout. `assets/catchup-workflow.png` is the compact workflow figure.

Project constraints: self-hosted web application; user-owned model API; manual, incremental digest generation; public sources and accessible transcripts first. Browser extensions, authenticated content, existing-page change detection, and automatic scheduling are not initial-release requirements.

Accepted so far: stack is FastAPI + SQLite + React/Vite/TypeScript, served as a single container (D-006); the first model adapter is OpenAI-compatible, developed against DeepSeek (D-004). Podcasts (published transcripts) and YouTube channels (opt-in local captions) are supported as of D-013. Still open: further source types and further model providers. Deployment is local only, from source or a Docker image; there is no hosted instance (D-011). The UI is a local web app, installable as a PWA; there is no native desktop packaging (D-014). Commands are listed under "Commands" below. Do not infer open decisions from the proposal. All decisions are tracked in `docs/process/decision-log.md`.

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
- Implementation is test-first (D-016): when running `openspec-apply-change`, complete each task in `tasks.md` with the `tdd` skill. First write the task's spec scenarios and verification items as failing tests and watch them fail, then implement until they pass, one slice at a time. The seams to test are the ones named in the task's verification; they count as agreed with the user, so do not stop to ask. If a task names no testable seam, stop and report.
- Bug fixing (D-016): for a bug, or a review finding whose cause is not yet known, use the `diagnosing-bugs` skill. Reproduce it with a failing check first, then rank hypotheses, fix, and add a regression test. When running unattended, put the ranked hypotheses and the confirmed cause in the final report and the commit message instead of waiting for the user.
- Review after every Droid run, including fix rounds (D-016). Claude Code reviews the run's diff (from the commit Droid started at to the branch head) in a separate worktree:
  1. Bugs: run Claude Code's built-in `/code-review` on that diff.
  2. Spec: an independent sub-agent that has not seen the design discussion checks the diff against `openspec/changes/<change-name>/` (spec deltas, `design.md`, `tasks.md`). Quoting the spec line for each finding, it reports requirements that are missing or partial, behavior nobody asked for, requirements that look implemented but are wrong, and `tasks.md` verification claims that the tests do not actually perform.
  3. Claude Code verifies every finding against the code or by running it before anything is changed, reports which findings were confirmed, rejected, or need the user's decision, and adds live checks (browser, measurements, Docker) where the change is user-visible.
- Fix rounds and when to stop (D-023, decided 2026-10-21):
  - Classify every confirmed finding before planning a round:
    - (a) a real defect in behavior;
    - (b) an error in an earlier plan or round;
    - (c) a test-only gap, where the behavior is already correct;
    - (d) churn.

    A round contains only (a) and (b) items, tests that cannot fail, and spec scenarios that no test covers. Mutation survivors that are equivalent or marginal (literal strings, logs, caps the spec does not name) are recorded, not fixed.
  - One Droid fix round by default. A second Droid round is only for (a) or (b) items that affect behavior. Leftover test or doc fixes of about 30 lines or fewer go into Claude Code's review commit, verified with named mutations, with no new Droid run and no full re-review.
  - Before changing what a stored state means, find every place that reads it, and trace one item through this run and the next.
  - Before Droid runs, a fresh sub-agent that sees only the code and the new task group checks it for false assumptions. Any assumption about a library's behavior gets a short probe first.
  - When a round would edit code that an earlier round already patched, re-derive that unit from its invariant instead of patching it again.
  - Re-review only the delta: mutations on the changed lines.
  - A round with no (a) item, that adds more than about 10 test lines per source line, is the last one.
  - The Docker smoke script (`scripts/docker-smoke.sh`) and the live check are required for every change. Extra pins are optional.
- Shared skills live in `.agents/skills/` (read by Droid; symlinked into `.claude/skills/` for Claude Code) and are pinned in `skills-lock.json`. Commit them, because a new worktree contains only committed files.

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

- Once per clone, from the repository root: `git config core.hooksPath "$PWD/.githooks"` enables the pre-commit hook that blocks staged API keys and secrets; all worktrees of that clone share the setting.
- Install: `uv sync` (backend), `npm ci` (frontend).
- Backend dev server: `uv run uvicorn catchup.main:app --reload`.
- Backend CLI alternative: `uv run catchup serve` (or `uv run catchup serve --help`).
- Frontend dev server: `npm run dev` (proxies `/api` to port 8000).
- Checks: `uv run pytest`, `npm test -- --run`, `npm run build`.
- See `README.md` for environment setup; `CATCHUP_SECRET_KEY` is required before saving a model key.
